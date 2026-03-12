"""Generation endpoints — create, poll, outputs, download, regenerate."""

import json
import logging
from datetime import datetime
from io import BytesIO
from zipfile import ZipFile

from PIL import Image

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_or_create_session_id
from app.middleware.auth import get_request_user
from app.models.db import AccessoryParams, ChildParams, FitonRequest, GenerationRequest, GenerationOutput, SourceImage, generate_gen_id, generate_ulid
from app.schemas.generation import (
    CreateGenerationRequest,
    GenerationCreatedResponse,
    GenerationOutputsResponse,
    GenerationStatusResponse,
    OutputImage,
)
from app.services.safety import ChildSafetyValidator
from app.services.storage import storage

router = APIRouter(tags=["generations"])


def _get_templates():
    """Lazy import to avoid circular dependency with app.main."""
    from app.main import templates
    return templates


# ---------------------------------------------------------------------------
# POST /v1/generations
# ---------------------------------------------------------------------------
@router.post("/generations", response_model=GenerationCreatedResponse, status_code=201)
def create_generation(
    body: CreateGenerationRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Create a new generation request and enqueue the worker job."""
    session_id = get_or_create_session_id(request, response)

    # Validate garment images count
    if len(body.garment_images) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 garment images allowed.")
    if len(body.garment_images) == 0:
        raise HTTPException(status_code=400, detail="At least one garment image is required.")

    # ── Build canonical params dicts (used for idempotency and DB storage) ────
    if body.module == "fiton":
        fp = body.fiton_params  # type: ignore[assignment]
        model_params_dict: dict = {
            "module": "fiton",
            "customer_photo_url": fp.customer_photo_url,
            "customer_measurements": fp.customer_measurements.model_dump(),
            "fit_preference": fp.fit_preference,
            "garment_type": fp.garment_type,
            "garment_description": fp.garment_description or {},
        }
        scene_params_dict: dict = {
            "garment_measurements": fp.garment_measurements.model_dump() if fp.garment_measurements else None,
            "garment_size_label": fp.garment_size_label,
        }

    elif body.module == "accessories":
        ap = body.accessory_params  # type: ignore[assignment]
        model_params_dict: dict = {
            "module": "accessories",
            "accessory_category": ap.accessory_category,
            "display_mode": ap.display_mode,
            "context_scene": ap.context_scene or "",
            "model_skin_tone": ap.model_skin_tone or "",
            "background_surface": ap.background_surface or "",
            "product_type": body.product_type,
        }
        scene_params_dict: dict = {
            "display_mode": ap.display_mode,
            "accessory_category": ap.accessory_category,
        }

    elif body.module == "children":
        # ── Children's module safety validation ────────────────────────────
        cp = body.child_params  # type: ignore[assignment]
        is_valid, error_msg = ChildSafetyValidator.validate_child_params(
            cp.age_group,
            {
                "pose_style": cp.pose_style,
                "background_preset": cp.background_preset,
                "hair_style": cp.hair_style or "",
                "expression": cp.expression or "",
            },
        )
        if not is_valid:
            raise HTTPException(status_code=422, detail=error_msg)

        # For the children module, model_params stores child config
        # and scene_params stores background + pose info for prompt assembly.
        model_params_dict = {
            "module": "children",
            "age_group": cp.age_group,
            "child_gender": cp.child_gender,
            "hair_style": cp.hair_style or "",
            "expression": cp.expression or "happy",
            "skin_tone": cp.skin_tone or "medium",
            "product_type": body.product_type,
        }
        scene_params_dict = {
            "pose_style": cp.pose_style,
            "background_preset": cp.background_preset,
        }

    else:
        # Adult module — original behaviour
        model_params_dict = body.model_params.model_dump()  # type: ignore[union-attr]
        model_params_dict["product_type"] = body.product_type
        scene_params_dict = body.scene.model_dump()  # type: ignore[union-attr]
        # Store views and quality so the worker can generate the right angles
        scene_params_dict["views"] = selected_views
        scene_params_dict["quality"] = selected_quality

    # ── Determine views and quality ────────────────────────────────────────────
    # These come from the request body (new v2 fields) or default to legacy values
    selected_views = getattr(body, "views", None) or ["front"]
    selected_quality = getattr(body, "quality", None) or "1k"
    image_count = len(selected_views) if body.module != "fiton" else 1

    # ── Wallet / usage enforcement (JWT users only) ─────────────────────────
    request_user = get_request_user(request)
    generation_user_id: str | None = None
    wallet_source: str = ""
    if request_user and request_user.get("auth_type") == "jwt":
        generation_user_id = request_user["user_id"]
        from app.models.db import User as UserModel
        user_obj = db.query(UserModel).filter(UserModel.id == generation_user_id).first()
        if user_obj:
            from app.services.wallet import WalletService
            can_generate, wallet_source = WalletService.check_can_generate(
                user_obj, body.module or "adult", selected_quality, image_count, db,
            )
            if not can_generate:
                from app.config.wallet_pricing import format_currency
                total_cost = WalletService.get_total_cost(
                    body.module or "adult", selected_quality, image_count,
                )
                detail = (
                    f"Insufficient wallet balance. This generation costs "
                    f"{format_currency(total_cost)}. Please reload your wallet."
                )
                raise HTTPException(status_code=402, detail=detail)

    # ── Idempotency check ─────────────────────────────────────────────────────
    if body.idempotency_key:
        existing = (
            db.query(GenerationRequest)
            .filter(GenerationRequest.idempotency_key == body.idempotency_key)
            .first()
        )
        if existing:
            existing_params = {
                "garment_images": existing.garment_image_urls,
                "model_params": existing.model_params,
                "scene_params": existing.scene_params,
            }
            new_params = {
                "garment_images": body.garment_images,
                "model_params": model_params_dict,
                "scene_params": scene_params_dict,
            }
            if json.dumps(existing_params, sort_keys=True) == json.dumps(
                new_params, sort_keys=True
            ):
                return GenerationCreatedResponse(id=existing.id, status=existing.status)
            else:
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency key already used with different parameters.",
                )

    # ── Create GenerationRequest record ───────────────────────────────────────
    gen_id = generate_gen_id()
    gen_request = GenerationRequest(
        id=gen_id,
        session_id=session_id,
        user_id=generation_user_id,          # tie to authenticated user
        status="queued",
        module=body.module,
        garment_image_urls=body.garment_images,
        model_params=model_params_dict,
        scene_params=scene_params_dict,
        output_count=image_count,
        prompt_template_version="v0.1",
        idempotency_key=body.idempotency_key,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(gen_request)
    db.flush()  # Flush so gen_id is persisted before inserting child_params FK

    # ── Create ChildParams record (children module only) ──────────────────────
    if body.module == "children" and body.child_params is not None:
        cp = body.child_params
        child_record = ChildParams(
            id=generate_ulid(),
            generation_request_id=gen_id,
            age_group=cp.age_group,
            child_gender=cp.child_gender,
            pose_style=cp.pose_style,
            background_preset=cp.background_preset,
            hair_style=cp.hair_style,
            expression=cp.expression or "happy",
        )
        db.add(child_record)

    # ── Create AccessoryParams record (accessories module only) ───────────────
    elif body.module == "accessories" and body.accessory_params is not None:
        ap = body.accessory_params
        accessory_record = AccessoryParams(
            id=generate_ulid(),
            generation_request_id=gen_id,
            accessory_category=ap.accessory_category,
            display_mode=ap.display_mode,
            context_scene=ap.context_scene,
            model_skin_tone=ap.model_skin_tone,
            background_surface=ap.background_surface,
        )
        db.add(accessory_record)

    # ── Create FitonRequest record (fiton module only) ────────────────────────
    elif body.module == "fiton" and body.fiton_params is not None:
        from app.services.sizing import sizing_service

        fp = body.fiton_params
        cm = fp.customer_measurements
        gm = fp.garment_measurements

        # Run size recommendation immediately so recommended_size is stored
        result = sizing_service.recommend_size(
            customer_measurements=cm.model_dump(),
            garment_measurements=gm.model_dump() if gm else None,
            garment_size_label=fp.garment_size_label,
            fit_preference=fp.fit_preference,
        )

        fiton_record = FitonRequest(
            id=generate_ulid(),
            generation_request_id=gen_id,
            customer_photo_url=fp.customer_photo_url,
            customer_measurements=cm.model_dump(),
            garment_measurements=gm.model_dump() if gm else None,
            garment_size_label=fp.garment_size_label,
            fit_preference=fp.fit_preference,
            recommended_size=result.recommended_size,
            fit_confidence=result.fit_confidence,
            fit_details=result.fit_details,
        )
        db.add(fiton_record)

    db.commit()
    db.refresh(gen_request)

    # ── Safety-net: ensure SourceImage rows exist for all referenced images ──
    try:
        all_source_urls = list(body.garment_images)
        # Also track model photo if present
        model_photo_url = model_params_dict.get("model_photo_url") or model_params_dict.get("customer_photo_url")
        if model_photo_url:
            all_source_urls.append(model_photo_url)

        for src_url in all_source_urls:
            existing = db.query(SourceImage).filter(SourceImage.image_url == src_url).first()
            if not existing:
                # Determine image type
                if "model-photos/" in src_url or "customer_photo" in src_url:
                    img_type = "model_photo"
                else:
                    img_type = "garment"

                db.add(SourceImage(
                    id=generate_ulid(),
                    user_id=generation_user_id,
                    session_id=session_id,
                    image_url=src_url,
                    image_type=img_type,
                ))
        db.commit()
    except Exception as exc:
        logger.warning("SourceImage safety-net upsert failed for %s: %s", gen_id, exc)
        try:
            db.rollback()
        except Exception:
            pass

    # ── Enqueue worker job ────────────────────────────────────────────────────
    try:
        import redis as redis_lib
        from rq import Queue

        redis_conn = redis_lib.from_url(settings.REDIS_URL)
        queue = Queue("drapestudio", connection=redis_conn)
        queue.enqueue(
            "app.worker.jobs.generate_images",
            gen_id,
            job_timeout=600,
        )
    except Exception:
        # If Redis is not available, the job stays queued
        pass

    # ── Deduct wallet balance (after successful enqueue) ──────────────────────
    if generation_user_id and wallet_source:
        try:
            from app.services.wallet import WalletService
            WalletService.deduct(
                user_id=generation_user_id,
                generation_id=gen_id,
                module=body.module or "adult",
                quality=selected_quality,
                image_count=image_count,
                source=wallet_source,
                db=db,
            )
        except Exception as exc:
            logger.warning("Wallet deduction failed for %s: %s", gen_id, exc)

    return GenerationCreatedResponse(id=gen_id, status="queued")


# ---------------------------------------------------------------------------
# GET /v1/generations/{id}
# ---------------------------------------------------------------------------
@router.get("/generations/{gen_id}", response_model=GenerationStatusResponse)
def get_generation_status(gen_id: str, db: Session = Depends(get_db)):
    """Get the status of a generation request."""
    gen = db.query(GenerationRequest).filter(GenerationRequest.id == gen_id).first()
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found.")

    return GenerationStatusResponse(
        id=gen.id,
        status=gen.status,
        created_at=gen.created_at,
        prompt_template_version=gen.prompt_template_version,
        error_message=gen.error_message,
    )


# ---------------------------------------------------------------------------
# GET /v1/generations/{id}/outputs
# ---------------------------------------------------------------------------
@router.get("/generations/{gen_id}/outputs", response_model=GenerationOutputsResponse)
def get_generation_outputs(gen_id: str, db: Session = Depends(get_db)):
    """Get the outputs for a completed generation."""
    gen = db.query(GenerationRequest).filter(GenerationRequest.id == gen_id).first()
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found.")

    outputs = []
    if gen.status == "succeeded":
        db_outputs = (
            db.query(GenerationOutput)
            .filter(GenerationOutput.generation_request_id == gen_id)
            .order_by(GenerationOutput.variation_index)
            .all()
        )
        for out in db_outputs:
            image_url = storage.signed_download_url(
                out.image_url,
                settings.OUTPUT_URL_EXPIRY_SECONDS,
            )
            outputs.append(
                OutputImage(
                    image_url=image_url,
                    width=out.width,
                    height=out.height,
                )
            )

    cost_usd = None
    if gen.usage and gen.usage.estimated_cost_usd is not None:
        cost_usd = float(gen.usage.estimated_cost_usd)

    return GenerationOutputsResponse(
        id=gen.id,
        status=gen.status,
        outputs=outputs,
        error_message=gen.error_message,
        cost_usd=cost_usd,
    )


# ---------------------------------------------------------------------------
# GET /v1/generations/{id}/status-partial  (HTMX polling)
# ---------------------------------------------------------------------------
@router.get("/generations/{gen_id}/status-partial", response_class=HTMLResponse)
def get_generation_status_partial(
    gen_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Return an HTMX partial fragment for status polling."""
    gen = db.query(GenerationRequest).filter(GenerationRequest.id == gen_id).first()
    if not gen:
        return HTMLResponse(
            '<div id="status-container">'
            '<div class="status-card status-error">'
            "<p>Generation not found.</p>"
            "</div></div>",
            status_code=404,
        )

    return _get_templates().TemplateResponse(
        "partials/status_poll.html",
        {
            "request": request,
            "gen_id": gen_id,
            "status": gen.status,
            "error_message": gen.error_message,
        },
    )


# ---------------------------------------------------------------------------
# GET /v1/generations/{id}/download-zip
# ---------------------------------------------------------------------------
@router.get("/generations/{gen_id}/download-zip")
def download_zip(gen_id: str, db: Session = Depends(get_db)):
    """Download all output images for a generation as a ZIP file."""
    gen = db.query(GenerationRequest).filter(GenerationRequest.id == gen_id).first()
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found.")
    if gen.status != "succeeded":
        raise HTTPException(
            status_code=400,
            detail=f"Generation is '{gen.status}', not yet succeeded.",
        )

    db_outputs = (
        db.query(GenerationOutput)
        .filter(GenerationOutput.generation_request_id == gen_id)
        .order_by(GenerationOutput.variation_index)
        .all()
    )

    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, "w") as zf:
        for i, out in enumerate(db_outputs):
            try:
                image_bytes = storage.load(out.image_url)
                filename = f"drapestudio_{gen_id}_{i + 1}.jpg"
                zf.writestr(filename, image_bytes)
            except Exception:
                pass

    zip_buffer.seek(0)
    zip_bytes = zip_buffer.read()

    return StreamingResponse(
        iter([zip_bytes]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="drapestudio_{gen_id}.zip"',
            "Content-Length": str(len(zip_bytes)),
        },
    )


# ---------------------------------------------------------------------------
# GET /v1/generations/{id}/fiton-details  (Virtual Fit-On module only)
# ---------------------------------------------------------------------------
@router.get("/generations/{gen_id}/fiton-details")
def get_fiton_details(gen_id: str, db: Session = Depends(get_db)):
    """Return size recommendation and fit details for a Virtual Fit-On generation."""
    gen = db.query(GenerationRequest).filter(GenerationRequest.id == gen_id).first()
    if not gen or gen.module != "fiton":
        raise HTTPException(status_code=404, detail="Fit-on generation not found.")

    fiton = (
        db.query(FitonRequest)
        .filter(FitonRequest.generation_request_id == gen_id)
        .first()
    )
    if not fiton:
        raise HTTPException(status_code=404, detail="Fit-on details not found.")

    customer_photo_signed = None
    if fiton.customer_photo_url:
        try:
            customer_photo_signed = storage.signed_download_url(
                fiton.customer_photo_url, settings.OUTPUT_URL_EXPIRY_SECONDS
            )
        except Exception:
            customer_photo_signed = None

    return {
        "recommended_size":  fiton.recommended_size,
        "fit_confidence":    float(fiton.fit_confidence) if fiton.fit_confidence is not None else 0.0,
        "fit_preference":    gen.model_params.get("fit_preference", "regular"),
        "fit_details":       fiton.fit_details or {},
        "garment_type":      gen.model_params.get("garment_type", "dress"),
        "customer_photo_url": customer_photo_signed,
    }


# ---------------------------------------------------------------------------
# GET /v1/outputs/{output_id}/thumb  — 200 px wide WebP thumbnail
# ---------------------------------------------------------------------------
@router.get("/outputs/{output_id}/thumb")
def get_output_thumb(output_id: str, width: int = 200, db: Session = Depends(get_db)):
    """Return a WebP thumbnail (default 200 px wide) for a generation output image."""
    output = db.query(GenerationOutput).filter(GenerationOutput.id == output_id).first()
    if not output:
        raise HTTPException(status_code=404, detail="Output not found.")

    try:
        image_bytes = storage.load(output.image_url)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Image data not found.") from exc

    # Resize while preserving aspect ratio, then encode as WebP
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    aspect = img.height / img.width
    thumb_h = int(width * aspect)
    img = img.resize((width, thumb_h), Image.LANCZOS)

    buf = BytesIO()
    img.save(buf, format="WEBP", quality=75)
    buf.seek(0)

    return Response(
        content=buf.read(),
        media_type="image/webp",
        headers={
            "Cache-Control": "public, max-age=86400",
            "Content-Disposition": f'inline; filename="thumb_{output_id}.webp"',
        },
    )
