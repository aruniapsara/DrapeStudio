"""RQ worker job for image generation."""

import io
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.db import (
    GenerationOutput,
    GenerationRequest,
    UsageCost,
    generate_ulid,
)
from app.services.gemini import GeminiError, generate_garment_images
from app.services.prompt import assemble_prompt
from app.services.storage import storage

logger = logging.getLogger(__name__)

# Staleness threshold: if a job has been "running" for longer than this
# and the worker restarts, it's safe to retry from the beginning.
STALE_THRESHOLD = timedelta(minutes=5)

# Estimated cost per Gemini image generation call (rough estimate)
ESTIMATED_COST_PER_CALL_USD = Decimal("0.02")


def generate_images(generation_request_id: str) -> None:
    """Main RQ job: generate images for a given generation request.

    Steps:
        1. Set status = "running"
        2. Load generation_request from DB
        3. Fetch garment images from storage
        4. Load prompt template
        5. Assemble prompt
        6. Call Gemini API (with retry)
        7. Upload output images to storage
        8. Insert GenerationOutput rows
        9. Insert UsageCost row
        10. Set status = "succeeded"
    """
    db: Session = SessionLocal()

    try:
        # Step 2: Load generation request
        gen = (
            db.query(GenerationRequest)
            .filter(GenerationRequest.id == generation_request_id)
            .first()
        )

        if not gen:
            logger.error("Generation request not found: %s", generation_request_id)
            return

        # Check for stale running state (worker restart scenario)
        if gen.status == "running":
            if gen.updated_at and (datetime.utcnow() - gen.updated_at) < STALE_THRESHOLD:
                logger.info(
                    "Generation %s is already running (updated %s ago). Skipping.",
                    generation_request_id,
                    datetime.utcnow() - gen.updated_at,
                )
                return
            logger.warning(
                "Generation %s was running but stale. Restarting.",
                generation_request_id,
            )

        # Step 1: Set status = "running"
        gen.status = "running"
        gen.updated_at = datetime.utcnow()
        db.commit()

        # Step 3: Fetch garment images from storage
        garment_image_bytes_list = []
        for image_url in gen.garment_image_urls:
            try:
                img_data = storage.load(image_url)
                garment_image_bytes_list.append(img_data)
            except FileNotFoundError:
                _fail_generation(db, gen, f"Garment image not found: {image_url}")
                return

        if not garment_image_bytes_list:
            _fail_generation(db, gen, "No garment images could be loaded.")
            return

        # Step 4 & 5: Load template and assemble prompt
        try:
            prompt_text = assemble_prompt(
                model_params=gen.model_params,
                scene_params=gen.scene_params,
                template_version=gen.prompt_template_version,
            )
        except Exception as e:
            _fail_generation(db, gen, f"Prompt assembly failed: {e}")
            return

        # Load model reference photo (optional)
        model_photo_bytes = None
        model_photo_url = gen.model_params.get("model_photo_url")
        if model_photo_url:
            try:
                model_photo_bytes = storage.load(model_photo_url)
                logger.info(
                    "Generation %s: loaded model photo from %s",
                    generation_request_id,
                    model_photo_url,
                )
            except FileNotFoundError:
                logger.warning(
                    "Generation %s: model photo not found at %s — proceeding without it",
                    generation_request_id,
                    model_photo_url,
                )

        logger.info(
            "Generation %s: calling Gemini with %d garment image(s)%s, prompt length %d",
            generation_request_id,
            len(garment_image_bytes_list),
            " + model photo" if model_photo_bytes else "",
            len(prompt_text),
        )

        # Step 6: Call Gemini API
        try:
            result = generate_garment_images(
                garment_image_bytes=garment_image_bytes_list,
                prompt_text=prompt_text,
                model_photo_bytes=model_photo_bytes,
            )
        except GeminiError as e:
            _fail_generation(db, gen, f"Gemini API error: {e}")
            return
        except Exception as e:
            _fail_generation(db, gen, f"Unexpected error during generation: {e}")
            return

        # Step 7: Upload output images to storage
        output_paths = []
        for i, img_bytes in enumerate(result.images):
            output_path = f"outputs/{generation_request_id}/variation_{i}.jpg"
            storage.save(img_bytes, output_path)
            output_paths.append(output_path)

        # Step 8: Insert GenerationOutput rows
        for i, path in enumerate(output_paths):
            # Try to get image dimensions
            width, height = _get_image_dimensions(result.images[i])

            output = GenerationOutput(
                id=generate_ulid(),
                generation_request_id=generation_request_id,
                image_url=f"local://{path}" if settings.STORAGE_BACKEND == "local" else path,
                variation_index=i,
                width=width,
                height=height,
                created_at=datetime.utcnow(),
            )
            db.add(output)

        # Step 9: Insert UsageCost row
        usage = UsageCost(
            id=generate_ulid(),
            generation_request_id=generation_request_id,
            provider="google_gemini",
            model_name=result.model_name,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            estimated_cost_usd=ESTIMATED_COST_PER_CALL_USD,
            duration_ms=result.duration_ms,
            recorded_at=datetime.utcnow(),
        )
        db.add(usage)

        # Step 10: Set status = "succeeded"
        gen.status = "succeeded"
        gen.updated_at = datetime.utcnow()
        db.commit()

        logger.info(
            "Generation %s succeeded: %d images in %dms",
            generation_request_id,
            len(result.images),
            result.duration_ms,
        )

    except Exception as e:
        logger.exception("Unhandled error in generate_images job: %s", e)
        try:
            gen = (
                db.query(GenerationRequest)
                .filter(GenerationRequest.id == generation_request_id)
                .first()
            )
            if gen:
                _fail_generation(db, gen, f"Unhandled error: {e}")
        except Exception:
            pass
    finally:
        db.close()


def _fail_generation(db: Session, gen: GenerationRequest, error_message: str) -> None:
    """Mark a generation as failed with an error message."""
    logger.error("Generation %s failed: %s", gen.id, error_message)
    gen.status = "failed"
    gen.error_message = error_message
    gen.updated_at = datetime.utcnow()
    db.commit()


def _get_image_dimensions(img_bytes: bytes) -> tuple[int | None, int | None]:
    """Try to get width and height from image bytes using Pillow."""
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(img_bytes))
        return img.width, img.height
    except Exception:
        return None, None
