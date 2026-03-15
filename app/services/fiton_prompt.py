"""Fit-On prompt builder for DrapeStudio Virtual Fit-On module.

Loads the YAML template (``app/config/prompts/fiton_v1.yaml``) and assembles
the image generation prompt for a given garment type and customer description.

Garment description fields (color, details) are sanitized at the Pydantic
schema layer (``FitonParamsCreate``) before reaching this module, and are
additionally boundary-quoted here as a defence-in-depth measure.

Usage::

    from app.services.fiton_prompt import FitonPromptBuilder

    builder = FitonPromptBuilder()
    prompt_data = builder.build_prompt(
        garment_type="dress",
        customer_measurements={"bust_cm": 88, "waist_cm": 70, "hips_cm": 96,
                               "height_cm": 163, "skin_tone": "medium", "gender": "female"},
        fit_preference="regular",
        fit_details={"bust": "good", "waist": "good", "hips": "slightly loose"},
    )
    # prompt_data["prompt"]         → assembled text prompt
    # prompt_data["negative_prompt"] → negative prompt string
    # prompt_data["system_context"] → system context for the AI
    # prompt_data["num_images"]     → always 1 for fit-on
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from app.services.input_sanitizer import quote_user_text_for_prompt


# ---------------------------------------------------------------------------
# Valid garment type keys
# ---------------------------------------------------------------------------
VALID_GARMENT_TYPES = frozenset(["dress", "top", "saree", "bottom", "full_outfit"])


class FitonPromptBuilder:
    """Builds image generation prompts for the Virtual Fit-On module.

    Loads the versioned YAML template on first instantiation.  The template
    lives at ``app/config/prompts/fiton_v1.yaml`` relative to the project.
    """

    _config_path = (
        Path(__file__).parent.parent / "config" / "prompts" / "fiton_v1.yaml"
    )

    def __init__(self) -> None:
        with open(self._config_path, encoding="utf-8") as f:
            self.config: dict = yaml.safe_load(f)["fiton"]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    # Scene descriptions for fiton — maps scene keys to natural-language phrases.
    SCENE_DESCRIPTIONS: dict[str, str] = {
        "studio_white":   "in a professional white studio with soft, even lighting",
        "studio_grey":    "in a neutral grey studio backdrop with professional lighting",
        "urban_street":   "on an urban street with modern architecture in the background",
        "outdoor_garden": "in a lush green garden with natural sunlight",
        "beach":          "on a sandy beach with ocean waves in the background",
        "coffee_shop":    "in a cozy modern coffee shop with warm ambient lighting",
        "office":         "in a bright, modern office space with clean interiors",
        "living_room":    "in a stylish contemporary living room with natural light",
        "traditional":    "in a traditional Sri Lankan interior with cultural decor",
        "runway":         "on a fashion runway with dramatic spotlight lighting",
    }

    def build_prompt(
        self,
        garment_type: str,
        customer_measurements: dict,
        fit_preference: str = "regular",
        fit_details: Optional[dict] = None,
        garment_description: Optional[dict] = None,
        scene: str = "studio_white",
        custom_text: str = "",
    ) -> dict:
        """Build the prompt payload for fit-on image generation.

        Args:
            garment_type:          "dress" | "top" | "saree" | "bottom" | "full_outfit".
                                   Falls back to "dress" for unknown types.
            customer_measurements: Dict with at least bust_cm, waist_cm, hips_cm,
                                   height_cm, skin_tone, gender.
            fit_preference:        "tight" | "regular" | "loose" (default "regular").
            fit_details:           Per-measurement fit labels from the sizing service.
                                   When provided, overrides fit_preference description.
            garment_description:   Optional dict with "color", "material", "details".
            scene:                 Scene/environment key (e.g. "studio_white", "urban_street").
            custom_text:           Optional custom text to append to the prompt.

        Returns:
            Dict with keys: prompt, negative_prompt, system_context, num_images.
        """
        garment_description = garment_description or {}

        # 1. Resolve garment type — fallback to dress for unknown types
        garment_types = self.config["garment_types"]
        type_key = garment_type if garment_type in garment_types else "dress"
        template = garment_types[type_key]

        # 2. Build customer natural-language description
        customer_desc = self._build_customer_description(customer_measurements)

        # 3. Build fit description
        if fit_details:
            fit_desc = self._build_detailed_fit_description(fit_details)
        else:
            fit_desc = self.config["fit_descriptions"].get(
                fit_preference,
                self.config["fit_descriptions"]["regular"],
            )

        # 4. Build optional garment extra details line
        garment_extra = self._build_garment_extra(garment_description)

        # 5. Build scene description
        scene_desc = self.SCENE_DESCRIPTIONS.get(
            scene, self.SCENE_DESCRIPTIONS["studio_white"]
        )

        # 6. Build custom text line (sanitized at schema layer, quoted here)
        custom_line = ""
        if custom_text and custom_text.strip():
            quoted = quote_user_text_for_prompt(custom_text.strip())
            custom_line = f"Additional styling notes: {quoted}."

        # 7. Format the prompt template
        raw_prompt = template["prompt_template"].format(
            customer_description=customer_desc,
            fit_description=fit_desc,
            garment_extra=garment_extra,
        )

        # 8. Append scene and custom text after the main prompt
        raw_prompt += f"\nSCENE: The photo is taken {scene_desc}."
        if custom_line:
            raw_prompt += f"\n{custom_line}"

        # 9. Prepend identity preservation instructions (critical for fit-on)
        identity_block = self.config.get("identity_preservation", "").strip()
        if identity_block:
            raw_prompt = f"{identity_block}\n\n{raw_prompt}"

        # 10. Append negative prompt directly into the prompt text
        #     (Gemini doesn't have a separate negative_prompt field — it must
        #     be embedded in the prompt text like the other modules do)
        negative = self.config["negative_prompt"].strip()
        if negative:
            raw_prompt += f"\n\nNEGATIVE (avoid ALL of these):\n{negative}"

        # Clean up formatting artefacts from optional placeholders
        prompt = self._clean_prompt(raw_prompt)

        return {
            "prompt":          prompt,
            "negative_prompt": negative,
            "system_context":  self.config["system_context"].strip(),
            "num_images":      1,  # fit-on always generates exactly 1 image
        }

    def validate_customer_photo(self, metadata: dict) -> tuple[bool, str]:
        """Validate that customer photo metadata contains no blocked terms.

        Args:
            metadata: Dict of arbitrary key→value pairs describing the photo
                      or the request (e.g. filename, tags, caption, etc.).

        Returns:
            Tuple ``(is_valid, message)`` — is_valid is True when safe.
        """
        blocked: list[str] = self.config["safety"]["blocked_terms"]
        for key, value in metadata.items():
            if isinstance(value, str):
                for term in blocked:
                    if term.lower() in value.lower():
                        return False, f"Customer photo contains blocked term: '{term}'"
        return True, "OK"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_customer_description(self, measurements: dict) -> str:
        """Build a natural-language customer description from measurements."""
        height_cm = measurements.get("height_cm", 160.0)

        if height_cm < 155:
            height_desc = "petite"
        elif height_cm < 165:
            height_desc = "average"
        elif height_cm < 175:
            height_desc = "tall"
        else:
            height_desc = "very tall"

        waist_cm = measurements.get("waist_cm", 72.0)
        gender = measurements.get("gender", "female")

        if waist_cm < 66:
            build = "slim"
        elif waist_cm < 78:
            build = "medium"
        elif waist_cm < 90:
            build = "curvy" if gender == "female" else "athletic"
        else:
            build = "plus-size" if gender == "female" else "heavy build"

        template: str = self.config["customer_description_template"]
        return template.format(
            gender=measurements.get("gender", "female"),
            skin_tone=measurements.get("skin_tone", "medium"),
            build=build,
            height_desc=height_desc,
        ).strip()

    def _build_detailed_fit_description(self, fit_details: dict) -> str:
        """Convert per-measurement fit labels into natural language.

        Args:
            fit_details: e.g. {"bust": "good", "waist": "tight", "hips": "slightly loose"}

        Returns:
            Human-readable string such as "with waist area is snug, hips area has some ease".
        """
        parts: list[str] = []
        for measurement, status in fit_details.items():
            if status == "tight":
                parts.append(f"{measurement} area is snug")
            elif status == "loose":
                parts.append(f"{measurement} area is relaxed")
            elif status == "slightly loose":
                parts.append(f"{measurement} area has some ease")
            # "good" → no annotation needed (perfect fit)

        if parts:
            return "with " + ", ".join(parts)
        return "comfortably"

    def _build_garment_extra(self, garment_description: dict) -> str:
        """Build an optional extra sentence describing the garment's visual attributes.

        User-supplied text (color, details) is boundary-quoted as a
        defence-in-depth measure against prompt injection. Primary
        sanitization happens at the Pydantic schema layer.
        """
        if not garment_description:
            return ""

        color    = garment_description.get("color", "").strip()
        material = garment_description.get("material", "").strip()
        details  = garment_description.get("details", "").strip()

        # Quote user-supplied free-text fields
        color = quote_user_text_for_prompt(color) if color else ""
        details = quote_user_text_for_prompt(details) if details else ""

        desc_parts = [p for p in [color, material] if p]
        desc_str = " ".join(desc_parts)

        if desc_str and details:
            return f"The garment is {desc_str} with {details}."
        elif desc_str:
            return f"The garment is {desc_str}."
        elif details:
            return f"Garment details: {details}."
        return ""

    @staticmethod
    def _clean_prompt(prompt: str) -> str:
        """Strip excessive whitespace and blank lines from a formatted prompt."""
        import re
        # Collapse multiple consecutive whitespace/newline sequences into a single space
        prompt = re.sub(r"\s+", " ", prompt)
        return prompt.strip()
