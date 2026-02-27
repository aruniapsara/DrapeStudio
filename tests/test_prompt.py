"""Tests for prompt template loading and assembly."""

from app.services.prompt import assemble_prompt, load_template


def test_template_loads_correctly():
    """YAML template loads and has expected keys."""
    template = load_template("v0.1")
    assert template["version"] == "v0.1"
    assert "quality" in template
    assert "output" in template
    assert "negative" in template
    assert "environments" in template
    assert "poses" in template
    assert "framing" in template
    assert "lighting" in template


def test_template_has_all_environments():
    """Template includes all 7 environment presets."""
    template = load_template("v0.1")
    expected = [
        "studio_white",
        "studio_beige",
        "outdoor_street",
        "outdoor_park",
        "outdoor_beach",
        "indoor_cafe",
        "indoor_home",
    ]
    for env in expected:
        assert env in template["environments"], f"Missing environment: {env}"


def test_template_has_all_poses():
    """Template includes all 4 pose presets."""
    template = load_template("v0.1")
    expected = ["front_standing", "walking", "three_quarter", "seated"]
    for pose in expected:
        assert pose in template["poses"], f"Missing pose: {pose}"


def test_template_has_all_framing():
    """Template includes all 3 framing options."""
    template = load_template("v0.1")
    expected = ["full_body", "three_quarter", "waist_up"]
    for framing in expected:
        assert framing in template["framing"], f"Missing framing: {framing}"


def test_assemble_prompt_basic():
    """Prompt assembly produces a non-empty string with expected content."""
    model_params = {
        "age_range": "25-34",
        "gender_presentation": "feminine",
        "skin_tone": "4",
        "body_mode": "simple",
        "body_type": "curvy",
    }
    scene_params = {
        "environment": "studio_white",
        "pose_preset": "front_standing",
        "framing": "full_body",
    }

    prompt = assemble_prompt(model_params, scene_params, "v0.1")

    assert len(prompt) > 100
    assert "feminine" in prompt
    assert "25-34" in prompt
    assert "skin tone 4" in prompt
    assert "curvy" in prompt
    assert "studio" in prompt.lower() or "white" in prompt.lower()
    assert "standing" in prompt.lower()
    assert "full body" in prompt.lower()


def test_assemble_prompt_different_params():
    """Prompt changes when different parameters are passed."""
    base_params = {
        "age_range": "18-24",
        "gender_presentation": "masculine",
        "skin_tone": "2",
        "body_mode": "simple",
        "body_type": "athletic",
    }
    scene_params = {
        "environment": "outdoor_park",
        "pose_preset": "walking",
        "framing": "three_quarter",
    }

    prompt = assemble_prompt(base_params, scene_params, "v0.1")

    assert "masculine" in prompt
    assert "18-24" in prompt
    assert "skin tone 2" in prompt
    assert "athletic" in prompt
    assert "park" in prompt.lower()
    assert "walking" in prompt.lower()


def test_assemble_prompt_all_environments():
    """Prompt assembly works for every environment option."""
    model_params = {
        "age_range": "35-44",
        "gender_presentation": "neutral",
        "skin_tone": "5",
        "body_mode": "simple",
        "body_type": "average",
    }

    environments = [
        "studio_white",
        "studio_beige",
        "outdoor_street",
        "outdoor_park",
        "outdoor_beach",
        "indoor_cafe",
        "indoor_home",
    ]

    for env in environments:
        scene_params = {
            "environment": env,
            "pose_preset": "front_standing",
            "framing": "full_body",
        }
        prompt = assemble_prompt(model_params, scene_params, "v0.1")
        assert len(prompt) > 100, f"Empty prompt for environment: {env}"
