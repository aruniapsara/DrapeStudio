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
from app.services.prompt import (
    assemble_prompt,
    assemble_children_prompt,
    assemble_accessories_prompt,
    load_children_template,
    load_accessories_template,
)
from app.services.storage import storage

logger = logging.getLogger(__name__)

# Staleness threshold: if a job has been "running" for longer than this
# and the worker restarts, it's safe to retry from the beginning.
STALE_THRESHOLD = timedelta(minutes=5)

# Estimated cost per Gemini image generation call
# Based on Gemini 3.1 Flash Image: ~1,120 output tokens at 1K = $0.067/image
ESTIMATED_COST_PER_CALL_USD = Decimal("0.07")


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

        # Step 4 & 5: Load template and assemble prompt (module-aware)
        module = gen.module or "adult"

        # Determine output image count and views
        display_mode = ""
        views_list = ["front"]  # default
        selected_quality = "1k"  # default
        if module == "accessories":
            output_count = 1
            display_mode = gen.scene_params.get("display_mode", "on_model")
        elif module == "fiton":
            output_count = 1
        else:
            output_count = gen.output_count or 3
            views_list = gen.scene_params.get("views", ["front"])
            selected_quality = gen.scene_params.get("quality", "1k")
            # Ensure output_count matches views
            if len(views_list) > 0:
                output_count = len(views_list)

        adult_prompts = None  # Only set for adult module with multiple views
        try:
            if module == "accessories":
                # Accessories module: rebuild accessory_params dict from stored JSON
                accessory_params_for_prompt = {
                    "accessory_category": gen.model_params.get("accessory_category", "necklace"),
                    "display_mode":       display_mode,
                    "model_skin_tone":    gen.model_params.get("model_skin_tone", ""),
                    "background_surface": gen.model_params.get("background_surface", ""),
                    "context_scene":      gen.model_params.get("context_scene", ""),
                    "accessory_size":     gen.model_params.get("accessory_size", ""),
                }
                # Assemble single prompt (1 image per accessories generation)
                accessories_template = load_accessories_template()
                prompt_text = assemble_accessories_prompt(
                    template=accessories_template,
                    accessory_params=accessory_params_for_prompt,
                    variation_index=0,
                )
                accessory_prompts = [prompt_text]
                logger.info(
                    "Generation %s (accessories/%s/%s): prompt assembled (%d chars)",
                    generation_request_id,
                    accessory_params_for_prompt.get("accessory_category"),
                    display_mode,
                    len(prompt_text),
                )

            elif module == "children":
                # Children's module: combine model_params + scene_params into
                # a single child_params dict for the children's prompt assembler
                child_params_for_prompt = {
                    "age_group":         gen.model_params.get("age_group", "kid"),
                    "child_gender":      gen.model_params.get("child_gender", "unisex"),
                    "pose_style":        gen.scene_params.get("pose_style", "standing"),
                    "background_preset": gen.scene_params.get("background_preset", "studio"),
                    "hair_style":        gen.model_params.get("hair_style", ""),
                    "expression":        gen.model_params.get("expression", "happy"),
                    "skin_tone":         gen.model_params.get("skin_tone", "medium"),
                }
                children_template = load_children_template()
                prompt_text = assemble_children_prompt(
                    template=children_template,
                    child_params=child_params_for_prompt,
                )
                logger.info(
                    "Generation %s (children/%s): prompt assembled (%d chars)",
                    generation_request_id,
                    child_params_for_prompt.get("age_group"),
                    len(prompt_text),
                )

            elif module == "fiton":
                # Fiton module: build prompt via FitonPromptBuilder
                from app.services.fiton_prompt import FitonPromptBuilder
                from app.models.db import FitonRequest as FitonRequestModel

                garment_type = gen.model_params.get("garment_type", "dress")
                customer_measurements = gen.model_params.get("customer_measurements", {})
                fit_preference = gen.model_params.get("fit_preference", "regular")
                garment_description = gen.model_params.get("garment_description") or {}

                # Load fit_details from the FitonRequest record (computed at API time)
                fiton_record = (
                    db.query(FitonRequestModel)
                    .filter(FitonRequestModel.generation_request_id == gen.id)
                    .first()
                )
                fit_details = fiton_record.fit_details if fiton_record else {}

                builder = FitonPromptBuilder()
                prompt_data = builder.build_prompt(
                    garment_type=garment_type,
                    customer_measurements=customer_measurements,
                    fit_preference=fit_preference,
                    fit_details=fit_details,
                    garment_description=garment_description,
                )
                prompt_text = prompt_data["prompt"]
                logger.info(
                    "Generation %s (fiton/%s): prompt assembled (%d chars)",
                    generation_request_id,
                    garment_type,
                    len(prompt_text),
                )

            else:
                # Adult module: generate per-view prompts if multiple views
                if len(views_list) > 1:
                    view_angle_instructions = {
                        "front": "Camera angle: FRONT VIEW — facing directly toward the camera.",
                        "side": "Camera angle: SIDE VIEW — model turned 90 degrees, profile view.",
                        "back": "Camera angle: BACK VIEW — model turned away, showing the garment from behind.",
                    }
                    adult_prompts = []
                    for view in views_list:
                        base_prompt = assemble_prompt(
                            model_params=gen.model_params,
                            scene_params=gen.scene_params,
                            template_version=gen.prompt_template_version,
                        )
                        angle_instruction = view_angle_instructions.get(view, "")
                        if angle_instruction:
                            base_prompt = angle_instruction + "\n\n" + base_prompt
                        adult_prompts.append(base_prompt)
                    prompt_text = adult_prompts[0]
                else:
                    adult_prompts = None
                    prompt_text = assemble_prompt(
                        model_params=gen.model_params,
                        scene_params=gen.scene_params,
                        template_version=gen.prompt_template_version,
                    )
        except Exception as e:
            _fail_generation(db, gen, f"Prompt assembly failed: {e}")
            return

        # Load reference photo:
        #   - adult module: optional model reference photo (model_photo_url)
        #   - fiton module: customer photo to preserve appearance (customer_photo_url)
        model_photo_bytes = None
        if module == "fiton":
            photo_url = gen.model_params.get("customer_photo_url")
        else:
            photo_url = gen.model_params.get("model_photo_url")

        if photo_url:
            try:
                model_photo_bytes = storage.load(photo_url)
                logger.info(
                    "Generation %s: loaded reference photo from %s",
                    generation_request_id,
                    photo_url,
                )
            except FileNotFoundError:
                logger.warning(
                    "Generation %s: reference photo not found at %s — proceeding without it",
                    generation_request_id,
                    photo_url,
                )

        logger.info(
            "Generation %s: calling Gemini with %d garment image(s)%s, module=%s, prompt length %d",
            generation_request_id,
            len(garment_image_bytes_list),
            " + model photo" if model_photo_bytes else "",
            module,
            len(prompt_text),
        )

        # Step 6: Call Gemini API (pass module + output_count + display_mode)
        try:
            extra_kwargs = {}
            if module == "accessories":
                # Pass both prompts (one per camera angle) so each variation
                # gets the correct angle instruction embedded in its prompt text.
                extra_kwargs["prompt_texts"] = accessory_prompts
                extra_kwargs["display_mode"] = display_mode
            elif module == "adult" and adult_prompts is not None:
                # Multiple views: pass per-view prompts so each gets the right angle
                extra_kwargs["prompt_texts"] = adult_prompts

            result = generate_garment_images(
                garment_image_bytes=garment_image_bytes_list,
                prompt_text=prompt_text,
                model_photo_bytes=model_photo_bytes,
                module=module,
                output_count=output_count,
                **extra_kwargs,
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
        # Cost scales with number of images generated
        total_usd_cost = ESTIMATED_COST_PER_CALL_USD * len(result.images)
        usage = UsageCost(
            id=generate_ulid(),
            generation_request_id=generation_request_id,
            provider="google_gemini",
            model_name=result.model_name,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            estimated_cost_usd=total_usd_cost,
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

        # Step 11: Send completion notifications (push + SMS)
        if gen.user_id:
            try:
                from app.models.db import User
                from app.services.notification import notification_service
                user_obj = db.query(User).filter_by(id=gen.user_id).first()
                notification_service.notify_generation_complete(
                    user=user_obj,
                    generation_id=generation_request_id,
                    module=gen.module or "adult",
                    db=db,
                )
            except Exception as exc:
                logger.warning("Notification step failed for %s: %s", generation_request_id, exc)

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
    """Mark a generation as failed with an error message and refund wallet."""
    logger.error("Generation %s failed: %s", gen.id, error_message)
    gen.status = "failed"
    gen.error_message = error_message
    gen.updated_at = datetime.utcnow()
    db.commit()

    # Refund wallet deduction if user was charged
    if gen.user_id:
        try:
            from app.services.wallet import WalletService
            refund_tx = WalletService.refund(gen.user_id, gen.id, db)
            if refund_tx:
                logger.info(
                    "Generation %s: wallet refund of Rs. %d applied",
                    gen.id, refund_tx.amount_lkr,
                )
        except Exception as exc:
            logger.warning(
                "Generation %s: wallet refund failed: %s", gen.id, exc
            )


def _get_image_dimensions(img_bytes: bytes) -> tuple[int | None, int | None]:
    """Try to get width and height from image bytes using Pillow."""
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(img_bytes))
        return img.width, img.height
    except Exception:
        return None, None


# ── Scheduled cleanup job ────────────────────────────────────────────────────

def run_scheduled_cleanup() -> None:
    """Run the full image cleanup and re-enqueue itself for the next cycle.

    This function is enqueued as an RQ job. After completing the cleanup
    it schedules itself to run again after CLEANUP_INTERVAL_SECONDS.
    """
    try:
        from app.services.cleanup import run_full_cleanup
        summary = run_full_cleanup()
        logger.info("Scheduled cleanup completed: %s", summary)
    except Exception as exc:
        logger.exception("Scheduled cleanup failed: %s", exc)

    # Re-enqueue self for next cycle
    try:
        import redis as redis_lib
        from rq import Queue

        redis_conn = redis_lib.from_url(settings.REDIS_URL)
        queue = Queue("drapestudio", connection=redis_conn)
        queue.enqueue_in(
            timedelta(seconds=settings.CLEANUP_INTERVAL_SECONDS),
            "app.worker.jobs.run_scheduled_cleanup",
            job_timeout=300,
        )
        logger.info(
            "Next cleanup scheduled in %d seconds", settings.CLEANUP_INTERVAL_SECONDS
        )
    except Exception as exc:
        logger.warning("Failed to re-enqueue cleanup job: %s", exc)
