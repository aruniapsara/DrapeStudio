"""Upload endpoints — POST /v1/uploads/sign and direct upload for local dev."""

from fastapi import APIRouter

router = APIRouter(tags=["uploads"])
