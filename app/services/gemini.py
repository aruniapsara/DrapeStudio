"""Image generation service via Google Gemini API (direct SDK)."""

import io
import logging
import time

from PIL import Image
from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)

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
    ],
    "flat_lay": [
        "CAMERA ANGLE FOR THIS IMAGE: Overhead (top-down) at 90 degrees.",
    ],
    "lifestyle": [
        "CAMERA ANGLE FOR THIS IMAGE: Wide contextual scene.",
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


def _bytes_to_pil(img_bytes: bytes) -> Image.Image:
    """Convert raw image bytes to a PIL Image."""
    return Image.open(io.BytesIO(img_bytes))


def _pil_to_bytes(pil_image: Image.Image, fmt: str = "JPEG") -> bytes:
    """Convert a PIL Image to raw bytes."""
    buf = io.BytesIO()
    pil_image.save(buf, format=fmt)
    return buf.getvalue()


def _call_gemini(
    prompt_text: str,
    garment_image_bytes: list[bytes],
    model_name: str,
    variation_index: int = 0,
    model_photo_bytes: bytes | None = None,
    module: str = "adult",
    display_mode: str = "",
    system_instruction: str | None = None,
) -> tuple[bytes, dict]:
    """Make a single Google Gemini API call that returns one image.

    Args:
        prompt_text:         The assembled text prompt.
        garment_image_bytes: List of garment image bytes.
        model_name:          Gemini model name.
        variation_index:     Which camera angle variation (0, 1, 2).
        model_photo_bytes:   Optional model reference photo bytes.
        module:              "adult", "children", "accessories", or "fiton".
        display_mode:        For accessories — "on_model", "flat_lay", or "lifestyle".
        system_instruction:  Optional system-level instruction (used for fiton identity preservation).

    Returns:
        Tuple of (image_bytes, usage_dict).
    """
    # Determine camera angle instruction
    if module == "accessories":
        view_instruction = ""
    elif module == "fiton":
        view_instruction = ""
    elif module == "children":
        views = CHILDREN_VARIATION_VIEWS
        view_instruction = views[variation_index % len(views)]
    else:
        views = VARIATION_VIEWS
        view_instruction = views[variation_index % len(views)]

    # Build the full prompt with camera angle
    full_prompt = prompt_text + (f"\n\n{view_instruction}" if view_instruction else "")

    # Build the contents list: text + images (PIL Image objects)
    # For fiton module: add explicit image labels so Gemini knows which
    # image is the customer reference and which is the garment
    contents: list = []

    if module == "fiton" and model_photo_bytes:
        # Fiton: customer photo FIRST with explicit label, then garment
        contents.append(
            "CUSTOMER REFERENCE PHOTO — This is the real person. "
            "You MUST preserve this EXACT person's face, skin tone, hair, "
            "and all physical features in the generated image:"
        )
        contents.append(_bytes_to_pil(model_photo_bytes))
        contents.append(
            "GARMENT PHOTO — Put this garment on the customer shown above:"
        )
        for img_bytes in garment_image_bytes:
            contents.append(_bytes_to_pil(img_bytes))
        contents.append(full_prompt)
    else:
        # Non-fiton modules: original order (prompt first, then images)
        contents.append(full_prompt)
        if model_photo_bytes:
            contents.append(_bytes_to_pil(model_photo_bytes))
        for img_bytes in garment_image_bytes:
            contents.append(_bytes_to_pil(img_bytes))

    # Create the Gemini client
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    # Determine aspect ratio per module
    # - adult/children/fiton: 3:4 portrait (ideal for fashion catalogue)
    # - accessories: 1:1 square (product-focused)
    if module == "accessories":
        aspect_ratio = "1:1"
    else:
        aspect_ratio = "3:4"

    # Build config — include system_instruction for fiton identity preservation
    config_kwargs = {
        "response_modalities": ["TEXT", "IMAGE"],
        "image_config": types.ImageConfig(aspect_ratio=aspect_ratio),
    }
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction

    # Call the API with image generation config
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )
    except Exception as exc:
        error_msg = str(exc)
        logger.error("Gemini API call failed: %s", error_msg)

        # Check for retryable errors
        retryable = any(
            keyword in error_msg.lower()
            for keyword in ("rate limit", "429", "500", "503", "504", "overloaded", "quota")
        )
        raise GeminiError(f"Gemini API error: {error_msg}", retryable=retryable)

    # Extract image from response
    image_bytes = None
    if response.candidates:
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                # Get raw bytes directly from inline_data
                image_bytes = part.inline_data.data
                break

    if not image_bytes:
        # Try alternate extraction via text content for debugging
        text_content = ""
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.text:
                    text_content = part.text[:200]
        logger.warning(
            "No images in Gemini response. Text content: %s", text_content
        )
        raise GeminiError("Gemini returned no images in the response.")

    # Extract usage metadata
    usage = {}
    if response.usage_metadata:
        usage = {
            "prompt_tokens": response.usage_metadata.prompt_token_count,
            "completion_tokens": response.usage_metadata.candidates_token_count,
        }

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
    system_instruction: str | None = None,
) -> GeminiResult:
    """Send garment images + text prompt to Google Gemini and return generated images.

    Makes ``output_count`` separate API calls to generate distinct image variations.
    Adult and children modules default to 3 images; accessories defaults to 2.

    Args:
        garment_image_bytes: List of garment image bytes (1-5 images).
        prompt_text: Assembled prompt string (used for all variations unless
                     prompt_texts is also supplied).
        model_name: Gemini model name. Defaults to settings.GEMINI_IMAGE_MODEL.
        max_retries: Number of retries per call on transient errors.
        model_photo_bytes: Optional bytes of a real-person model reference photo.
        module: "adult", "children", "accessories", or "fiton".
        output_count: Number of image variations to generate.
        display_mode: For module="accessories" — "on_model", "flat_lay", or "lifestyle".
        prompt_texts: Optional per-variation prompt list.
        system_instruction: Optional system-level instruction for identity preservation (fiton).

    Returns:
        GeminiResult with generated images and usage metadata.

    Raises:
        GeminiError: On persistent API failure.
    """
    if model_name is None:
        model_name = settings.GEMINI_IMAGE_MODEL

    if not settings.GOOGLE_API_KEY:
        raise GeminiError("GOOGLE_API_KEY is not configured.")

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
                image_bytes, usage = _call_gemini(
                    prompt_text=current_prompt,
                    garment_image_bytes=garment_image_bytes,
                    model_name=model_name,
                    variation_index=variation_idx,
                    model_photo_bytes=model_photo_bytes,
                    module=module,
                    display_mode=display_mode,
                    system_instruction=system_instruction,
                )

                all_images.append(image_bytes)

                # Accumulate token usage
                total_input_tokens += usage.get("prompt_tokens", 0) or 0
                total_output_tokens += usage.get("completion_tokens", 0) or 0

                logger.info(
                    "Gemini variation %d/%d generated (%d bytes)",
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
                    "Gemini call %d (attempt %d/%d) failed: %s",
                    variation_idx + 1,
                    attempt + 1,
                    max_retries + 1,
                    str(e),
                )
                if attempt < max_retries:
                    wait_time = 15 * (2 ** attempt)  # 15s, 30s
                    logger.info("Retrying in %ds...", wait_time)
                    time.sleep(wait_time)

            except Exception as e:
                last_error = e
                logger.warning(
                    "Gemini call %d (attempt %d/%d) failed: %s",
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
                f"Gemini failed for variation {variation_idx + 1}/{output_count} "
                f"after {max_retries + 1} attempts: {last_error}"
            )

    elapsed_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "Gemini generated %d images in %dms (tokens: %d/%d)",
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
