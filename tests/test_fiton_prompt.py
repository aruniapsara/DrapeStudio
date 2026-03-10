"""Tests for FitonPromptBuilder — app/services/fiton_prompt.py."""

import pytest

from app.services.fiton_prompt import FitonPromptBuilder, VALID_GARMENT_TYPES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def builder() -> FitonPromptBuilder:
    """Module-scoped FitonPromptBuilder (loads YAML once)."""
    return FitonPromptBuilder()


SAMPLE_MEASUREMENTS = {
    "bust_cm": 88.0,
    "waist_cm": 70.0,
    "hips_cm": 96.0,
    "height_cm": 163.0,
    "skin_tone": "medium",
    "gender": "female",
}

SAMPLE_FIT_DETAILS = {
    "bust": "good",
    "waist": "tight",
    "hips": "slightly loose",
}


# ---------------------------------------------------------------------------
# 1. YAML loading
# ---------------------------------------------------------------------------

class TestYAMLLoading:
    def test_config_loaded(self, builder):
        assert builder.config is not None

    def test_all_garment_types_present(self, builder):
        for gt in VALID_GARMENT_TYPES:
            assert gt in builder.config["garment_types"], f"Missing garment type: {gt}"

    def test_fit_descriptions_present(self, builder):
        for key in ("tight", "regular", "loose"):
            assert key in builder.config["fit_descriptions"]

    def test_negative_prompt_present(self, builder):
        assert "negative_prompt" in builder.config
        assert len(builder.config["negative_prompt"]) > 10

    def test_safety_blocked_terms(self, builder):
        blocked = builder.config["safety"]["blocked_terms"]
        assert "child" in blocked
        assert "minor" in blocked
        assert "underage" in blocked


# ---------------------------------------------------------------------------
# 2. build_prompt — all five garment types
# ---------------------------------------------------------------------------

class TestBuildPromptAllGarmentTypes:
    @pytest.mark.parametrize("garment_type", list(VALID_GARMENT_TYPES))
    def test_returns_dict_with_required_keys(self, builder, garment_type):
        result = builder.build_prompt(
            garment_type=garment_type,
            customer_measurements=SAMPLE_MEASUREMENTS,
        )
        assert "prompt" in result
        assert "negative_prompt" in result
        assert "system_context" in result
        assert "num_images" in result

    @pytest.mark.parametrize("garment_type", list(VALID_GARMENT_TYPES))
    def test_num_images_always_one(self, builder, garment_type):
        result = builder.build_prompt(
            garment_type=garment_type,
            customer_measurements=SAMPLE_MEASUREMENTS,
        )
        assert result["num_images"] == 1

    @pytest.mark.parametrize("garment_type", list(VALID_GARMENT_TYPES))
    def test_prompt_is_non_empty_string(self, builder, garment_type):
        result = builder.build_prompt(
            garment_type=garment_type,
            customer_measurements=SAMPLE_MEASUREMENTS,
        )
        assert isinstance(result["prompt"], str)
        assert len(result["prompt"]) > 20

    def test_dress_prompt_contains_dress(self, builder):
        result = builder.build_prompt(
            garment_type="dress",
            customer_measurements=SAMPLE_MEASUREMENTS,
        )
        assert "dress" in result["prompt"].lower()

    def test_top_prompt_contains_top_or_blouse(self, builder):
        result = builder.build_prompt(
            garment_type="top",
            customer_measurements=SAMPLE_MEASUREMENTS,
        )
        prompt_lower = result["prompt"].lower()
        assert "top" in prompt_lower or "blouse" in prompt_lower

    def test_saree_prompt_contains_saree(self, builder):
        result = builder.build_prompt(
            garment_type="saree",
            customer_measurements=SAMPLE_MEASUREMENTS,
        )
        assert "saree" in result["prompt"].lower()

    def test_bottom_prompt_contains_pants_or_skirt(self, builder):
        result = builder.build_prompt(
            garment_type="bottom",
            customer_measurements=SAMPLE_MEASUREMENTS,
        )
        prompt_lower = result["prompt"].lower()
        assert "pant" in prompt_lower or "skirt" in prompt_lower or "bottom" in prompt_lower

    def test_full_outfit_prompt_contains_outfit(self, builder):
        result = builder.build_prompt(
            garment_type="full_outfit",
            customer_measurements=SAMPLE_MEASUREMENTS,
        )
        assert "outfit" in result["prompt"].lower()

    def test_unknown_garment_type_falls_back_to_dress(self, builder):
        result = builder.build_prompt(
            garment_type="swimwear",
            customer_measurements=SAMPLE_MEASUREMENTS,
        )
        assert "dress" in result["prompt"].lower()


# ---------------------------------------------------------------------------
# 3. Customer description
# ---------------------------------------------------------------------------

class TestCustomerDescription:
    def test_height_petite(self, builder):
        desc = builder._build_customer_description(
            {"height_cm": 150.0, "waist_cm": 64.0, "skin_tone": "fair", "gender": "female"}
        )
        assert "petite" in desc

    def test_height_average(self, builder):
        desc = builder._build_customer_description(
            {"height_cm": 160.0, "waist_cm": 64.0, "skin_tone": "fair", "gender": "female"}
        )
        assert "average" in desc

    def test_height_tall(self, builder):
        desc = builder._build_customer_description(
            {"height_cm": 170.0, "waist_cm": 64.0, "skin_tone": "fair", "gender": "female"}
        )
        assert "tall" in desc

    def test_height_very_tall(self, builder):
        desc = builder._build_customer_description(
            {"height_cm": 180.0, "waist_cm": 64.0, "skin_tone": "fair", "gender": "female"}
        )
        assert "very tall" in desc

    def test_build_slim(self, builder):
        desc = builder._build_customer_description(
            {"height_cm": 163.0, "waist_cm": 60.0, "skin_tone": "medium", "gender": "female"}
        )
        assert "slim" in desc

    def test_build_medium(self, builder):
        desc = builder._build_customer_description(
            {"height_cm": 163.0, "waist_cm": 70.0, "skin_tone": "medium", "gender": "female"}
        )
        assert "medium" in desc

    def test_build_curvy(self, builder):
        desc = builder._build_customer_description(
            {"height_cm": 163.0, "waist_cm": 82.0, "skin_tone": "medium", "gender": "female"}
        )
        assert "curvy" in desc

    def test_build_plus_size(self, builder):
        desc = builder._build_customer_description(
            {"height_cm": 163.0, "waist_cm": 95.0, "skin_tone": "medium", "gender": "female"}
        )
        assert "plus" in desc

    def test_skin_tone_appears_in_description(self, builder):
        desc = builder._build_customer_description(
            {"height_cm": 163.0, "waist_cm": 70.0, "skin_tone": "deep", "gender": "female"}
        )
        assert "deep" in desc

    def test_gender_appears_in_description(self, builder):
        desc = builder._build_customer_description(
            {"height_cm": 163.0, "waist_cm": 70.0, "skin_tone": "medium", "gender": "male"}
        )
        assert "male" in desc

    def test_defaults_when_keys_missing(self, builder):
        """Should not raise — uses defaults for missing keys."""
        desc = builder._build_customer_description({})
        assert isinstance(desc, str)
        assert len(desc) > 0


# ---------------------------------------------------------------------------
# 4. Fit description
# ---------------------------------------------------------------------------

class TestFitDescription:
    def test_fit_preference_regular_used_when_no_fit_details(self, builder):
        result = builder.build_prompt(
            garment_type="dress",
            customer_measurements=SAMPLE_MEASUREMENTS,
            fit_preference="regular",
        )
        # "regular" fit_description should appear somewhere in the prompt
        assert any(
            word in result["prompt"].lower()
            for word in ["comfortably", "standard", "regular"]
        )

    def test_fit_preference_loose(self, builder):
        result = builder.build_prompt(
            garment_type="dress",
            customer_measurements=SAMPLE_MEASUREMENTS,
            fit_preference="loose",
        )
        assert any(
            word in result["prompt"].lower()
            for word in ["loosely", "relaxed", "loose"]
        )

    def test_fit_preference_tight(self, builder):
        result = builder.build_prompt(
            garment_type="dress",
            customer_measurements=SAMPLE_MEASUREMENTS,
            fit_preference="tight",
        )
        assert any(
            word in result["prompt"].lower()
            for word in ["snugly", "close", "snug", "tight"]
        )

    def test_detailed_fit_description_tight(self, builder):
        desc = builder._build_detailed_fit_description({"waist": "tight"})
        assert "snug" in desc

    def test_detailed_fit_description_loose(self, builder):
        desc = builder._build_detailed_fit_description({"hips": "loose"})
        assert "relaxed" in desc

    def test_detailed_fit_description_slightly_loose(self, builder):
        desc = builder._build_detailed_fit_description({"bust": "slightly loose"})
        assert "ease" in desc

    def test_detailed_fit_description_good_skipped(self, builder):
        desc = builder._build_detailed_fit_description({"bust": "good"})
        # "good" means perfect fit — no annotation, returns "comfortably"
        assert desc == "comfortably"

    def test_detailed_fit_mixed(self, builder):
        desc = builder._build_detailed_fit_description(
            {"bust": "good", "waist": "tight", "hips": "slightly loose"}
        )
        assert "snug" in desc
        assert "ease" in desc
        # "good" (bust) should NOT appear as annotation
        assert "good" not in desc

    def test_fit_details_override_fit_preference(self, builder):
        """When fit_details is provided, it should produce a detailed fit desc."""
        result_with_details = builder.build_prompt(
            garment_type="dress",
            customer_measurements=SAMPLE_MEASUREMENTS,
            fit_preference="regular",
            fit_details={"waist": "tight"},
        )
        # Should contain "snug" (from tight) not just generic regular text
        assert "snug" in result_with_details["prompt"]


# ---------------------------------------------------------------------------
# 5. Garment extra description
# ---------------------------------------------------------------------------

class TestGarmentExtra:
    def test_empty_dict_returns_empty_string(self, builder):
        extra = builder._build_garment_extra({})
        assert extra == ""

    def test_color_and_material(self, builder):
        extra = builder._build_garment_extra({"color": "navy blue", "material": "silk"})
        assert "navy blue" in extra
        assert "silk" in extra

    def test_color_only(self, builder):
        extra = builder._build_garment_extra({"color": "red"})
        assert "red" in extra

    def test_material_only(self, builder):
        extra = builder._build_garment_extra({"material": "cotton"})
        assert "cotton" in extra

    def test_details_only(self, builder):
        extra = builder._build_garment_extra({"details": "embroidered hem"})
        assert "embroidered hem" in extra

    def test_full_description(self, builder):
        extra = builder._build_garment_extra(
            {"color": "emerald green", "material": "chiffon", "details": "floral print"}
        )
        assert "emerald green" in extra
        assert "chiffon" in extra
        assert "floral print" in extra

    def test_garment_description_appears_in_dress_prompt(self, builder):
        result = builder.build_prompt(
            garment_type="dress",
            customer_measurements=SAMPLE_MEASUREMENTS,
            garment_description={"color": "crimson", "material": "velvet"},
        )
        assert "crimson" in result["prompt"] or "velvet" in result["prompt"]


# ---------------------------------------------------------------------------
# 6. Safety / photo validation
# ---------------------------------------------------------------------------

class TestValidateCustomerPhoto:
    def test_safe_metadata_passes(self, builder):
        is_valid, msg = builder.validate_customer_photo(
            {"filename": "customer_photo.jpg", "caption": "front view"}
        )
        assert is_valid is True
        assert msg == "OK"

    def test_blocked_term_child(self, builder):
        is_valid, msg = builder.validate_customer_photo(
            {"filename": "child_photo.jpg"}
        )
        assert is_valid is False
        assert "child" in msg.lower()

    def test_blocked_term_minor(self, builder):
        is_valid, msg = builder.validate_customer_photo(
            {"caption": "photo of a minor wearing dress"}
        )
        assert is_valid is False

    def test_blocked_term_teen(self, builder):
        is_valid, msg = builder.validate_customer_photo(
            {"description": "teen model"}
        )
        assert is_valid is False

    def test_blocked_term_underage(self, builder):
        is_valid, msg = builder.validate_customer_photo(
            {"tags": "underage teenager"}
        )
        assert is_valid is False

    def test_blocked_term_case_insensitive(self, builder):
        is_valid, msg = builder.validate_customer_photo(
            {"caption": "CHILD PHOTO"}
        )
        assert is_valid is False

    def test_empty_metadata_passes(self, builder):
        is_valid, msg = builder.validate_customer_photo({})
        assert is_valid is True

    def test_non_string_values_skipped(self, builder):
        """Non-string metadata values should not cause errors."""
        is_valid, msg = builder.validate_customer_photo(
            {"width": 1080, "height": 1920, "size_bytes": 204800}
        )
        assert is_valid is True


# ---------------------------------------------------------------------------
# 7. Prompt cleanliness
# ---------------------------------------------------------------------------

class TestPromptCleanliness:
    @pytest.mark.parametrize("garment_type", list(VALID_GARMENT_TYPES))
    def test_no_double_spaces(self, builder, garment_type):
        result = builder.build_prompt(
            garment_type=garment_type,
            customer_measurements=SAMPLE_MEASUREMENTS,
        )
        assert "  " not in result["prompt"]

    @pytest.mark.parametrize("garment_type", list(VALID_GARMENT_TYPES))
    def test_no_leading_trailing_whitespace(self, builder, garment_type):
        result = builder.build_prompt(
            garment_type=garment_type,
            customer_measurements=SAMPLE_MEASUREMENTS,
        )
        assert result["prompt"] == result["prompt"].strip()

    def test_clean_prompt_collapses_newlines(self, builder):
        raw = "Hello\n\n  world\t  here"
        cleaned = builder._clean_prompt(raw)
        assert "\n" not in cleaned
        assert "  " not in cleaned
        assert cleaned == "Hello world here"
