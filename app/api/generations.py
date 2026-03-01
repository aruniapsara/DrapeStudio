"""Generation endpoints — create, poll, outputs, regenerate."""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_or_create_session_id
from app.models.db import GenerationRequest, GenerationOutput, generate_gen_id
from app.schemas.generation import (
    CreateGenerationRequest,
    GenerationCreatedResponse,
    GenerationOutputsResponse,
    GenerationStatusResponse,
    OutputImage,
)
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

    # Idempotency check
    if body.idempotency_key:
        existing = (
            db.query(GenerationRequest)
            .filter(GenerationRequest.idempotency_key == body.idempotency_key)
            .first()
        )
        if existing:
            # Check if params match
            existing_params = {
                "garment_images": existing.garment_image_urls,
                "model_params": existing.model_params,
                "scene_params": existing.scene_params,
            }
            new_model_params = body.model_params.model_dump()
            new_model_params["product_type"] = body.product_type
            new_params = {
                "garment_images": body.garment_images,
                "model_params": new_model_params,
                "scene_params": body.scene.model_dump(),
            }
            if json.dumps(existing_params, sort_keys=True) == json.dumps(
                new_params, sort_keys=True
            ):
                # Identical request — return existing
                return GenerationCreatedResponse(
                    id=existing.id, status=existing.status
                )
            else:
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency key already used with different parameters.",
                )

    # Build model_params dict — embed product_type so prompt assembly
    # can access it without a DB schema migration.
    model_params_dict = body.model_params.model_dump()
    model_params_dict["product_type"] = body.product_type

    # Create generation request
    gen_id = generate_gen_id()
    gen_request = GenerationRequest(
        id=gen_id,
        session_id=session_id,
        status="queued",
        garment_image_urls=body.garment_images,
        model_params=model_params_dict,
        scene_params=body.scene.model_dump(),
        output_count=body.output.count,
        prompt_template_version="v0.1",
        idempotency_key=body.idempotency_key,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(gen_request)
    db.commit()
    db.refresh(gen_request)

    # Enqueue worker job (try Redis Queue, fall back gracefully)
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
        # Worker can pick it up later, or it can be processed manually
        pass

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
            # Generate a signed download URL
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
