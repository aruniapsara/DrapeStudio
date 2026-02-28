"""History endpoints — GET /v1/history, DELETE /v1/history/{gen_id}."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, get_or_create_session_id
from app.models.db import GenerationOutput, GenerationRequest, UsageCost
from app.schemas.generation import HistoryItem, HistoryListResponse, HistoryOutputImage
from app.services.storage import storage

router = APIRouter(tags=["history"])


# ---------------------------------------------------------------------------
# GET /v1/history
# ---------------------------------------------------------------------------
@router.get("/history", response_model=HistoryListResponse)
def get_history(
    request: Request,
    response: Response,
    page: int = 1,
    per_page: int = 12,
    db: Session = Depends(get_db),
):
    """Return paginated generation history (admin sees all, others see own)."""
    session_id = get_or_create_session_id(request, response)
    user = get_current_user(request)
    is_admin = user and user["role"] == "admin"

    per_page = max(1, min(per_page, 50))
    page = max(page, 1)
    offset = (page - 1) * per_page

    count_query = db.query(func.count(GenerationRequest.id))
    list_query = db.query(GenerationRequest)

    if not is_admin:
        count_query = count_query.filter(GenerationRequest.session_id == session_id)
        list_query = list_query.filter(GenerationRequest.session_id == session_id)

    total: int = count_query.scalar() or 0

    gens = (
        list_query
        .order_by(GenerationRequest.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    items: list[HistoryItem] = []
    for gen in gens:
        # Garment images → signed download URLs
        garment_urls = [
            storage.signed_download_url(url, settings.OUTPUT_URL_EXPIRY_SECONDS)
            for url in (gen.garment_image_urls or [])
        ]

        # Generated output images
        db_outputs = (
            db.query(GenerationOutput)
            .filter(GenerationOutput.generation_request_id == gen.id)
            .order_by(GenerationOutput.variation_index)
            .all()
        )
        output_images = [
            HistoryOutputImage(
                image_url=storage.signed_download_url(
                    o.image_url, settings.OUTPUT_URL_EXPIRY_SECONDS
                ),
                variation_index=o.variation_index,
                width=o.width,
                height=o.height,
            )
            for o in db_outputs
        ]

        cost_usd = None
        duration_ms = None
        if gen.usage:
            if gen.usage.estimated_cost_usd is not None:
                cost_usd = float(gen.usage.estimated_cost_usd)
            duration_ms = gen.usage.duration_ms

        items.append(
            HistoryItem(
                id=gen.id,
                status=gen.status,
                created_at=gen.created_at,
                garment_image_urls=garment_urls,
                output_images=output_images,
                model_params=gen.model_params or {},
                scene_params=gen.scene_params or {},
                cost_usd=cost_usd,
                duration_ms=duration_ms,
            )
        )

    return HistoryListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(offset + per_page) < total,
    )


# ---------------------------------------------------------------------------
# DELETE /v1/history/{gen_id}
# ---------------------------------------------------------------------------
@router.delete("/history/{gen_id}", status_code=204)
def delete_history_item(
    gen_id: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Delete a generation and all its associated files (ownership enforced)."""
    session_id = get_or_create_session_id(request, response)
    user = get_current_user(request)
    is_admin = user and user["role"] == "admin"

    query = db.query(GenerationRequest).filter(GenerationRequest.id == gen_id)
    if not is_admin:
        query = query.filter(GenerationRequest.session_id == session_id)  # ownership check

    gen = query.first()

    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found.")

    # Delete generated output files from storage
    outputs = (
        db.query(GenerationOutput)
        .filter(GenerationOutput.generation_request_id == gen_id)
        .all()
    )
    for output in outputs:
        try:
            storage.delete(output.image_url)
        except Exception:
            pass  # Don't fail if file is already gone

    # Delete uploaded garment images from storage
    for garment_url in gen.garment_image_urls or []:
        try:
            storage.delete(garment_url)
        except Exception:
            pass

    # Remove DB records — children first (no cascade configured)
    db.query(GenerationOutput).filter(
        GenerationOutput.generation_request_id == gen_id
    ).delete(synchronize_session=False)

    db.query(UsageCost).filter(
        UsageCost.generation_request_id == gen_id
    ).delete(synchronize_session=False)

    db.delete(gen)
    db.commit()

    return Response(status_code=204)
