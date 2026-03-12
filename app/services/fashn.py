"""FASHN.ai virtual try-on API integration.

Replaces Gemini for the fit-on module. FASHN is purpose-built for virtual
try-on and preserves customer identity natively — no prompt engineering needed.

API flow: submit → poll → download result.

Usage (synchronous, for RQ worker)::

    from app.services.fashn import FashnService, FashnError

    svc = FashnService()
    result = svc.generate_tryon(
        customer_photo_url="https://...",
        garment_photo_url="https://...",
    )
    # result.image_bytes  → raw PNG bytes of the output
    # result.duration_ms  → total wall-clock time
"""

import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

FASHN_MODEL = "tryon-v1.6"
POLL_INTERVAL_S = 2.5
MAX_POLLS = 60  # 60 × 2.5s = 150s max wait


class FashnError(Exception):
    """Raised when the FASHN API call fails."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class FashnResult:
    """Result from a FASHN try-on call."""

    def __init__(
        self,
        image_bytes: bytes,
        prediction_id: str = "",
        duration_ms: int = 0,
    ):
        self.image_bytes = image_bytes
        self.prediction_id = prediction_id
        self.duration_ms = duration_ms


class FashnService:
    """Synchronous FASHN.ai virtual try-on client (for RQ worker)."""

    def __init__(self):
        self.api_key = settings.FASHN_API_KEY
        self.base_url = settings.FASHN_API_URL.rstrip("/")
        if not self.api_key:
            raise FashnError("FASHN_API_KEY is not configured.")

    @property
    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def generate_tryon(
        self,
        customer_photo_url: str,
        garment_photo_url: str,
        category: str = "auto",
    ) -> FashnResult:
        """Submit a try-on request, poll until complete, download the result.

        Args:
            customer_photo_url: Publicly accessible URL of the customer photo.
            garment_photo_url:  Publicly accessible URL of the garment photo.
            category:           "auto", "tops", "bottoms", or "one-piece".

        Returns:
            FashnResult with downloaded image bytes and metadata.

        Raises:
            FashnError: On API errors, timeouts, or download failures.
        """
        start = time.time()

        # ── Step 1: Submit prediction ─────────────────────────────────────
        prediction_id = self._submit(customer_photo_url, garment_photo_url, category)
        logger.info("FASHN prediction submitted: %s", prediction_id)

        # ── Step 2: Poll until completed / failed ─────────────────────────
        output_urls = self._poll(prediction_id)
        logger.info(
            "FASHN prediction %s completed with %d output(s)",
            prediction_id,
            len(output_urls),
        )

        # ── Step 3: Download the first output image ───────────────────────
        image_bytes = self._download(output_urls[0])

        duration_ms = int((time.time() - start) * 1000)
        logger.info(
            "FASHN try-on complete: %s — %d bytes in %dms",
            prediction_id,
            len(image_bytes),
            duration_ms,
        )

        return FashnResult(
            image_bytes=image_bytes,
            prediction_id=prediction_id,
            duration_ms=duration_ms,
        )

    # ── Internal helpers ──────────────────────────────────────────────────

    def _submit(
        self,
        customer_photo_url: str,
        garment_photo_url: str,
        category: str,
    ) -> str:
        """POST /run — submit a try-on prediction. Returns prediction ID."""
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    f"{self.base_url}/run",
                    headers=self._headers,
                    json={
                        "model_name": FASHN_MODEL,
                        "inputs": {
                            "model_image": customer_photo_url,
                            "garment_image": garment_photo_url,
                            "category": category,
                            "mode": "quality",
                            "garment_photo_type": "auto",
                            "num_samples": 1,
                            "output_format": "png",
                        },
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["id"]
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text[:500]
            status = exc.response.status_code
            retryable = status in (429, 500, 502, 503, 504)
            raise FashnError(
                f"FASHN submit failed (HTTP {status}): {error_body}",
                retryable=retryable,
            )
        except Exception as exc:
            raise FashnError(f"FASHN submit error: {exc}")

    def _poll(self, prediction_id: str) -> list[str]:
        """GET /status/{id} — poll until completed or failed. Returns output URLs."""
        try:
            with httpx.Client(timeout=30) as client:
                for poll_num in range(MAX_POLLS):
                    time.sleep(POLL_INTERVAL_S)
                    resp = client.get(
                        f"{self.base_url}/status/{prediction_id}",
                        headers=self._headers,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    status = data.get("status", "")

                    if status == "completed":
                        output = data.get("output", [])
                        if not output:
                            raise FashnError(
                                "FASHN returned completed but no output URLs."
                            )
                        return output

                    if status == "failed":
                        error_info = data.get("error", {})
                        error_msg = (
                            error_info.get("message", "Unknown error")
                            if isinstance(error_info, dict)
                            else str(error_info)
                        )
                        raise FashnError(f"FASHN prediction failed: {error_msg}")

                    # Still running — log progress every 10 polls
                    if (poll_num + 1) % 10 == 0:
                        logger.info(
                            "FASHN %s still %s after %ds...",
                            prediction_id,
                            status,
                            int((poll_num + 1) * POLL_INTERVAL_S),
                        )

        except FashnError:
            raise
        except httpx.HTTPStatusError as exc:
            raise FashnError(
                f"FASHN poll failed (HTTP {exc.response.status_code}): "
                f"{exc.response.text[:300]}"
            )
        except Exception as exc:
            raise FashnError(f"FASHN poll error: {exc}")

        raise FashnError(
            f"FASHN timeout: prediction {prediction_id} did not complete "
            f"within {int(MAX_POLLS * POLL_INTERVAL_S)}s"
        )

    def _download(self, url: str) -> bytes:
        """Download the output image from FASHN CDN."""
        try:
            with httpx.Client(timeout=60, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.content
        except Exception as exc:
            raise FashnError(f"Failed to download FASHN output from {url}: {exc}")
