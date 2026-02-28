"""Prompt template loading and assembly service."""

from pathlib import Path

import yaml

# Prompt templates directory
PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

# Cache loaded templates
_template_cache: dict[str, dict] = {}


def load_template(version: str = "v0.1") -> dict:
    """Load a prompt template YAML file by version.

    Args:
        version: Template version string (e.g., "v0.1").

    Returns:
        Parsed YAML template as a dictionary.
    """
    if version in _template_cache:
        return _template_cache[version]

    # Convert version format: "v0.1" → "v0_1.yaml"
    filename = version.replace(".", "_") + ".yaml"
    filepath = PROMPTS_DIR / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Prompt template not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        template = yaml.safe_load(f)

    _template_cache[version] = template
    return template


def assemble_prompt(
    model_params: dict,
    scene_params: dict,
    template_version: str = "v0.1",
) -> str:
    """Assemble a full prompt string from template and user parameters.

    Args:
        model_params: Dict with keys: age_range, gender_presentation, skin_tone,
                      body_mode, body_type.
        scene_params: Dict with keys: environment, pose_preset, framing.
        template_version: Version of the prompt template to use.

    Returns:
        Assembled prompt string ready for the Gemini API.
    """
    template = load_template(template_version)

    # Extract environment, pose, and framing keys
    environment = scene_params.get("environment", "studio_white")
    pose_preset = scene_params.get("pose_preset", "front_standing")
    framing = scene_params.get("framing", "full_body")

    # Look up descriptions from template
    env_desc = template.get("environments", {}).get(environment, environment)
    pose_desc = template.get("poses", {}).get(pose_preset, pose_preset)
    framing_desc = template.get("framing", {}).get(framing, framing)
    lighting_desc = template.get("lighting", {}).get(environment, "")

    # Build model description
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

    # Assemble full prompt
    quality = template.get("quality", "").strip()
    output_instructions = template.get("output", "").strip()
    negative = template.get("negative", "").strip()

    prompt = f"""Generate a photorealistic catalogue image of a model wearing the garment shown in the reference image(s).

MODEL: {model_desc}

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
