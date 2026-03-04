"""Tests for accessories prompt assembly (accessories_v1.yaml + assemble_accessories_prompt)."""

import pytest

from app.services.prompt import load_accessories_template, assemble_accessories_prompt
from app.config.accessories import ACCESSORY_CATEGORIES


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _params(category="necklace", display_mode="on_model", **kwargs):
    """Build a minimal accessory_params dict for the given mode."""
    base = {
        "accessory_category": category,
        "display_mode": display_mode,
    }
    if display_mode == "on_model" and "model_skin_tone" not in kwargs:
        base["model_skin_tone"] = "medium"
    if display_mode == "flat_lay" and "background_surface" not in kwargs:
        base["background_surface"] = "white_marble"
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

def test_accessories_template_loads():
    """accessories_v1.yaml must load without error."""
    tmpl = load_accessories_template()
    assert isinstance(tmpl, dict)
    assert tmpl.get("version") == "accessories_v1"


def test_template_has_all_sections():
    """Template must contain all required top-level keys."""
    tmpl = load_accessories_template()
    required_keys = {
        "camera_angles", "categories", "surfaces",
        "lifestyle_scenes", "skin_tones", "quality", "output", "negative",
    }
    missing = required_keys - set(tmpl.keys())
    assert not missing, f"Template missing sections: {missing}"


def test_template_camera_angles_for_all_modes():
    """camera_angles must have entries for on_model, flat_lay, and lifestyle."""
    tmpl = load_accessories_template()
    angles = tmpl["camera_angles"]
    for mode in ("on_model", "flat_lay", "lifestyle"):
        assert mode in angles, f"Missing camera_angles for mode '{mode}'"
        assert len(angles[mode]) == 2, (
            f"Expected 2 camera angle entries for '{mode}', got {len(angles[mode])}"
        )


def test_template_has_all_nine_categories():
    """Template categories must include all 9 accessory categories."""
    tmpl = load_accessories_template()
    expected = set(ACCESSORY_CATEGORIES.keys())
    actual = set(tmpl["categories"].keys())
    assert actual == expected, f"Template categories mismatch: {actual ^ expected}"


def test_template_category_has_all_display_modes():
    """Each category in the template must have on_model, flat_lay, lifestyle."""
    tmpl = load_accessories_template()
    for cat_key, cat_config in tmpl["categories"].items():
        for mode in ("on_model", "flat_lay", "lifestyle"):
            assert mode in cat_config, (
                f"Category '{cat_key}' missing display_mode '{mode}' in template"
            )


# ---------------------------------------------------------------------------
# On-model prompt tests
# ---------------------------------------------------------------------------

def test_on_model_necklace_includes_body_area():
    """Necklace on-model prompt must mention 'neck and upper chest'."""
    tmpl = load_accessories_template()
    prompt = assemble_accessories_prompt(
        tmpl, _params("necklace", "on_model", model_skin_tone="medium"), variation_index=0
    )
    assert "neck and upper chest" in prompt.lower()


def test_on_model_bracelet_includes_wrist():
    """Bracelet on-model prompt must mention 'wrist'."""
    tmpl = load_accessories_template()
    prompt = assemble_accessories_prompt(
        tmpl, _params("bracelet", "on_model", model_skin_tone="light"), variation_index=0
    )
    assert "wrist" in prompt.lower()


def test_on_model_earrings_includes_ear():
    """Earrings on-model prompt must mention 'ear'."""
    tmpl = load_accessories_template()
    prompt = assemble_accessories_prompt(
        tmpl, _params("earrings", "on_model", model_skin_tone="dark"), variation_index=0
    )
    assert "ear" in prompt.lower()


def test_on_model_ring_includes_finger():
    """Ring on-model prompt must mention 'finger'."""
    tmpl = load_accessories_template()
    prompt = assemble_accessories_prompt(
        tmpl, _params("ring", "on_model", model_skin_tone="medium"), variation_index=0
    )
    assert "finger" in prompt.lower()


def test_on_model_hat_includes_head():
    """Hat on-model prompt must mention 'head'."""
    tmpl = load_accessories_template()
    prompt = assemble_accessories_prompt(
        tmpl, _params("hat", "on_model", model_skin_tone="very_light"), variation_index=0
    )
    assert "head" in prompt.lower()


def test_on_model_includes_skin_tone():
    """On-model prompt must reference the provided skin tone."""
    tmpl = load_accessories_template()
    prompt = assemble_accessories_prompt(
        tmpl, _params("necklace", "on_model", model_skin_tone="dark"), variation_index=0
    )
    # "dark/brown skin tone" is in skin_tones map
    assert "dark" in prompt.lower()


def test_on_model_camera_angle_changes_with_variation():
    """Variation 0 and 1 must produce different camera angle text in on_model prompts."""
    tmpl = load_accessories_template()
    p0 = assemble_accessories_prompt(tmpl, _params("necklace", "on_model"), variation_index=0)
    p1 = assemble_accessories_prompt(tmpl, _params("necklace", "on_model"), variation_index=1)
    assert p0 != p1, "Variation 0 and 1 should produce different prompts"


# ---------------------------------------------------------------------------
# Flat-lay prompt tests
# ---------------------------------------------------------------------------

def test_flat_lay_includes_surface():
    """Flat-lay prompt must include the surface description."""
    tmpl = load_accessories_template()
    prompt = assemble_accessories_prompt(
        tmpl,
        _params("earrings", "flat_lay", background_surface="wooden_table"),
        variation_index=0,
    )
    assert "wooden" in prompt.lower()


def test_flat_lay_white_marble_surface():
    """Flat-lay with white_marble should mention marble."""
    tmpl = load_accessories_template()
    prompt = assemble_accessories_prompt(
        tmpl,
        _params("ring", "flat_lay", background_surface="white_marble"),
        variation_index=0,
    )
    assert "marble" in prompt.lower()


def test_flat_lay_mentions_arrangement():
    """Flat-lay prompt must include the category's arrangement description."""
    tmpl = load_accessories_template()
    # necklace flat_lay arrangement mentions "chain length"
    prompt = assemble_accessories_prompt(
        tmpl,
        _params("necklace", "flat_lay", background_surface="linen_cloth"),
        variation_index=0,
    )
    assert "chain" in prompt.lower() or "draped" in prompt.lower()


def test_flat_lay_no_model_instruction():
    """Flat-lay prompt must specify 'no model' or similar."""
    tmpl = load_accessories_template()
    prompt = assemble_accessories_prompt(
        tmpl, _params("bracelet", "flat_lay"), variation_index=0
    )
    assert "no model" in prompt.lower() or "no hands" in prompt.lower()


def test_flat_lay_overhead_angle_in_variation_0():
    """Variation 0 flat-lay camera angle should be overhead / top-down."""
    tmpl = load_accessories_template()
    prompt = assemble_accessories_prompt(
        tmpl, _params("hat", "flat_lay"), variation_index=0
    )
    assert "overhead" in prompt.lower() or "top-down" in prompt.lower() or "90 degrees" in prompt.lower()


def test_flat_lay_camera_angle_changes_with_variation():
    """Variation 0 and 1 must produce different camera angle text in flat-lay prompts."""
    tmpl = load_accessories_template()
    p0 = assemble_accessories_prompt(tmpl, _params("scarf", "flat_lay"), variation_index=0)
    p1 = assemble_accessories_prompt(tmpl, _params("scarf", "flat_lay"), variation_index=1)
    assert p0 != p1


# ---------------------------------------------------------------------------
# Lifestyle prompt tests
# ---------------------------------------------------------------------------

def test_lifestyle_includes_context_scene():
    """Lifestyle prompt with a context_scene key must include the scene description."""
    tmpl = load_accessories_template()
    prompt = assemble_accessories_prompt(
        tmpl,
        _params("necklace", "lifestyle", context_scene="cafe"),
        variation_index=0,
    )
    assert "cafe" in prompt.lower()


def test_lifestyle_garden_scene():
    """Lifestyle prompt with garden scene must include garden description."""
    tmpl = load_accessories_template()
    prompt = assemble_accessories_prompt(
        tmpl,
        _params("hat", "lifestyle", context_scene="garden"),
        variation_index=0,
    )
    assert "garden" in prompt.lower()


def test_lifestyle_fallback_without_scene():
    """Lifestyle prompt with no context_scene falls back to category's own context."""
    tmpl = load_accessories_template()
    prompt = assemble_accessories_prompt(
        tmpl, _params("crochet", "lifestyle"), variation_index=0
    )
    # crochet lifestyle context mentions "cozy" or "cosy"
    assert "cozy" in prompt.lower() or "cosy" in prompt.lower() or "lifestyle" in prompt.lower()


def test_lifestyle_camera_angle_changes_with_variation():
    """Variation 0 and 1 must produce different camera angle text in lifestyle prompts."""
    tmpl = load_accessories_template()
    p0 = assemble_accessories_prompt(
        tmpl, _params("handbag", "lifestyle", context_scene="urban_street"), variation_index=0
    )
    p1 = assemble_accessories_prompt(
        tmpl, _params("handbag", "lifestyle", context_scene="urban_street"), variation_index=1
    )
    assert p0 != p1


# ---------------------------------------------------------------------------
# All categories assemble without error (smoke tests)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("category", list(ACCESSORY_CATEGORIES.keys()))
def test_all_categories_assemble_on_model(category):
    """Every category must assemble an on_model prompt without error."""
    tmpl = load_accessories_template()
    prompt = assemble_accessories_prompt(
        tmpl, _params(category, "on_model", model_skin_tone="medium"), variation_index=0
    )
    assert len(prompt) > 50, f"Prompt for '{category}' on_model seems too short"
    assert category.replace("_", " ") in prompt.lower() or tmpl["categories"][category]["label"] in prompt.lower()


@pytest.mark.parametrize("category", list(ACCESSORY_CATEGORIES.keys()))
def test_all_categories_assemble_flat_lay(category):
    """Every category must assemble a flat_lay prompt without error."""
    tmpl = load_accessories_template()
    prompt = assemble_accessories_prompt(
        tmpl, _params(category, "flat_lay", background_surface="linen_cloth"), variation_index=1
    )
    assert len(prompt) > 50


@pytest.mark.parametrize("category", list(ACCESSORY_CATEGORIES.keys()))
def test_all_categories_assemble_lifestyle(category):
    """Every category must assemble a lifestyle prompt without error."""
    tmpl = load_accessories_template()
    prompt = assemble_accessories_prompt(
        tmpl, _params(category, "lifestyle", context_scene="garden"), variation_index=0
    )
    assert len(prompt) > 50


# ---------------------------------------------------------------------------
# Output count test
# ---------------------------------------------------------------------------

def test_output_count_is_2_for_accessories():
    """The template must declare default_output_count=2 for accessories."""
    tmpl = load_accessories_template()
    assert tmpl.get("default_output_count") == 2, (
        f"Expected default_output_count=2, got {tmpl.get('default_output_count')}"
    )


def test_invalid_category_raises_value_error():
    """Assembling with an unknown category must raise ValueError."""
    tmpl = load_accessories_template()
    with pytest.raises(ValueError, match="Unknown accessory category"):
        assemble_accessories_prompt(
            tmpl,
            {"accessory_category": "sunglasses", "display_mode": "lifestyle"},
            variation_index=0,
        )


def test_invalid_display_mode_raises_value_error():
    """Assembling with an unknown display_mode must raise ValueError."""
    tmpl = load_accessories_template()
    with pytest.raises(ValueError, match="Unknown display_mode"):
        assemble_accessories_prompt(
            tmpl,
            {"accessory_category": "necklace", "display_mode": "hanging"},
            variation_index=0,
        )
