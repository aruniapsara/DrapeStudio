"""Tests for the Children's Module — data model, safety validator, and API."""

import uuid


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_children_body(
    age_group: str = "kid",
    child_gender: str = "girl",
    pose_style: str = "standing",
    background_preset: str = "park",
    hair_style: str | None = "ponytail",
    expression: str = "happy",
    garment_images: list[str] | None = None,
    idempotency_key: str | None = None,
) -> dict:
    """Return a valid POST /v1/generations body for the children's module."""
    return {
        "module": "children",
        "idempotency_key": idempotency_key or str(uuid.uuid4()),
        "garment_images": garment_images or ["local://uploads/test/front.jpg"],
        "child_params": {
            "age_group": age_group,
            "child_gender": child_gender,
            "pose_style": pose_style,
            "background_preset": background_preset,
            "hair_style": hair_style,
            "expression": expression,
        },
        "output": {"count": 3, "resolution": "high"},
    }


# ---------------------------------------------------------------------------
# ── Children config / age groups ──────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestAgeGroupConfig:

    def test_all_age_groups_present(self):
        from app.children_config import AGE_GROUPS
        assert set(AGE_GROUPS.keys()) == {"baby", "toddler", "kid", "teen"}

    def test_baby_poses(self):
        from app.children_config import get_allowed_poses
        poses = get_allowed_poses("baby")
        assert "sitting" in poses
        assert "lying" in poses
        assert "held" in poses
        # baby must NOT allow teen poses
        assert "fashion_standing" not in poses
        assert "urban" not in poses

    def test_toddler_poses(self):
        from app.children_config import get_allowed_poses
        poses = get_allowed_poses("toddler")
        assert "standing" in poses
        assert "playing" in poses
        assert "fashion_standing" not in poses

    def test_kid_poses(self):
        from app.children_config import get_allowed_poses
        poses = get_allowed_poses("kid")
        assert "standing" in poses
        assert "school" in poses

    def test_teen_poses(self):
        from app.children_config import get_allowed_poses
        poses = get_allowed_poses("teen")
        assert "fashion_standing" in poses
        assert "urban" in poses

    def test_each_group_has_required_keys(self):
        from app.children_config import AGE_GROUPS
        required = {"age_range", "proportions", "poses", "backgrounds", "hair_options", "expressions"}
        for group_name, group in AGE_GROUPS.items():
            missing = required - set(group.keys())
            assert not missing, f"Age group '{group_name}' is missing keys: {missing}"

    def test_get_allowed_backgrounds(self):
        from app.children_config import get_allowed_backgrounds
        assert "nursery" in get_allowed_backgrounds("baby")
        assert "urban" in get_allowed_backgrounds("teen")


# ---------------------------------------------------------------------------
# ── Safety validator ──────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestChildSafetyValidator:

    def test_valid_params_pass(self):
        from app.services.safety import ChildSafetyValidator
        valid, msg = ChildSafetyValidator.validate_child_params(
            "kid",
            {"pose_style": "standing", "background_preset": "park"},
        )
        assert valid is True
        assert msg == ""

    def test_invalid_age_group_fails(self):
        from app.services.safety import ChildSafetyValidator
        valid, msg = ChildSafetyValidator.validate_child_params(
            "adult",
            {"pose_style": "standing", "background_preset": "park"},
        )
        assert valid is False
        assert "age group" in msg.lower()

    def test_baby_cannot_use_fashion_standing(self):
        """Core safety rule: baby's allowed poses exclude 'fashion_standing'."""
        from app.services.safety import ChildSafetyValidator
        valid, msg = ChildSafetyValidator.validate_child_params(
            "baby",
            {"pose_style": "fashion_standing", "background_preset": "nursery"},
        )
        assert valid is False
        assert "pose_style" in msg.lower() or "fashion_standing" in msg.lower()

    def test_toddler_cannot_use_urban_background(self):
        from app.services.safety import ChildSafetyValidator
        valid, msg = ChildSafetyValidator.validate_child_params(
            "toddler",
            {"pose_style": "standing", "background_preset": "urban"},
        )
        assert valid is False
        assert "background_preset" in msg.lower() or "urban" in msg.lower()

    def test_blocked_term_rejected(self):
        from app.services.safety import ChildSafetyValidator
        valid, msg = ChildSafetyValidator.validate_child_params(
            "teen",
            {
                "pose_style": "casual",
                "background_preset": "studio",
                "hair_style": "nsfw long hair",
            },
        )
        assert valid is False
        assert "nsfw" in msg.lower() or "blocked" in msg.lower()

    def test_nude_term_rejected(self):
        from app.services.safety import ChildSafetyValidator
        valid, msg = ChildSafetyValidator.validate_child_params(
            "teen",
            {
                "pose_style": "casual",
                "background_preset": "studio",
                "additional_description": "nude pose",
            },
        )
        assert valid is False

    def test_safety_prompt_additions_structure(self):
        from app.services.safety import ChildSafetyValidator
        additions = ChildSafetyValidator.get_safety_prompt_additions()
        assert "positive" in additions
        assert "negative" in additions
        # Must include all mandatory constraints
        assert "fully clothed" in additions["positive"]
        assert "child-safe" in additions["positive"]
        # Must include all mandatory negative terms
        assert "nsfw" in additions["negative"]
        assert "nude" in additions["negative"]
        assert "violence" in additions["negative"]

    def test_mandatory_negative_prompts_all_present(self):
        from app.services.safety import ChildSafetyValidator
        neg = ChildSafetyValidator.get_safety_prompt_additions()["negative"]
        for term in ChildSafetyValidator.MANDATORY_NEGATIVE_PROMPTS:
            assert term in neg, f"Mandatory negative term '{term}' missing from additions"

    def test_scan_for_blocked_terms_finds_term(self):
        from app.services.safety import ChildSafetyValidator
        found = ChildSafetyValidator.scan_for_blocked_terms("this text contains nsfw content")
        assert found == "nsfw"

    def test_scan_for_blocked_terms_returns_none_for_clean_text(self):
        from app.services.safety import ChildSafetyValidator
        found = ChildSafetyValidator.scan_for_blocked_terms("a happy child wearing a blue dress")
        assert found is None


# ---------------------------------------------------------------------------
# ── Pydantic schema validation ────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestChildParamsSchema:

    def test_valid_child_params_accepted(self):
        from app.schemas.generation import ChildParamsCreate
        cp = ChildParamsCreate(
            age_group="kid",
            child_gender="girl",
            pose_style="standing",
            background_preset="park",
            expression="happy",
        )
        assert cp.age_group == "kid"
        assert cp.child_gender == "girl"

    def test_invalid_pose_for_baby_rejected(self):
        from pydantic import ValidationError
        from app.schemas.generation import ChildParamsCreate
        try:
            ChildParamsCreate(
                age_group="baby",
                child_gender="girl",
                pose_style="fashion_standing",   # Not allowed for baby
                background_preset="nursery",
            )
            raise AssertionError("Should have raised ValidationError")
        except ValidationError as e:
            assert "fashion_standing" in str(e) or "pose_style" in str(e)

    def test_invalid_background_for_baby_rejected(self):
        from pydantic import ValidationError
        from app.schemas.generation import ChildParamsCreate
        try:
            ChildParamsCreate(
                age_group="baby",
                child_gender="unisex",
                pose_style="sitting",
                background_preset="urban",  # Not allowed for baby
            )
            raise AssertionError("Should have raised ValidationError")
        except ValidationError as e:
            assert "background_preset" in str(e) or "urban" in str(e)

    def test_adult_module_requires_model_params(self):
        from pydantic import ValidationError
        from app.schemas.generation import CreateGenerationRequest
        try:
            CreateGenerationRequest(
                module="adult",
                garment_images=["local://uploads/test/front.jpg"],
                # model_params intentionally omitted → should fail
            )
            raise AssertionError("Should have raised ValidationError")
        except ValidationError as e:
            assert "model_params" in str(e)

    def test_children_module_requires_child_params(self):
        from pydantic import ValidationError
        from app.schemas.generation import CreateGenerationRequest
        try:
            CreateGenerationRequest(
                module="children",
                garment_images=["local://uploads/test/front.jpg"],
                # child_params intentionally omitted → should fail
            )
            raise AssertionError("Should have raised ValidationError")
        except ValidationError as e:
            assert "child_params" in str(e)


# ---------------------------------------------------------------------------
# ── API integration tests ────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestChildrenAPI:

    def test_create_children_generation_returns_201(self, client):
        body = _make_children_body()
        resp = client.post("/v1/generations", json=body)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["id"].startswith("gen_")
        assert data["status"] == "queued"

    def test_children_generation_stores_module_field(self, client, db_session):
        from app.models.db import GenerationRequest
        body = _make_children_body()
        resp = client.post("/v1/generations", json=body)
        assert resp.status_code == 201
        gen_id = resp.json()["id"]

        gen = db_session.query(GenerationRequest).filter(
            GenerationRequest.id == gen_id
        ).first()
        assert gen is not None
        assert gen.module == "children"

    def test_children_generation_creates_child_params_record(self, client, db_session):
        from app.models.db import ChildParams
        body = _make_children_body(
            age_group="teen",
            child_gender="girl",
            pose_style="fashion_standing",
            background_preset="urban",
            hair_style="ponytail",
        )
        resp = client.post("/v1/generations", json=body)
        assert resp.status_code == 201
        gen_id = resp.json()["id"]

        cp = db_session.query(ChildParams).filter(
            ChildParams.generation_request_id == gen_id
        ).first()
        assert cp is not None
        assert cp.age_group == "teen"
        assert cp.child_gender == "girl"
        assert cp.pose_style == "fashion_standing"
        assert cp.background_preset == "urban"

    def test_all_four_age_groups_via_api(self, client):
        """Each age group should create a generation with valid params."""
        test_cases = [
            ("baby",    "unisex", "sitting",          "nursery"),
            ("toddler", "girl",   "standing",          "garden"),
            ("kid",     "boy",    "school",            "school"),
            ("teen",    "girl",   "fashion_standing",  "urban"),
        ]
        for age_group, gender, pose, bg in test_cases:
            body = _make_children_body(
                age_group=age_group,
                child_gender=gender,
                pose_style=pose,
                background_preset=bg,
            )
            resp = client.post("/v1/generations", json=body)
            assert resp.status_code == 201, (
                f"Failed for age_group={age_group}: {resp.text}"
            )

    def test_invalid_pose_for_baby_returns_error(self, client):
        """Baby cannot use 'fashion_standing' — should return 422."""
        body = _make_children_body(
            age_group="baby",
            pose_style="fashion_standing",  # Invalid for baby
            background_preset="nursery",
        )
        resp = client.post("/v1/generations", json=body)
        assert resp.status_code == 422, resp.text

    def test_blocked_term_in_hair_style_rejected(self, client):
        """A blocked term in any field must be rejected with 422."""
        body = _make_children_body(age_group="teen", pose_style="casual", background_preset="studio")
        body["child_params"]["hair_style"] = "nsfw style"
        resp = client.post("/v1/generations", json=body)
        assert resp.status_code == 422, resp.text

    def test_adult_module_still_works(self, client):
        """Existing adult module must still return 201 (backward compat)."""
        body = {
            "module": "adult",
            "idempotency_key": str(uuid.uuid4()),
            "garment_images": ["local://uploads/test/front.jpg"],
            "model_params": {
                "age_range": "25-34",
                "gender_presentation": "feminine",
                "skin_tone": "4",
                "body_mode": "simple",
                "body_type": "curvy",
            },
            "scene": {
                "environment": "studio_white",
                "pose_preset": "front_standing",
                "framing": "full_body",
            },
            "output": {"count": 3, "resolution": "high"},
        }
        resp = client.post("/v1/generations", json=body)
        assert resp.status_code == 201, resp.text

    def test_adult_module_stores_adult_module_field(self, client, db_session):
        from app.models.db import GenerationRequest
        body = {
            "idempotency_key": str(uuid.uuid4()),
            "garment_images": ["local://uploads/test/front.jpg"],
            "model_params": {
                "age_range": "25-34",
                "gender_presentation": "feminine",
                "skin_tone": "4",
                "body_mode": "simple",
                "body_type": "curvy",
            },
            "scene": {
                "environment": "studio_white",
                "pose_preset": "front_standing",
                "framing": "full_body",
            },
        }
        resp = client.post("/v1/generations", json=body)
        assert resp.status_code == 201
        gen_id = resp.json()["id"]

        gen = db_session.query(GenerationRequest).filter(
            GenerationRequest.id == gen_id
        ).first()
        assert gen.module == "adult"
