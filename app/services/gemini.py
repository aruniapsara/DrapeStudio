"""Image generation service via OpenRouter API (Gemini model)."""

import base64
import logging
import re
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Fixed camera angles for the three output variations — adult module.
# Each description also requires the face to remain visible.
VARIATION_VIEWS = [
    (
        "CAMERA ANGLE FOR THIS IMAGE: Front view — model facing directly toward the camera. "
        "Full face clearly visible, eyes looking at camera."
    ),
    (
        "CAMERA ANGLE FOR THIS IMAGE: Three-quarter side view — model turned 45 degrees to the side. "
        "Head angled back toward the camera so the face is clearly visible."
    ),
    (
        "CAMERA ANGLE FOR THIS IMAGE: Back view — model facing away from camera to show the back of the garment. "
        "Model's head turned over the shoulder looking back toward the camera so the face is clearly visible."
    ),
]

# Accessories camera angle descriptions — loaded directly from the YAML template
# at call time rather than hard-coded here, because the angles differ by display mode.
# This dict provides fallback strings in case the template can't be loaded.
ACCESSORIES_FALLBACK_VIEWS: dict[str, list[str]] = {
    "on_model": [
        "CAMERA ANGLE FOR THIS IMAGE: Straight-on close-up — product facing directly toward lens.",
        "CAMERA ANGLE FOR THIS IMAGE: Angled view — 45 degrees to the side, showing product depth.",
    ],
    "flat_lay": [
        "CAMERA ANGLE FOR THIS IMAGE: Overhead (top-down) at 90 degrees.",
        "CAMERA ANGLE FOR THIS IMAGE: 45-degree angle — showing product profile and depth.",
    ],
    "lifestyle": [
        "CAMERA ANGLE FOR THIS IMAGE: Wide contextual scene.",
        "CAMERA ANGLE FOR THIS IMAGE: Tighter product-focused composition.",
    ],
}

# Gentler camera angle descriptions for the children's module.
# Uses softer language to avoid overly fashion-forward framing for minors.
CHILDREN_VARIATION_VIEWS = [
    (
        "CAMERA ANGLE FOR THIS IMAGE: Front view — child facing directly toward the camera. "
        "Face clearly and naturally visible, neutral or gentle expression."
    ),
    (
        "CAMERA ANGLE FOR THIS IMAGE: Gentle 45-degree side view — child turned slightly to the side. "
        "Face gently turned back toward the camera so it remains clearly visible. "
        "Outfit silhouette visible on both sides."
    ),
    (
        "CAMERA ANGLE FOR THIS IMAGE: Back view — child facing away from camera to show the back of the garment. "
        "Child looking over the shoulder with a natural, comfortable head turn so the face is partially visible."
    ),
]


class GeminiError(Exception):
    """Custom exception for image-generation API errors."""
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class GeminiResult:
    """Result from an image generation call."""

    def __init__(
        self,
        images: list[bytes],
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        model_name: str = "",
        duration_ms: int = 0,
    ):
        self.images = images
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.model_name = model_name
        self.duration_ms = duration_ms


def _encode_image_to_data_url(img_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """Encode raw image bytes to a base64 data URL."""
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def _decode_data_url(data_url: str) -> bytes:
    """Decode a base64 data URL back to raw bytes."""
    # Pattern: data:image/<type>;base64,<data>
    match = re.match(r"data:image/[^;]+;base64,(.+)", data_url, re.DOTALL)
    if not match:
        raise GeminiError(f"Invalid image data URL format: {data_url[:80]}...")
    return base64.b64decode(match.group(1))


def _call_openrouter(
    prompt_text: str,
    garment_image_bytes: list[bytes],
    model_name: str,
    variation_index: int = 0,
    model_photo_bytes: bytes | None = None,
    module: str = "adult",
    display_mode: str = "",
) -> tuple[bytes, dict]:
    """Make a single OpenRouter chat completion call that returns one image.

    If model_photo_bytes is provided it is included as the FIRST image in the
    multimodal payload (before the garment images) so the model can reference
    the real person's appearance.

    Args:
        module:       "adult", "children", "accessories", or "fiton".
        display_mode: For module="accessories" — "on_model", "flat_lay", or "lifestyle".
                      The camera angle is already injected into the prompt text by the
                      accessories prompt assembler, so this is informational only here.

    Returns:
        Tuple of (image_bytes, usage_dict).
    """
    if module == "accessories":
        # Camera angle text is already embedded in prompt_text by assemble_accessories_prompt().
        # No additional view instruction needed.
        view_instruction = ""
    elif module == "fiton":
        # Fit-on generates exactly one image; no camera-angle rotation.
        # The pose is determined by the customer reference photo.
        view_instruction = ""
    elif module == "children":
        views = CHILDREN_VARIATION_VIEWS
        view_instruction = views[variation_index % len(views)]
    else:
        views = VARIATION_VIEWS
        view_instruction = views[variation_index % len(views)]

    # Build the multimodal content: text prompt first, then images
    full_prompt = prompt_text + (f"\n\n{view_instruction}" if view_instruction else "")
    content_parts: list[dict] = [
        {"type": "text", "text": full_prompt},
    ]

    # Model reference photo goes first (if provided)
    if model_photo_bytes:
        data_url = _encode_image_to_data_url(model_photo_bytes)
        content_parts.append({"type": "image_url", "image_url": {"url": data_url}})

    for img_bytes in garment_image_bytes:
        data_url = _encode_image_to_data_url(img_bytes)
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": data_url},
        })

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": content_parts,
            }
        ],
        "modalities": ["image", "text"],
    }

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://drapestudio.app",
        "X-Title": "DrapeStudio",
    }

    # Use a generous timeout for image generation (120s)
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(OPENROUTER_API_URL, json=payload, headers=headers)

    # Handle HTTP errors
    if resp.status_code != 200:
        error_detail = resp.text[:500]
        logger.error(
            "OpenRouter API returned %d: %s", resp.status_code, error_detail
        )
        # 429 and 5xx are transient — mark as retryable
        retryable = resp.status_code in (429, 500, 502, 503, 504)
        raise GeminiError(
            f"OpenRouter API error (HTTP {resp.status_code}): {error_detail}",
            retryable=retryable,
        )

    data = resp.json()

    # Check for API-level errors
    if "error" in data:
        raise GeminiError(f"OpenRouter API error: {data['error']}")

    # Extract images from response
    choices = data.get("choices", [])
    if not choices:
        raise GeminiError("OpenRouter returned no choices in response.")

    message = choices[0].get("message", {})
    images_list = message.get("images", [])

    if not images_list:
        logger.warning(
            "No images in OpenRouter response. Message content: %s",
            str(message.get("content", ""))[:200],
        )
        raise GeminiError("OpenRouter returned no images in the response.")

    # Decode the first image from base64 data URL
    image_url = images_list[0].get("image_url", {}).get("url", "")
    if not image_url:
        raise GeminiError("Image data URL is empty in response.")

    image_bytes = _decode_data_url(image_url)

    # Extract usage metadata
    usage = data.get("usage", {})

    return image_bytes, usage


def generate_garment_images(
    garment_image_bytes: list[bytes],
    prompt_text: str,
    model_name: str | None = None,
    max_retries: int = 2,
    model_photo_bytes: bytes | None = None,
    module: str = "adult",
    output_count: int = 3,
    display_mode: str = "",
    prompt_texts: list[str] | None = None,
) -> GeminiResult:
    """Send garment images + text prompt to OpenRouter and return generated images.

    Makes ``output_count`` separate API calls to generate distinct image variations.
    Adult and children modules default to 3 images; accessories defaults to 2.

    Args:
        garment_image_bytes: List of garment image bytes (1-5 images).
        prompt_text: Assembled prompt string (used for all variations unless
                     prompt_texts is also supplied).
        model_name: OpenRouter model slug. Defaults to settings.OPENROUTER_MODEL.
        max_retries: Number of retries per call on transient errors.
        model_photo_bytes: Optional bytes of a real-person model reference photo.
                           When provided, it is prepended to the image list so the
                           AI can replicate the person's appearance.
        module: "adult", "children", "accessories", or "fiton".
        output_count: Number of image variations to generate (1 for fiton, 2 for accessories, 3 otherwise).
        display_mode: For module="accessories" — "on_model", "flat_lay", or "lifestyle".
        prompt_texts: Optional per-variation prompt list. When provided,
                      ``prompt_texts[i]`` is used for variation i instead of
                      ``prompt_text``. Used by the accessories module so each
                      variation carries its own camera angle instruction.

    Returns:
        GeminiResult with generated images and usage metadata.

    Raises:
        GeminiError: On persistent API failure.
    """
    if model_name is None:
        model_name = settings.OPENROUTER_MODEL

    if not settings.OPENROUTER_API_KEY:
        raise GeminiError("OPENROUTER_API_KEY is not configured.")

    all_images: list[bytes] = []
    total_input_tokens = 0
    total_output_tokens = 0
    start_time = time.time()

    # Generate image variations via separate API calls
    for variation_idx in range(output_count):
        last_error = None

        # Per-variation prompt: accessories supply a list; others use the single prompt
        current_prompt = (
            prompt_texts[variation_idx]
            if prompt_texts and variation_idx < len(prompt_texts)
            else prompt_text
        )

        for attempt in range(max_retries + 1):
            try:
                image_bytes, usage = _call_openrouter(
                    prompt_text=current_prompt,
                    garment_image_bytes=garment_image_bytes,
                    model_name=model_name,
                    variation_index=variation_idx,
                    model_photo_bytes=model_photo_bytes,
                    module=module,
                    display_mode=display_mode,
                )

                all_images.append(image_bytes)

                # Accumulate token usage
                total_input_tokens += usage.get("prompt_tokens", 0) or 0
                total_output_tokens += usage.get("completion_tokens", 0) or 0

                logger.info(
                    "OpenRouter variation %d/%d generated (%d bytes)",
                    variation_idx + 1,
                    output_count,
                    len(image_bytes),
                )
                break  # Success — move to next variation

            except GeminiError as e:
                if not e.retryable:
                    raise  # auth errors, bad requests, etc. — fail immediately
                last_error = e
                logger.warning(
                    "OpenRouter call %d (attempt %d/%d) failed: %s",
                    variation_idx + 1,
                    attempt + 1,
                    max_retries + 1,
                    str(e),
                )
                if attempt < max_retries:
                    # Use a longer backoff for rate limits (429)
                    wait_time = 15 * (2 ** attempt)  # 15s, 30s
                    logger.info("Retrying in %ds...", wait_time)
                    time.sleep(wait_time)

            except Exception as e:
                last_error = e
                logger.warning(
                    "OpenRouter call %d (attempt %d/%d) failed: %s",
                    variation_idx + 1,
                    attempt + 1,
                    max_retries + 1,
                    str(e),
                )
                if attempt < max_retries:
                    wait_time = 2 ** (attempt + 1)
                    logger.info("Retrying in %ds...", wait_time)
                    time.sleep(wait_time)
        else:
            # All retries exhausted for this variation
            raise GeminiError(
                f"OpenRouter failed for variation {variation_idx + 1}/{output_count} "
                f"after {max_retries + 1} attempts: {last_error}"
            )

    elapsed_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "OpenRouter generated %d images in %dms (tokens: %d/%d)",
        len(all_images),
        elapsed_ms,
        total_input_tokens,
        total_output_tokens,
    )

    return GeminiResult(
        images=all_images,
        input_tokens=total_input_tokens if total_input_tokens else None,
        output_tokens=total_output_tokens if total_output_tokens else None,
        model_name=model_name,
        duration_ms=elapsed_ms,
    )
