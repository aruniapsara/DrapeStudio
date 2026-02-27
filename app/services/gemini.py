"""Gemini API wrapper — call and parse response for image generation."""

import logging
import time

import google.generativeai as genai

from app.config import settings

logger = logging.getLogger(__name__)

# Configure the Gemini API key
genai.configure(api_key=settings.GOOGLE_API_KEY)


class GeminiError(Exception):
    """Custom exception for Gemini API errors."""
    pass


class GeminiResult:
    """Result from a Gemini image generation call."""

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


def generate_garment_images(
    garment_image_bytes: list[bytes],
    prompt_text: str,
    model_name: str = "gemini-2.0-flash-exp-image-generation",
    max_retries: int = 2,
) -> GeminiResult:
    """Send garment images + text prompt to Gemini and return generated images.

    Args:
        garment_image_bytes: List of garment image bytes (1-5 images).
        prompt_text: Assembled prompt string.
        model_name: Gemini model to use.
        max_retries: Number of retries on transient errors.

    Returns:
        GeminiResult with generated images and usage metadata.

    Raises:
        GeminiError: On persistent API failure.
    """
    model = genai.GenerativeModel(model_name)

    # Build parts: all garment images first, then the text prompt
    parts = []
    for img_bytes in garment_image_bytes:
        parts.append({"mime_type": "image/jpeg", "data": img_bytes})
    parts.append(prompt_text)

    last_error = None
    start_time = time.time()

    for attempt in range(max_retries + 1):
        try:
            response = model.generate_content(
                contents=parts,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="image/jpeg",
                    candidate_count=3,
                ),
            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Extract image bytes from response
            images = []
            for candidate in response.candidates:
                if hasattr(candidate, "content") and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, "inline_data") and part.inline_data:
                            images.append(part.inline_data.data)

            # If we got fewer than expected, also check top-level parts
            if not images and hasattr(response, "parts"):
                for part in response.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        images.append(part.inline_data.data)

            if not images:
                logger.warning(
                    "Gemini response contained no images. "
                    "Response structure: %s",
                    type(response).__name__,
                )
                raise GeminiError("Gemini returned no images in the response.")

            # Extract token usage if available
            input_tokens = None
            output_tokens = None
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = response.usage_metadata
                input_tokens = getattr(usage, "prompt_token_count", None)
                output_tokens = getattr(usage, "candidates_token_count", None)

            logger.info(
                "Gemini generated %d images in %dms (tokens: %s/%s)",
                len(images),
                elapsed_ms,
                input_tokens,
                output_tokens,
            )

            return GeminiResult(
                images=images,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model_name=model_name,
                duration_ms=elapsed_ms,
            )

        except GeminiError:
            raise  # Don't retry our own errors

        except Exception as e:
            last_error = e
            logger.warning(
                "Gemini API attempt %d/%d failed: %s",
                attempt + 1,
                max_retries + 1,
                str(e),
            )
            if attempt < max_retries:
                # Exponential back-off: 2s, 4s
                wait_time = 2 ** (attempt + 1)
                logger.info("Retrying in %ds...", wait_time)
                time.sleep(wait_time)

    raise GeminiError(
        f"Gemini API failed after {max_retries + 1} attempts: {last_error}"
    )
