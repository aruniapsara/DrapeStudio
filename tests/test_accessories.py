"""Tests for accessories module: config, schema validation, and API endpoint."""

import pytest
import uuid

from app.config.accessories import (
    ACCESSORY_CATEGORIES,
    DISPLAY_MODES,
    BACKGROUND_SURFACES,
    VALID_ACCESSORY_CATEGORIES,
    VALID_DISPLAY_MODES,
)
from app.schemas.generation import AccessoryParamsCreate, CreateGenerationRequest


# ---------------------------------------------------------------------------
# Task 1: Category configuration tests
# ---------------------------------------------------------------------------

def test_all_nine_categories_present():
    """All 9 accessory categories must be defined."""
    expected = {
        "necklace", "earrings", "bracelet", "ring",
        "handbag", "hat", "scarf", "crochet", "hair_accessory",
    }
    assert set(ACCESSORY_CATEGORIES.keys()) == expected


def test_every_category_has_all_display_modes():
    """Each category must have 'on_model', 'flat_lay', and 'lifestyle' configs."""
    for category, config in ACCESSORY_CATEGORIES.items():
        for mode in ["on_model", "flat_lay", "lifestyle"]:
            assert mode in config, (
                f"Category '{category}' is missing display_mode '{mode}'"
            )


def test_every_category_has_ai_params():
    """Each category must have at least one ai_params entry."""
    for category, config in ACCESSORY_CATEGORIES.items():
        assert "ai_params" in config, f"Category '{category}' missing 'ai_params'"
        assert len(config["ai_params"]) >= 1, (
            f"Category '{category}' has empty ai_params list"
        )


def test_on_model_config_has_required_keys():
    """Each on_model config must have body_area, framing, model_needs."""
    required_keys = {"body_area", "framing", "model_needs"}
    for category, config in ACCESSORY_CATEGORIES.items():
        on_model = config["on_model"]
        missing = required_keys - set(on_model.keys())
        assert not missing, (
            f"Category '{category}' on_model is missing: {missing}"
        )


def test_flat_lay_config_has_required_keys():
    """Each flat_lay config must have surface and arrangement."""
    required_keys = {"surface", "arrangement"}
    for category, config in ACCESSORY_CATEGORIES.items():
        flat_lay = config["flat_lay"]
        missing = required_keys - set(flat_lay.keys())
        assert not missing, (
            f"Category '{category}' flat_lay is missing: {missing}"
        )


def test_display_modes_list():
    """DISPLAY_MODES list must contain exactly three modes."""
    assert set(DISPLAY_MODES) == {"on_model", "flat_lay", "lifestyle"}


def test_background_surfaces_coverage():
    """BACKGROUND_SURFACES must have entries for flat_lay and lifestyle."""
    assert "flat_lay" in BACKGROUND_SURFACES
    assert "lifestyle" in BACKGROUND_SURFACES
    assert len(BACKGROUND_SURFACES["flat_lay"]) >= 1
    assert len(BACKGROUND_SURFACES["lifestyle"]) >= 1


def test_valid_sets_populated():
    """Convenience sets must contain all expected values."""
    assert "necklace" in VALID_ACCESSORY_CATEGORIES
    assert "hair_accessory" in VALID_ACCESSORY_CATEGORIES
    assert "on_model" in VALID_DISPLAY_MODES
    assert len(VALID_ACCESSORY_CATEGORIES) == 9
    assert len(VALID_DISPLAY_MODES) == 3


# ---------------------------------------------------------------------------
# Task 2: Pydantic schema validation tests
# ---------------------------------------------------------------------------

def test_on_model_requires_skin_tone():
    """display_mode='on_model' must provide model_skin_tone."""
    with pytest.raises(Exception, match="model_skin_tone"):
        AccessoryParamsCreate(
            accessory_category="necklace",
            display_mode="on_model",
            # model_skin_tone intentionally omitted
        )


def test_flat_lay_requires_background_surface():
    """display_mode='flat_lay' must provide background_surface."""
    with pytest.raises(Exception, match="background_surface"):
        AccessoryParamsCreate(
            accessory_category="earrings",
            display_mode="flat_lay",
            # background_surface intentionally omitted
        )


def test_lifestyle_no_required_fields():
    """display_mode='lifestyle' does not require skin_tone or surface."""
    params = AccessoryParamsCreate(
        accessory_category="hat",
        display_mode="lifestyle",
        context_scene="garden",
    )
    assert params.display_mode == "lifestyle"
    assert params.accessory_category == "hat"


def test_on_model_valid():
    """A fully-populated on_model request passes validation."""
    params = AccessoryParamsCreate(
        accessory_category="bracelet",
        display_mode="on_model",
        model_skin_tone="medium",
    )
    assert params.model_skin_tone == "medium"
    assert params.background_surface is None


def test_flat_lay_valid():
    """A fully-populated flat_lay request passes validation."""
    params = AccessoryParamsCreate(
        accessory_category="ring",
        display_mode="flat_lay",
        background_surface="white_marble",
    )
    assert params.background_surface == "white_marble"
    assert params.model_skin_tone is None


def test_invalid_category_rejected():
    """An unknown category must be rejected by the Literal validator."""
    with pytest.raises(Exception):
        AccessoryParamsCreate(
            accessory_category="sunglasses",   # not in the Literal
            display_mode="lifestyle",
        )


def test_invalid_display_mode_rejected():
    """An unknown display_mode must be rejected."""
    with pytest.raises(Exception):
        AccessoryParamsCreate(
            accessory_category="necklace",
            display_mode="hanging",   # not in the Literal
            model_skin_tone="light",
        )


def test_all_nine_categories_accepted_on_model():
    """Every one of the 9 categories can be instantiated as on_model."""
    for cat in VALID_ACCESSORY_CATEGORIES:
        params = AccessoryParamsCreate(
            accessory_category=cat,  # type: ignore[arg-type]
            display_mode="on_model",
            model_skin_tone="medium",
        )
        assert params.accessory_category == cat


def test_all_nine_categories_accepted_flat_lay():
    """Every one of the 9 categories can be instantiated as flat_lay."""
    for cat in VALID_ACCESSORY_CATEGORIES:
        params = AccessoryParamsCreate(
            accessory_category=cat,  # type: ignore[arg-type]
            display_mode="flat_lay",
            background_surface="linen_cloth",
        )
        assert params.display_mode == "flat_lay"


# ---------------------------------------------------------------------------
# Task 3: API endpoint tests
# ---------------------------------------------------------------------------

def _accessories_body(
    category="necklace",
    display_mode="on_model",
    model_skin_tone="medium",
    background_surface=None,
    context_scene=None,
    idempotency_key=None,
):
    body = {
        "module": "accessories",
        "idempotency_key": idempotency_key or str(uuid.uuid4()),
        "garment_images": ["local://uploads/test-session/necklace.jpg"],
        "accessory_params": {
            "accessory_category": category,
            "display_mode": display_mode,
        },
        "output": {"count": 3},
    }
    if model_skin_tone is not None:
        body["accessory_params"]["model_skin_tone"] = model_skin_tone
    if background_surface is not None:
        body["accessory_params"]["background_surface"] = background_surface
    if context_scene is not None:
        body["accessory_params"]["context_scene"] = context_scene
    return body


def test_api_accepts_accessories_on_model(client):
    """POST /v1/generations with module=accessories (on_model) returns 201."""
    resp = client.post("/v1/generations", json=_accessories_body())
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "id" in data
    assert data["id"].startswith("gen_")
    assert data["status"] == "queued"


def test_api_accepts_accessories_flat_lay(client):
    """POST /v1/generations with display_mode=flat_lay returns 201."""
    body = _accessories_body(
        display_mode="flat_lay",
        model_skin_tone=None,
        background_surface="wooden_table",
    )
    resp = client.post("/v1/generations", json=body)
    assert resp.status_code == 201, resp.text


def test_api_accepts_accessories_lifestyle(client):
    """POST /v1/generations with display_mode=lifestyle returns 201."""
    body = _accessories_body(
        display_mode="lifestyle",
        model_skin_tone=None,
        context_scene="garden",
    )
    resp = client.post("/v1/generations", json=body)
    assert resp.status_code == 201, resp.text


def test_api_rejects_on_model_without_skin_tone(client):
    """display_mode=on_model without model_skin_tone must return 422."""
    body = _accessories_body(display_mode="on_model", model_skin_tone=None)
    resp = client.post("/v1/generations", json=body)
    assert resp.status_code == 422, resp.text


def test_api_rejects_flat_lay_without_surface(client):
    """display_mode=flat_lay without background_surface must return 422."""
    body = _accessories_body(
        display_mode="flat_lay",
        model_skin_tone=None,
        background_surface=None,
    )
    resp = client.post("/v1/generations", json=body)
    assert resp.status_code == 422, resp.text


def test_api_rejects_accessories_missing_params(client):
    """module=accessories without accessory_params must return 422."""
    body = {
        "module": "accessories",
        "garment_images": ["local://uploads/test-session/item.jpg"],
        "output": {"count": 3},
    }
    resp = client.post("/v1/generations", json=body)
    assert resp.status_code == 422, resp.text


def test_api_all_categories_on_model(client):
    """All 9 accessory categories are accepted by the API for on_model."""
    for cat in sorted(VALID_ACCESSORY_CATEGORIES):
        body = _accessories_body(category=cat)
        resp = client.post("/v1/generations", json=body)
        assert resp.status_code == 201, f"Category '{cat}' failed: {resp.text}"


def test_accessories_generation_status_queryable(client):
    """After creation, GET /v1/generations/{id} returns status."""
    resp = client.post("/v1/generations", json=_accessories_body())
    assert resp.status_code == 201
    gen_id = resp.json()["id"]

    status_resp = client.get(f"/v1/generations/{gen_id}")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["id"] == gen_id
    assert data["status"] == "queued"


def test_accessories_idempotency(client):
    """Same idempotency key + same params returns existing generation."""
    key = str(uuid.uuid4())
    body = _accessories_body(idempotency_key=key)

    resp1 = client.post("/v1/generations", json=body)
    assert resp1.status_code == 201
    gen_id = resp1.json()["id"]

    resp2 = client.post("/v1/generations", json=body)
    assert resp2.status_code == 201
    assert resp2.json()["id"] == gen_id
