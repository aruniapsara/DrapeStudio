"""Prompt template loading and assembly service."""

from pathlib import Path

import yaml

# Prompt templates directory
PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

# Cache loaded templates
_template_cache: dict[str, dict] = {}


def load_template(version: str = "v0.1") -> dict:
    """Load a prompt template YAML file by version."""
    if version in _template_cache:
        return _template_cache[version]

    filename = version.replace(".", "_") + ".yaml"
    filepath = PROMPTS_DIR / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Prompt template not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        template = yaml.safe_load(f)

    _template_cache[version] = template
    return template


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


def assemble_prompt(
    model_params: dict,
    scene_params: dict,
    template_version: str = "v0.1",
) -> str:
    """Assemble a full prompt string from template and user parameters."""
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
        ethnicity = model_params.get("ethnicity", "")
        hair_style = model_params.get("hair_style", "")
        hair_color = model_params.get("hair_color", "")
        additional_description = model_params.get("additional_description", "").strip()

        ethnicity_desc = template.get("ethnicities", {}).get(ethnicity, "") if ethnicity else ""
        hair_style_desc = template.get("hair_styles", {}).get(hair_style, "") if hair_style else ""
        hair_color_desc = template.get("hair_colors", {}).get(hair_color, "") if hair_color else ""

        intro = f"Generate a photorealistic catalogue image of a model {pt_desc}."

        model_desc = (
            f"A {gender} model, age {age_range}, "
            f"Fitzpatrick skin tone {skin_tone}, {body_type} body type"
        )
        if ethnicity_desc:
            model_desc += f", {ethnicity_desc}"
        if hair_color_desc and hair_style_desc:
            model_desc += f", {hair_color_desc}, {hair_style_desc}"
        elif hair_style_desc:
            model_desc += f", {hair_style_desc}"
        elif hair_color_desc:
            model_desc += f", {hair_color_desc}"
        if additional_description:
            model_desc += f". Additional details: {additional_description}"
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
