"""Pydantic request/response schemas for generation endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ModelMeasurements(BaseModel):
    """Optional physical measurements for the model."""
    height_cm: int | None = Field(default=None, description="Height in cm")
    weight_kg: float | None = Field(default=None, description="Weight in kg")
    chest_bust_cm: int | None = Field(default=None, description="Chest/bust in cm")
    waist_cm: int | None = Field(default=None, description="Waist in cm")
    hips_cm: int | None = Field(default=None, description="Hips in cm")
    inseam_cm: int | None = Field(default=None, description="Inseam in cm")
    shoe_size_eu: float | None = Field(default=None, description="Shoe size (EU)")


class ModelParams(BaseModel):
    age_range: str = Field(..., description="e.g. 18-24, 25-34, 35-44, 45+")
    gender_presentation: str = Field(..., description="feminine | masculine | neutral")
    ethnicity: str = Field(default="", description="sri_lankan | indian | middle_eastern | african | european")
    skin_tone: str = Field(..., description="Fitzpatrick 1-6")
    body_mode: str = Field(default="simple", description="simple (Phase 1)")
    body_type: str = Field(..., description="petite | average | athletic | curvy | plus")
    hair_style: str = Field(default="", description="Hair style preset key")
    hair_color: str = Field(default="", description="Hair color preset key")
    additional_description: str = Field(default="", description="Free-text extra model details")
    model_photo_url: str | None = Field(default=None, description="Storage path of uploaded model reference photo")
    measurements: ModelMeasurements | None = Field(default=None, description="Optional physical measurements")


class SceneParams(BaseModel):
    environment: str = Field(..., description="Environment preset key")
    pose_preset: str = Field(..., description="Pose preset key")
    framing: str = Field(..., description="Framing preset key")


class OutputParams(BaseModel):
    count: int = Field(default=3, ge=1, le=3)
    resolution: str = Field(default="high")


class CreateGenerationRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    idempotency_key: str | None = None
    product_type: str = Field(default="clothing", description="clothing | accessories")
    garment_images: list[str] = Field(..., min_length=1, max_length=5)
    model_params: ModelParams
    scene: SceneParams
    output: OutputParams = OutputParams()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class GenerationCreatedResponse(BaseModel):
    id: str
    status: str


class CostEstimate(BaseModel):
    credits: int = 1


class GenerationStatusResponse(BaseModel):
    id: str
    status: str
    created_at: datetime
    prompt_template_version: str
    cost_estimate: CostEstimate = CostEstimate()
    error_message: str | None = None


class OutputImage(BaseModel):
    image_url: str
    width: int | None = None
    height: int | None = None


class GenerationOutputsResponse(BaseModel):
    id: str
    status: str
    outputs: list[OutputImage] = []
    error_message: str | None = None
    cost_usd: float | None = None


# ---------------------------------------------------------------------------
# History schemas
# ---------------------------------------------------------------------------

class HistoryOutputImage(BaseModel):
    image_url: str
    variation_index: int
    width: int | None = None
    height: int | None = None


class HistoryItem(BaseModel):
    id: str
    status: str
    created_at: datetime
    garment_image_urls: list[str] = []
    output_images: list[HistoryOutputImage] = []
    model_params: dict = {}
    scene_params: dict = {}
    cost_usd: float | None = None
    duration_ms: int | None = None


class HistoryListResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    page: int
    per_page: int
    has_more: bool
