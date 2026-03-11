"""Scheduled cleanup service for image retention management.

Three cleanup tasks:
1. Delete expired generated outputs (>7 days, status succeeded/failed)
2. Cap per-user outputs to MAX_OUTPUTS_PER_USER (oldest auto-deleted)
3. Delete expired source images (>30 days, unreferenced)
"""

import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import cast, String
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.db import (
    GenerationOutput,
    GenerationRequest,
    SourceImage,
    UsageCost,
)
from app.services.storage import storage

logger = logging.getLogger(__name__)


def cleanup_expired_outputs(db: Session) -> int:
    """Delete generation requests (and their outputs) older than OUTPUT_RETENTION_DAYS.

    Only deletes rows with status 'succeeded' or 'failed' — never pending/running.
    Returns the number of generation requests deleted.
    """
    cutoff = datetime.utcnow() - timedelta(days=settings.OUTPUT_RETENTION_DAYS)
    expired = (
        db.query(GenerationRequest)
        .filter(
            GenerationRequest.created_at < cutoff,
            GenerationRequest.status.in_(["succeeded", "failed"]),
        )
        .all()
    )

    deleted_count = 0
    for gen in expired:
        _delete_generation_and_files(db, gen)
        deleted_count += 1

    if deleted_count:
        db.commit()
        logger.info("cleanup_expired_outputs: deleted %d expired generations", deleted_count)

    return deleted_count


def cleanup_excess_outputs(db: Session) -> int:
    """Per user, keep only the newest MAX_OUTPUTS_PER_USER succeeded generations.

    Uses a 1-hour buffer: only deletes rows whose created_at is at least 1 hour
    old, to avoid race conditions with generations currently in progress.
    Returns the number of generation requests deleted.
    """
    max_keep = settings.MAX_OUTPUTS_PER_USER
    buffer_cutoff = datetime.utcnow() - timedelta(hours=1)

    # Get all user_ids that have generations
    user_ids = (
        db.query(GenerationRequest.user_id)
        .filter(GenerationRequest.user_id.isnot(None))
        .distinct()
        .all()
    )

    deleted_count = 0
    for (user_id,) in user_ids:
        # Get all succeeded generations for this user, ordered newest first
        user_gens = (
            db.query(GenerationRequest)
            .filter(
                GenerationRequest.user_id == user_id,
                GenerationRequest.status == "succeeded",
                GenerationRequest.created_at < buffer_cutoff,
            )
            .order_by(GenerationRequest.created_at.desc())
            .all()
        )

        # Keep newest max_keep, delete the rest
        if len(user_gens) > max_keep:
            excess = user_gens[max_keep:]
            for gen in excess:
                _delete_generation_and_files(db, gen)
                deleted_count += 1

    if deleted_count:
        db.commit()
        logger.info("cleanup_excess_outputs: deleted %d excess generations", deleted_count)

    return deleted_count


def cleanup_expired_sources(db: Session) -> int:
    """Delete SourceImage rows older than SOURCE_RETENTION_DAYS if unreferenced.

    A source image is 'referenced' if any GenerationRequest still has it in
    its garment_image_urls JSON array or model_params JSON dict.
    Returns the number of source images deleted.
    """
    cutoff = datetime.utcnow() - timedelta(days=settings.SOURCE_RETENTION_DAYS)
    expired = (
        db.query(SourceImage)
        .filter(SourceImage.created_at < cutoff)
        .all()
    )

    deleted_count = 0
    for source in expired:
        if not _is_source_image_referenced(db, source.image_url):
            # Delete the actual file from storage
            try:
                storage.delete(source.image_url)
            except Exception as exc:
                logger.warning(
                    "Failed to delete source file %s: %s", source.image_url, exc
                )

            db.delete(source)
            deleted_count += 1

    if deleted_count:
        db.commit()
        logger.info("cleanup_expired_sources: deleted %d expired source images", deleted_count)

    return deleted_count


def _is_source_image_referenced(db: Session, image_url: str) -> bool:
    """Check if any GenerationRequest references this image URL.

    Checks both garment_image_urls (JSON array) and model_params (JSON dict)
    using string containment on the JSON-cast column. Works with both
    SQLite and PostgreSQL.
    """
    # Check garment_image_urls — cast JSON column to string and search
    garment_ref = (
        db.query(GenerationRequest.id)
        .filter(
            cast(GenerationRequest.garment_image_urls, String).contains(image_url)
        )
        .first()
    )
    if garment_ref:
        return True

    # Check model_params (for model_photo_url / customer_photo_url)
    model_ref = (
        db.query(GenerationRequest.id)
        .filter(
            cast(GenerationRequest.model_params, String).contains(image_url)
        )
        .first()
    )
    if model_ref:
        return True

    return False


def _delete_generation_and_files(db: Session, gen: GenerationRequest) -> None:
    """Delete a generation request, its outputs, usage cost, and associated files."""
    gen_id = gen.id

    # Delete output files from storage
    outputs = (
        db.query(GenerationOutput)
        .filter(GenerationOutput.generation_request_id == gen_id)
        .all()
    )
    for output in outputs:
        try:
            storage.delete(output.image_url)
        except Exception as exc:
            logger.warning("Failed to delete output file %s: %s", output.image_url, exc)

    # Delete DB records — children first (no cascade)
    db.query(GenerationOutput).filter(
        GenerationOutput.generation_request_id == gen_id
    ).delete(synchronize_session=False)

    db.query(UsageCost).filter(
        UsageCost.generation_request_id == gen_id
    ).delete(synchronize_session=False)

    # Delete related module-specific records
    from app.models.db import ChildParams, AccessoryParams, FitonRequest

    db.query(ChildParams).filter(
        ChildParams.generation_request_id == gen_id
    ).delete(synchronize_session=False)

    db.query(AccessoryParams).filter(
        AccessoryParams.generation_request_id == gen_id
    ).delete(synchronize_session=False)

    db.query(FitonRequest).filter(
        FitonRequest.generation_request_id == gen_id
    ).delete(synchronize_session=False)

    db.delete(gen)


def run_full_cleanup() -> dict:
    """Run all three cleanup tasks. Returns summary dict."""
    db = SessionLocal()
    try:
        expired_outputs = cleanup_expired_outputs(db)
        excess_outputs = cleanup_excess_outputs(db)
        expired_sources = cleanup_expired_sources(db)

        summary = {
            "expired_outputs_deleted": expired_outputs,
            "excess_outputs_deleted": excess_outputs,
            "expired_sources_deleted": expired_sources,
            "timestamp": datetime.utcnow().isoformat(),
        }
        logger.info("Full cleanup completed: %s", summary)
        return summary

    except Exception as exc:
        logger.exception("Cleanup failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
        raise
    finally:
        db.close()
