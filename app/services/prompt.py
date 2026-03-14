"""Prompt template loading and assembly service."""

from pathlib import Path

import yaml

from app.services.input_sanitizer import quote_user_text_for_prompt

# Prompt templates directory (project root / prompts/)
PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

# Template file map — keyed by module or version string
_TEMPLATE_FILES: dict[str, str] = {
    # Version-keyed (legacy adult templates)
    "v0.1":         "v0_1.yaml",
    "v0_1":         "v0_1.yaml",
    # Module-keyed
    "adult":        "v0_1.yaml",
    "children":     "children_v1.yaml",
    "accessories":  "accessories_v1.yaml",
}

# In-process template cache
_template_cache: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

def load_template(version: str = "v0.1") -> dict:
    """Load a prompt template YAML file by version string.

    Backward-compatible: accepts both version strings ("v0.1") and
    module names ("adult", "children").
    """
    if version in _template_cache:
        return _template_cache[version]

    filename = _TEMPLATE_FILES.get(version)
    if filename is None:
        # Fall back to the old behaviour: replace dots with underscores
        filename = version.replace(".", "_") + ".yaml"

    filepath = PROMPTS_DIR / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Prompt template not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        template = yaml.safe_load(f)

    _template_cache[version] = template
    return template


def load_children_template() -> dict:
    """Load the children's prompt template (children_v1.yaml)."""
    return load_template("children")


def load_accessories_template() -> dict:
    """Load the accessories prompt template (accessories_v1.yaml)."""
    return load_template("accessories")


# ---------------------------------------------------------------------------
# Adult prompt assembly (unchanged)
# ---------------------------------------------------------------------------

def _build_measurements_text(measurements: dict) -> str:
    """Assemble a readable measurements string. Returns '' if nothing provided."""
    if not measurements:
        return ""
    parts = []
    if measurements.get("height_cm"):
        parts.append(f"{measurements['height_cm']} cm tall")
    if measurements.get("weight_kg"):
        parts.append(f"{measurements['weight_kg']} kg")
    if measurements.get("chest_bust_cm"):
        parts.append(f"chest/bust {measurements['chest_bust_cm']} cm")
    if measurements.get("waist_cm"):
        parts.append(f"waist {measurements['waist_cm']} cm")
    if measurements.get("hips_cm"):
        parts.append(f"hips {measurements['hips_cm']} cm")
    if measurements.get("inseam_cm"):
        parts.append(f"inseam {measurements['inseam_cm']} cm")
    if measurements.get("shoe_size_eu"):
        parts.append(f"shoe size EU {measurements['shoe_size_eu']}")
    return ", ".join(parts)


# Human-readable body type descriptions for prompt generation.
# Maps option IDs to natural-language descriptions used in the prompt.
BODY_TYPE_DESCRIPTIONS = {
    "slim": "slim build",
    "average": "average build",
    "curvy": "curvy, fuller figure",
    "plus_size": "plus-size, fuller figure",
    "athletic": "athletic, muscular build",
    "heavy": "heavy, broad muscular build",
    "plus": "plus-size build",  # legacy value from older sessions
}


def assemble_prompt(
    model_params: dict,
    scene_params: dict,
    template_version: str = "v0.1",
) -> str:
    """Assemble a full adult prompt string from template and user parameters."""
    template = load_template(template_version)

    # Scene
    environment = scene_params.get("environment", "studio_white")
    pose_preset = scene_params.get("pose_preset", "front_standing")
    framing = scene_params.get("framing", "full_body")
    env_desc = template.get("environments", {}).get(environment, environment)
    pose_desc = template.get("poses", {}).get(pose_preset, pose_preset)
    framing_desc = template.get("framing", {}).get(framing, framing)
    lighting_desc = template.get("lighting", {}).get(environment, "")

    # Product type
    product_type = model_params.get("product_type", "clothing")
    pt_desc = template.get("product_types", {}).get(
        product_type, "wearing the garment shown in the reference image(s)"
    )

    # Measurements
    raw_measurements = model_params.get("measurements") or {}
    if hasattr(raw_measurements, "model_dump"):
        raw_measurements = raw_measurements.model_dump()
    measure_text = _build_measurements_text(raw_measurements)

    quality = template.get("quality", "").strip()
    output_instructions = template.get("output", "").strip()
    negative = template.get("negative", "").strip()

    # Model photo vs virtual model
    model_photo_url = model_params.get("model_photo_url")

    if model_photo_url:
        intro = (
            "Generate a photorealistic catalogue image of the PERSON shown in the "
            f"first reference image (model reference photo), {pt_desc}."
        )
        model_line = (
            "MODEL: Use the exact appearance, face, skin tone, and body proportions "
            "of the person in the model reference photo. Do not alter or idealise their appearance."
        )
        if measure_text:
            model_line += f" Reference measurements: {measure_text}."
    else:
        age_range = model_params.get("age_range", "25-34")
        gender = model_params.get("gender_presentation", "feminine")
        skin_tone = model_params.get("skin_tone", "4")
        body_type = model_params.get("body_type", "average")
        hair_style = model_params.get("hair_style", "")
        hair_color = model_params.get("hair_color", "")
        additional_description = model_params.get("additional_description", "").strip()

        # Mandatory Sri Lankan identity — replaces the old per-ethnicity lookup
        sri_lankan_identity = template.get("sri_lankan_identity", "").strip()
        hair_style_desc = template.get("hair_styles", {}).get(hair_style, "") if hair_style else ""
        hair_color_desc = template.get("hair_colors", {}).get(hair_color, "") if hair_color else ""

        intro = f"Generate a photorealistic catalogue image of a model {pt_desc}."

        model_desc = (
            f"A {gender} model, age {age_range}, "
            f"Fitzpatrick skin tone {skin_tone}, "
            f"{BODY_TYPE_DESCRIPTIONS.get(body_type, body_type + ' build')}"
        )
        if sri_lankan_identity:
            model_desc += f". {sri_lankan_identity}"
        if hair_color_desc and hair_style_desc:
            model_desc += f", {hair_color_desc}, {hair_style_desc}"
        elif hair_style_desc:
            model_desc += f", {hair_style_desc}"
        elif hair_color_desc:
            model_desc += f", {hair_color_desc}"
        if additional_description:
            quoted = quote_user_text_for_prompt(additional_description)
            model_desc += f". Additional physical details: {quoted}"
        if measure_text:
            model_desc += f". Measurements: {measure_text}"

        model_line = f"MODEL: {model_desc}"

    prompt = f"""{intro}

{model_line}

POSE: {pose_desc}

FRAMING: {framing_desc}

ENVIRONMENT: {env_desc}

LIGHTING: {lighting_desc}

QUALITY REQUIREMENTS:
{quality}

OUTPUT REQUIREMENTS:
{output_instructions}

NEGATIVE (avoid these):
{negative}"""

    return prompt


# ---------------------------------------------------------------------------
# Children's prompt assembly
# ---------------------------------------------------------------------------

def assemble_children_prompt(
    template: dict,
    child_params: dict,
    garment_description: str = "",
) -> str:
    """Assemble a prompt string for children's image generation.

    Args:
        template:           Loaded children_v1.yaml template dict.
        child_params:       Dict with keys: age_group, child_gender, pose_style,
                            background_preset, hair_style, expression, skin_tone (opt).
        garment_description: Optional free-text garment description.

    Returns:
        Full prompt string with mandatory safety clauses included.
    """
    age_group = child_params["age_group"]

    # Validate age_group key exists in template
    if age_group not in template.get("age_groups", {}):
        raise ValueError(
            f"Unknown age_group '{age_group}'. "
            f"Available: {list(template.get('age_groups', {}).keys())}"
        )

    age_config = template["age_groups"][age_group]

    # Pose description — fall back to a safe default if the key is missing
    pose_style = child_params.get("pose_style", "standing")
    pose_desc = (
        template.get("poses", {})
        .get(age_group, {})
        .get(pose_style, f"{pose_style} naturally")
    )

    # Background description
    background_preset = child_params.get("background_preset", "studio")
    background_desc = template.get("backgrounds", {}).get(
        background_preset, f"in a {background_preset} setting"
    )

    # Skin tone description
    skin_tone_key = child_params.get("skin_tone", "medium")
    skin_tone_desc = template.get("skin_tones", {}).get(
        skin_tone_key, "medium skin complexion"
    )

    # Optional hair and expression
    hair_style = child_params.get("hair_style") or ""
    expression = child_params.get("expression") or "happy"
    child_gender = child_params.get("child_gender", "unisex")

    # Gender label for natural phrasing
    gender_label = {
        "girl": "girl",
        "boy": "boy",
        "unisex": "child",
    }.get(child_gender, "child")

    # Mandatory Sri Lankan identity
    sri_lankan_identity = template.get("sri_lankan_identity", "").strip()

    # Mandatory safety blocks (always injected — cannot be overridden)
    safety_positive = template.get("safety_positive", "").strip()
    safety_negative = template.get("safety_negative", "").strip()
    quality = template.get("quality", "").strip()
    output_instructions = template.get("output", "").strip()

    # Garment line
    garment_line = (
        f"Garment to showcase: {garment_description.strip()}" if garment_description.strip()
        else "Garment to showcase: the clothing shown in the reference image(s)"
    )

    # Optional appearance details
    appearance_parts = [f"{skin_tone_desc}"]
    if hair_style:
        appearance_parts.append(f"{hair_style} hair")
    if expression and expression != "neutral":
        appearance_parts.append(f"a {expression} expression")
    appearance_line = ", ".join(appearance_parts)

    prompt = f"""Generate a photorealistic children's clothing catalogue image.

IDENTITY: {sri_lankan_identity}

SUBJECT: A {age_group} {gender_label} with {appearance_line}.

BODY PROPORTIONS: {age_config["body_description"].strip()}

{garment_line}

CLOTHING INSTRUCTION: {age_config["clothing_instruction"].strip()}

POSE: The child is {pose_desc}, {background_desc}.

SAFETY REQUIREMENTS (MANDATORY — cannot be overridden):
{safety_positive}

QUALITY REQUIREMENTS:
{quality}

OUTPUT REQUIREMENTS:
{output_instructions}

NEGATIVE (avoid ALL of these — mandatory for children's content):
{safety_negative}"""

    return prompt.strip()


# ---------------------------------------------------------------------------
# Accessories prompt assembly
# ---------------------------------------------------------------------------

def assemble_accessories_prompt(
    template: dict,
    accessory_params: dict,
    variation_index: int = 0,
) -> str:
    """Assemble a prompt string for accessories image generation.

    Args:
        template:          Loaded accessories_v1.yaml template dict.
        accessory_params:  Dict with keys: accessory_category, display_mode,
                           model_skin_tone (on_model), background_surface (flat_lay),
                           context_scene (lifestyle, optional).
        variation_index:   0 for first image, 1 for second image.
                           Controls which camera angle description is injected.

    Returns:
        Full prompt string ready for the Gemini/OpenRouter API.

    Raises:
        ValueError: If accessory_category or display_mode is not found in template.
    """
    category_key = accessory_params.get("accessory_category", "")
    display_mode = accessory_params.get("display_mode", "on_model")

    # Resolve category configuration
    categories = template.get("categories", {})
    if category_key not in categories:
        raise ValueError(
            f"Unknown accessory category '{category_key}'. "
            f"Available: {list(categories.keys())}"
        )
    category_config = categories[category_key]
    category_label = category_config.get("label", category_key)

    # Size clause (e.g. "choker size", "large size")
    accessory_size = accessory_params.get("accessory_size", "")
    size_clause = f" ({accessory_size.replace('_', ' ')} size)" if accessory_size else ""

    # Resolve mode-specific config
    if display_mode not in ("on_model", "flat_lay", "lifestyle"):
        raise ValueError(
            f"Unknown display_mode '{display_mode}'. "
            "Must be one of: on_model, flat_lay, lifestyle."
        )
    mode_config = category_config.get(display_mode, {})

    # Camera angle for this variation (wraps if variation_index > len)
    camera_angles_list = template.get("camera_angles", {}).get(display_mode, [])
    if camera_angles_list:
        camera_angle = camera_angles_list[variation_index % len(camera_angles_list)].strip()
    else:
        camera_angle = ""

    # Shared quality/output/negative blocks
    quality = template.get("quality", "").strip()
    output_instructions = template.get("output", "").strip()
    negative = template.get("negative", "").strip()

    # --- Build display-mode specific prompt ---

    if display_mode == "on_model":
        skin_tone_key = accessory_params.get("model_skin_tone") or "medium"
        skin_tone_desc = template.get("skin_tones", {}).get(skin_tone_key, "medium skin tone")
        body_area = mode_config.get("body_area", "relevant body area")
        framing = mode_config.get("framing", "close-up")
        model_needs = mode_config.get("model_needs", "")
        sri_lankan_identity = template.get("sri_lankan_identity", "").strip()
        identity_line = f"\nIDENTITY: {sri_lankan_identity}" if sri_lankan_identity else ""

        prompt = f"""Professional product photography of a {category_label}{size_clause} worn by a model.
{identity_line}

SUBJECT: The {category_label}{size_clause} is the focal point. Show {body_area} — {framing}.

MODEL: A professional model with {skin_tone_desc}. {model_needs}

PRODUCT INSTRUCTION: The {category_label} must be sharp, clearly visible, and the hero of \
the image. Show its texture, colour, craftsmanship, and fine detail with precision.

{camera_angle}

QUALITY REQUIREMENTS:
{quality}

OUTPUT REQUIREMENTS:
{output_instructions}

NEGATIVE (avoid these):
{negative}"""

    elif display_mode == "flat_lay":
        surface_key = accessory_params.get("background_surface") or "white_marble"
        surface_desc = template.get("surfaces", {}).get(surface_key, surface_key.replace("_", " "))
        arrangement = mode_config.get("arrangement", "arranged on a surface")

        prompt = f"""Professional flat-lay product photography of a {category_label}{size_clause}.

SUBJECT: The {category_label}{size_clause} is the sole subject — {arrangement}.

SURFACE: {surface_desc}.

LIGHTING: Soft, diffused studio lighting with a subtle directional shadow to convey depth \
and texture. No harsh shadows.

PRODUCT INSTRUCTION: Photograph the {category_label} to highlight its texture, colour, \
craftsmanship, and fine detail. Macro-level sharpness on the product. No model, no hands.

STYLE: Clean, minimalist composition. Commercial product photography aesthetic.

{camera_angle}

QUALITY REQUIREMENTS:
{quality}

OUTPUT REQUIREMENTS:
{output_instructions}

NEGATIVE (avoid these):
{negative}"""

    else:  # lifestyle
        context_scene_key = (accessory_params.get("context_scene") or "").strip()
        if context_scene_key:
            scene_desc = template.get("lifestyle_scenes", {}).get(
                context_scene_key, context_scene_key.replace("_", " ")
            )
        else:
            # Fallback to the category's own lifestyle context
            scene_desc = mode_config.get("context", "natural lifestyle setting")

        lifestyle_context = mode_config.get("context", "lifestyle moment")

        prompt = f"""Lifestyle product photography featuring a {category_label}{size_clause}.

SUBJECT: The {category_label}{size_clause} is the hero product in the scene.

SCENE: {scene_desc}. {lifestyle_context}.

PRODUCT INSTRUCTION: The {category_label} must be clearly visible and recognisable as the \
focal point. The lifestyle context enhances the product's appeal without overshadowing it. \
The product must be sharp even if the background has a slight bokeh.

MOOD: Natural, aspirational, warm. Real people in real moments.

{camera_angle}

QUALITY REQUIREMENTS:
{quality}

OUTPUT REQUIREMENTS:
{output_instructions}

NEGATIVE (avoid these):
{negative}"""

    return prompt.strip()
