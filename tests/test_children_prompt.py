"""Tests for children's prompt template loading and assembly."""

import pytest


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

class TestChildrenTemplateLoading:

    def test_children_template_loads_without_error(self):
        from app.services.prompt import load_children_template
        template = load_children_template()
        assert template is not None
        assert isinstance(template, dict)

    def test_children_template_version_field(self):
        from app.services.prompt import load_children_template
        template = load_children_template()
        assert template.get("version") == "children_v1"
        assert template.get("module") == "children"

    def test_children_template_has_all_age_groups(self):
        from app.services.prompt import load_children_template
        template = load_children_template()
        age_groups = template.get("age_groups", {})
        assert set(age_groups.keys()) == {"baby", "toddler", "kid", "teen"}

    def test_each_age_group_has_required_fields(self):
        from app.services.prompt import load_children_template
        template = load_children_template()
        for group_name, group in template["age_groups"].items():
            assert "body_description" in group, f"'{group_name}' missing body_description"
            assert "clothing_instruction" in group, f"'{group_name}' missing clothing_instruction"
            assert len(group["body_description"]) > 20, f"'{group_name}' body_description too short"

    def test_template_has_poses_for_all_age_groups(self):
        from app.services.prompt import load_children_template
        template = load_children_template()
        poses = template.get("poses", {})
        for group in ["baby", "toddler", "kid", "teen"]:
            assert group in poses, f"No poses for age group '{group}'"
            assert len(poses[group]) >= 2, f"Too few poses for '{group}'"

    def test_template_has_backgrounds(self):
        from app.services.prompt import load_children_template
        template = load_children_template()
        backgrounds = template.get("backgrounds", {})
        assert len(backgrounds) >= 5
        # Each age group's backgrounds should exist in the template
        for bg in ["nursery", "studio", "park", "playground", "urban"]:
            assert bg in backgrounds, f"Background '{bg}' missing from template"

    def test_template_has_mandatory_safety_fields(self):
        from app.services.prompt import load_children_template
        template = load_children_template()
        assert "safety_positive" in template
        assert "safety_negative" in template
        assert len(template["safety_positive"]) > 20
        assert len(template["safety_negative"]) > 20

    def test_template_has_quality_and_output_fields(self):
        from app.services.prompt import load_children_template
        template = load_children_template()
        assert "quality" in template
        assert "output" in template

    def test_template_has_skin_tones(self):
        from app.services.prompt import load_children_template
        template = load_children_template()
        skin_tones = template.get("skin_tones", {})
        for tone in ["very_light", "light", "medium", "dark", "very_dark"]:
            assert tone in skin_tones, f"Skin tone '{tone}' missing"

    def test_load_template_by_module_name(self):
        """load_template('children') should return the children template."""
        from app.services.prompt import load_template
        template = load_template("children")
        assert template.get("module") == "children"

    def test_load_template_children_distinct_from_adult(self):
        from app.services.prompt import load_template
        adult = load_template("adult")
        children = load_template("children")
        assert adult is not children
        assert adult.get("module") != children.get("module")

    def test_template_is_cached_on_second_load(self):
        from app.services.prompt import load_children_template
        t1 = load_children_template()
        t2 = load_children_template()
        assert t1 is t2  # Same object — from cache


# ---------------------------------------------------------------------------
# Prompt assembly — per age group
# ---------------------------------------------------------------------------

class TestChildrenPromptAssembly:

    def _get_template(self):
        from app.services.prompt import load_children_template
        return load_children_template()

    def _assemble(self, **overrides):
        from app.services.prompt import assemble_children_prompt
        defaults = {
            "age_group": "kid",
            "child_gender": "girl",
            "pose_style": "standing",
            "background_preset": "park",
            "hair_style": "ponytail",
            "expression": "happy",
        }
        defaults.update(overrides)
        return assemble_children_prompt(self._get_template(), defaults)

    # ── Baby ────────────────────────────────────────────────────────────────

    def test_baby_prompt_contains_baby_body_description(self):
        prompt = self._assemble(
            age_group="baby", pose_style="sitting", background_preset="nursery"
        )
        assert "baby" in prompt.lower()
        assert "0-2" in prompt or "1:4" in prompt

    def test_baby_prompt_sitting_pose(self):
        prompt = self._assemble(
            age_group="baby", pose_style="sitting", background_preset="nursery"
        )
        assert "sitting" in prompt.lower()

    def test_baby_prompt_nursery_background(self):
        prompt = self._assemble(
            age_group="baby", pose_style="sitting", background_preset="nursery"
        )
        assert "nursery" in prompt.lower()

    # ── Toddler ─────────────────────────────────────────────────────────────

    def test_toddler_prompt_contains_toddler_description(self):
        prompt = self._assemble(
            age_group="toddler", pose_style="standing", background_preset="garden"
        )
        assert "toddler" in prompt.lower()
        assert "2-5" in prompt or "1:5" in prompt

    def test_toddler_prompt_garden_background(self):
        prompt = self._assemble(
            age_group="toddler", pose_style="playing", background_preset="garden"
        )
        assert "garden" in prompt.lower()

    # ── Kid ─────────────────────────────────────────────────────────────────

    def test_kid_prompt_contains_kid_description(self):
        prompt = self._assemble(age_group="kid")
        assert "child" in prompt.lower() or "kid" in prompt.lower()
        assert "6-12" in prompt or "1:6" in prompt

    def test_kid_prompt_school_pose(self):
        prompt = self._assemble(
            age_group="kid", pose_style="school", background_preset="school"
        )
        assert "school" in prompt.lower()

    # ── Teen ────────────────────────────────────────────────────────────────

    def test_teen_prompt_contains_teen_description(self):
        prompt = self._assemble(
            age_group="teen",
            pose_style="fashion_standing",
            background_preset="urban",
        )
        assert "teen" in prompt.lower() or "13-17" in prompt

    def test_teen_fashion_standing_pose(self):
        prompt = self._assemble(
            age_group="teen",
            pose_style="fashion_standing",
            background_preset="urban",
        )
        assert "fashion" in prompt.lower() or "confident" in prompt.lower()

    # ── General structure ────────────────────────────────────────────────────

    def test_prompt_includes_garment_instruction(self):
        prompt = self._assemble()
        assert "garment" in prompt.lower()

    def test_prompt_includes_pose_section(self):
        prompt = self._assemble()
        assert "POSE:" in prompt

    def test_prompt_includes_quality_section(self):
        prompt = self._assemble()
        assert "QUALITY" in prompt

    def test_prompt_includes_output_section(self):
        prompt = self._assemble()
        assert "OUTPUT" in prompt

    def test_prompt_includes_clothing_instruction(self):
        prompt = self._assemble()
        assert "CLOTHING INSTRUCTION:" in prompt

    def test_custom_garment_description_included(self):
        from app.services.prompt import assemble_children_prompt, load_children_template
        template = load_children_template()
        prompt = assemble_children_prompt(
            template,
            {"age_group": "kid", "child_gender": "girl", "pose_style": "standing", "background_preset": "park"},
            garment_description="a red floral dress with white collar",
        )
        assert "red floral dress" in prompt

    def test_hair_style_included_in_prompt(self):
        prompt = self._assemble(hair_style="braids")
        assert "braid" in prompt.lower()

    def test_expression_included_in_prompt(self):
        prompt = self._assemble(expression="laughing")
        assert "laughing" in prompt.lower()

    def test_skin_tone_included_in_prompt(self):
        prompt = self._assemble(skin_tone="dark")
        assert "dark" in prompt.lower()

    def test_invalid_age_group_raises_value_error(self):
        from app.services.prompt import assemble_children_prompt, load_children_template
        template = load_children_template()
        with pytest.raises(ValueError, match="Unknown age_group"):
            assemble_children_prompt(
                template,
                {"age_group": "adult", "pose_style": "standing", "background_preset": "studio"},
            )


# ---------------------------------------------------------------------------
# Safety constraints — mandatory injection
# ---------------------------------------------------------------------------

class TestChildrenPromptSafety:

    def _assemble(self, **overrides):
        from app.services.prompt import assemble_children_prompt, load_children_template
        defaults = {
            "age_group": "kid",
            "child_gender": "girl",
            "pose_style": "standing",
            "background_preset": "park",
        }
        defaults.update(overrides)
        return assemble_children_prompt(load_children_template(), defaults)

    def test_safety_positive_always_present(self):
        for age_group, pose, bg in [
            ("baby",    "sitting",          "nursery"),
            ("toddler", "standing",          "garden"),
            ("kid",     "standing",          "park"),
            ("teen",    "fashion_standing",  "urban"),
        ]:
            prompt = self._assemble(age_group=age_group, pose_style=pose, background_preset=bg)
            assert "fully clothed" in prompt.lower(), f"Safety positive missing for {age_group}"
            assert "family-friendly" in prompt.lower() or "wholesome" in prompt.lower(), \
                f"Safety positive incomplete for {age_group}"

    def test_safety_negative_always_present(self):
        for age_group, pose, bg in [
            ("baby",    "sitting",          "nursery"),
            ("toddler", "playing",           "playground"),
            ("kid",     "school",            "school"),
            ("teen",    "casual",            "studio"),
        ]:
            prompt = self._assemble(age_group=age_group, pose_style=pose, background_preset=bg)
            # Core safety negative terms must always appear
            assert "nsfw" in prompt.lower(), f"'nsfw' missing from negative for {age_group}"
            assert "nude" in prompt.lower(), f"'nude' missing from negative for {age_group}"
            assert "violence" in prompt.lower(), f"'violence' missing from negative for {age_group}"

    def test_safety_negative_contains_nsfw(self):
        prompt = self._assemble()
        assert "nsfw" in prompt.lower()

    def test_safety_negative_contains_nude(self):
        prompt = self._assemble()
        assert "nude" in prompt.lower()

    def test_safety_negative_contains_violence(self):
        prompt = self._assemble()
        assert "violence" in prompt.lower()

    def test_safety_negative_contains_alcohol(self):
        prompt = self._assemble()
        assert "alcohol" in prompt.lower()

    def test_safety_positive_contains_age_appropriate(self):
        prompt = self._assemble()
        assert "age-appropriate" in prompt.lower()

    def test_safety_positive_contains_child_safe(self):
        prompt = self._assemble()
        assert "child-safe" in prompt.lower()

    def test_safety_section_labelled_mandatory(self):
        """The SAFETY REQUIREMENTS section must be clearly labelled as mandatory."""
        prompt = self._assemble()
        assert "MANDATORY" in prompt or "mandatory" in prompt.lower()


# ---------------------------------------------------------------------------
# Camera angle descriptions
# ---------------------------------------------------------------------------

class TestChildrenCameraAngles:

    def test_children_variation_views_has_3_entries(self):
        from app.services.gemini import CHILDREN_VARIATION_VIEWS
        assert len(CHILDREN_VARIATION_VIEWS) == 3

    def test_children_camera_front_view(self):
        from app.services.gemini import CHILDREN_VARIATION_VIEWS
        front = CHILDREN_VARIATION_VIEWS[0]
        assert "front" in front.lower()
        assert "child" in front.lower()

    def test_children_camera_side_view_is_gentle(self):
        from app.services.gemini import CHILDREN_VARIATION_VIEWS
        side = CHILDREN_VARIATION_VIEWS[1]
        assert "side" in side.lower() or "45" in side
        # Should NOT use the word "dramatic" or "fashion-forward"
        assert "dramatic" not in side.lower()

    def test_children_camera_back_view(self):
        from app.services.gemini import CHILDREN_VARIATION_VIEWS
        back = CHILDREN_VARIATION_VIEWS[2]
        assert "back" in back.lower()

    def test_adult_and_children_views_are_different(self):
        from app.services.gemini import VARIATION_VIEWS, CHILDREN_VARIATION_VIEWS
        # None of the children views should be identical to adult views
        for child_view in CHILDREN_VARIATION_VIEWS:
            assert child_view not in VARIATION_VIEWS, \
                "Children camera view should differ from adult view"
