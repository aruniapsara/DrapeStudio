"""Upload endpoints — POST /v1/uploads/sign, direct upload, and upload history."""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_or_create_session_id
from app.middleware.auth import get_request_user
from app.models.db import SourceImage, generate_ulid
from app.services.storage import storage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["uploads"])


def _sanitize_filename(filename: str) -> str:
    """Replace spaces and URL-unsafe characters with underscores."""
    name = re.sub(r"[^\w\-.]", "_", filename)
    return re.sub(r"_+", "_", name)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

ACCEPTED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILES = 5


class FileSignRequest(BaseModel):
    kind: str = "image"
    filename: str
    content_type: str


class SignRequest(BaseModel):
    files: list[FileSignRequest]


class UploadInfo(BaseModel):
    filename: str
    upload_url: str
    file_url: str


class SignResponse(BaseModel):
    uploads: list[UploadInfo]
    expires_in_seconds: int


# ---------------------------------------------------------------------------
# POST /v1/uploads/sign
# ---------------------------------------------------------------------------
@router.post("/uploads/sign", response_model=SignResponse)
async def sign_upload_urls(body: SignRequest, request: Request, response: Response):
    """Return signed upload URLs for each requested file."""
    session_id = get_or_create_session_id(request, response)

    # Validate file count
    if len(body.files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_FILES} files allowed.")
    if len(body.files) == 0:
        raise HTTPException(status_code=400, detail="At least one file is required.")

    uploads: list[UploadInfo] = []
    for f in body.files:
        # Validate content type
        if f.content_type not in ACCEPTED_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {f.content_type}. Use JPG, PNG, or WEBP.",
            )

        safe_filename = _sanitize_filename(f.filename)
        if f.kind == "model_photo":
            path = f"model-photos/{session_id}/{safe_filename}"
        else:
            path = f"uploads/{session_id}/{safe_filename}"
        upload_url = storage.signed_upload_url(
            path, f.content_type, settings.UPLOAD_URL_EXPIRY_SECONDS
        )
        file_url = f"local://{path}"

        uploads.append(
            UploadInfo(
                filename=safe_filename,
                upload_url=upload_url,
                file_url=file_url,
            )
        )

    return SignResponse(
        uploads=uploads,
        expires_in_seconds=settings.UPLOAD_URL_EXPIRY_SECONDS,
    )


# ---------------------------------------------------------------------------
# POST /v1/uploads/direct/{file_path:path}  (local dev only)
# Handles both garment uploads ({session_id}/{filename}) and model photos
# (model-photos/{session_id}/{filename}).
# ---------------------------------------------------------------------------
@router.post("/uploads/direct/{file_path:path}")
async def direct_upload(
    file_path: str,
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Direct file upload endpoint for local development.

    Also records a SourceImage row so the user can reuse this image later.
    """
    if settings.STORAGE_BACKEND != "local":
        raise HTTPException(status_code=404, detail="Direct upload only available in local mode.")

    # Validate content type
    if file.content_type not in ACCEPTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}",
        )

    # Read and validate file size (max 20MB)
    data = await file.read()
    max_size = 20 * 1024 * 1024  # 20MB
    if len(data) > max_size:
        raise HTTPException(status_code=413, detail="File too large. Maximum 20MB.")

    # model-photos/ paths are kept as-is; everything else is prefixed with uploads/
    if file_path.startswith("model-photos/"):
        path = file_path
    else:
        path = f"uploads/{file_path}"

    storage.save(data, path)
    file_url = f"local://{path}"

    # ── Record SourceImage row ────────────────────────────────────────────
    try:
        session_id = get_or_create_session_id(request, response)
        user = get_request_user(request)
        user_id = user["user_id"] if user and user.get("auth_type") == "jwt" else None

        # Determine image type from path prefix
        if "model-photos/" in path:
            image_type = "model_photo"
        else:
            image_type = "garment"

        # Upsert: only insert if image_url doesn't already exist
        existing = db.query(SourceImage).filter(SourceImage.image_url == file_url).first()
        if not existing:
            source_img = SourceImage(
                id=generate_ulid(),
                user_id=user_id,
                session_id=session_id,
                image_url=file_url,
                image_type=image_type,
                original_filename=file.filename,
                file_size_bytes=len(data),
            )
            db.add(source_img)
            db.commit()
    except Exception as exc:
        logger.warning("Failed to record SourceImage for %s: %s", file_url, exc)
        # Don't fail the upload if tracking fails
        try:
            db.rollback()
        except Exception:
            pass

    return {"status": "ok", "file_url": file_url}


# ---------------------------------------------------------------------------
# GET /v1/files/{path:path}  (serve local files in dev)
# ---------------------------------------------------------------------------
@router.get("/files/{file_path:path}")
async def serve_file(file_path: str):
    """Serve files from local storage in development mode."""
    if settings.STORAGE_BACKEND != "local":
        raise HTTPException(status_code=404, detail="File serving only available in local mode.")

    try:
        data = storage.load(file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found.")

    # Determine content type from extension
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    content_types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }
    content_type = content_types.get(ext, "application/octet-stream")

    return Response(content=data, media_type=content_type)


# ---------------------------------------------------------------------------
# GET /v1/uploads/history  — previously uploaded source images
# ---------------------------------------------------------------------------
@router.get("/uploads/history")
def get_upload_history(
    request: Request,
    response: Response,
    image_type: str = "garment",
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
):
    """Return paginated list of previously uploaded source images.

    Authenticated users see their own uploads (by user_id).
    Legacy/unauthenticated users see uploads from their session.
    """
    per_page = max(1, min(per_page, 50))
    page = max(page, 1)
    offset = (page - 1) * per_page

    user = get_request_user(request)

    query = db.query(SourceImage).filter(SourceImage.image_type == image_type)

    # Filter by ownership
    if user and user.get("auth_type") == "jwt" and user.get("user_id"):
        query = query.filter(SourceImage.user_id == user["user_id"])
    else:
        session_id = get_or_create_session_id(request, response)
        query = query.filter(SourceImage.session_id == session_id)

    total = query.count()

    items = (
        query
        .order_by(SourceImage.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    # Use 1-hour expiry for history thumbnails
    history_url_expiry = 3600

    result_items = []
    for img in items:
        signed_url = storage.signed_download_url(img.image_url, history_url_expiry)
        result_items.append({
            "id": img.id,
            "image_url": signed_url,
            "storage_url": img.image_url,
            "original_filename": img.original_filename,
            "file_size_bytes": img.file_size_bytes,
            "created_at": img.created_at.isoformat() if img.created_at else None,
        })

    return {
        "items": result_items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "has_more": (offset + per_page) < total,
    }
