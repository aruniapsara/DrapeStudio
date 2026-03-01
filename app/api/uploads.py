"""Upload endpoints — POST /v1/uploads/sign and direct upload for local dev."""

import re

from fastapi import APIRouter, HTTPException, Request, Response, UploadFile, File
from pydantic import BaseModel

from app.config import settings
from app.dependencies import get_or_create_session_id
from app.services.storage import storage

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
async def direct_upload(file_path: str, file: UploadFile = File(...)):
    """Direct file upload endpoint for local development."""
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
    return {"status": "ok", "file_url": f"local://{path}"}


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
