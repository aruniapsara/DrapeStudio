"""Pydantic request/response schemas for generation endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ModelParams(BaseModel):
    age_range: str = Field(..., description="e.g. 18-24, 25-34, 35-44, 45+")
    gender_presentation: str = Field(..., description="feminine | masculine | neutral")
    skin_tone: str = Field(..., description="Fitzpatrick 1-6")
    body_mode: str = Field(default="simple", description="simple (Phase 1)")
    body_type: str = Field(..., description="petite | average | athletic | curvy | plus")


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
