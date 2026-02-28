"""Storage abstraction: local filesystem (dev) and GCS (prod)."""

import os
from abc import ABC, abstractmethod
from pathlib import Path

from app.config import settings

# Base storage directory for local backend — driven by STORAGE_ROOT env var
STORAGE_ROOT = Path(settings.STORAGE_ROOT)


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def save(self, data: bytes, path: str) -> str:
        """Save data to storage and return the storage path."""
        ...

    @abstractmethod
    def load(self, path: str) -> bytes:
        """Load data from storage by path."""
        ...

    @abstractmethod
    def signed_download_url(self, path: str, expiry_seconds: int) -> str:
        """Return a URL to download the file."""
        ...

    @abstractmethod
    def signed_upload_url(
        self, path: str, content_type: str, expiry_seconds: int
    ) -> str:
        """Return a URL where the client can upload a file."""
        ...


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage for development."""

    def __init__(self, root: Path | None = None):
        self.root = root or STORAGE_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, path: str) -> str:
        """Save bytes to local filesystem at storage/{path}."""
        full_path = self.root / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        return f"local://{path}"

    def load(self, path: str) -> bytes:
        """Load bytes from local filesystem."""
        # Strip local:// prefix if present
        clean_path = path.replace("local://", "")
        full_path = self.root / clean_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {full_path}")
        return full_path.read_bytes()

    def signed_download_url(self, path: str, expiry_seconds: int) -> str:
        """Return a local URL served by FastAPI."""
        clean_path = path.replace("local://", "")
        return f"/v1/files/{clean_path}"

    def signed_upload_url(
        self, path: str, content_type: str, expiry_seconds: int
    ) -> str:
        """Return the local direct upload endpoint URL."""
        # path is "uploads/{session_id}/{filename}"; strip the "uploads/" prefix
        # because the endpoint is /v1/uploads/direct/{session_id}/{filename}
        clean_path = path.removeprefix("uploads/")
        return f"/v1/uploads/direct/{clean_path}"


class GCSStorageBackend(StorageBackend):
    """Google Cloud Storage backend for production."""

    def __init__(self):
        # Import here so GCS dependency is optional
        from google.cloud import storage as gcs

        self.client = gcs.Client()
        self.uploads_bucket = self.client.bucket(settings.GCS_BUCKET_UPLOADS)
        self.outputs_bucket = self.client.bucket(settings.GCS_BUCKET_OUTPUTS)

    def _get_bucket(self, path: str):
        """Determine bucket based on path prefix."""
        if path.startswith("uploads/"):
            return self.uploads_bucket
        return self.outputs_bucket

    def save(self, data: bytes, path: str) -> str:
        """Save bytes to GCS."""
        bucket = self._get_bucket(path)
        blob = bucket.blob(path)
        blob.upload_from_string(data)
        return f"gcs://{bucket.name}/{path}"

    def load(self, path: str) -> bytes:
        """Load bytes from GCS."""
        clean_path = path
        for prefix in ("gcs://", f"gcs://{settings.GCS_BUCKET_UPLOADS}/", f"gcs://{settings.GCS_BUCKET_OUTPUTS}/"):
            if clean_path.startswith(prefix):
                clean_path = clean_path[len(prefix):]
                break
        bucket = self._get_bucket(clean_path)
        blob = bucket.blob(clean_path)
        return blob.download_as_bytes()

    def signed_download_url(self, path: str, expiry_seconds: int) -> str:
        """Return a GCS signed download URL."""
        import datetime

        clean_path = path
        for prefix in ("gcs://", f"gcs://{settings.GCS_BUCKET_UPLOADS}/", f"gcs://{settings.GCS_BUCKET_OUTPUTS}/"):
            if clean_path.startswith(prefix):
                clean_path = clean_path[len(prefix):]
                break
        bucket = self._get_bucket(clean_path)
        blob = bucket.blob(clean_path)
        return blob.generate_signed_url(
            expiration=datetime.timedelta(seconds=expiry_seconds),
            method="GET",
        )

    def signed_upload_url(
        self, path: str, content_type: str, expiry_seconds: int
    ) -> str:
        """Return a GCS signed upload URL."""
        import datetime

        bucket = self._get_bucket(path)
        blob = bucket.blob(path)
        return blob.generate_signed_url(
            expiration=datetime.timedelta(seconds=expiry_seconds),
            method="PUT",
            content_type=content_type,
        )


def get_storage_backend() -> StorageBackend:
    """Factory: return the appropriate backend based on STORAGE_BACKEND env var."""
    if settings.STORAGE_BACKEND == "gcs":
        return GCSStorageBackend()
    return LocalStorageBackend()


# Singleton instance
storage = get_storage_backend()
