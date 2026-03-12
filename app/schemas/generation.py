"""Pydantic request/response schemas for generation endpoints."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.children_config import (
    AGE_GROUPS,
    VALID_GENDERS,
    get_allowed_poses,
    get_allowed_backgrounds,
)
from app.config.accessories import VALID_ACCESSORY_CATEGORIES, VALID_DISPLAY_MODES


# ---------------------------------------------------------------------------
# Request schemas — Adult module
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
    ethnicity: str = Field(default="", description="DEPRECATED — Sri Lankan identity is now hard-coded in prompts")
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


# ---------------------------------------------------------------------------
# Request schemas — Children's module
# ---------------------------------------------------------------------------

class ChildParamsCreate(BaseModel):
    """Parameters for children's clothing generation.

    Validated against the allowed options for the specified age group.
    """
    age_group: Literal["baby", "toddler", "kid", "teen"]
    child_gender: Literal["girl", "boy", "unisex"]
    pose_style: str = Field(..., description="Pose preset key (must be valid for age_group)")
    background_preset: str = Field(..., description="Background preset (must be valid for age_group)")
    hair_style: Optional[str] = Field(default=None, description="Hair style option")
    expression: Optional[str] = Field(default="happy", description="Facial expression")
    skin_tone: Optional[str] = Field(default="medium", description="Skin tone preset key")

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_age_group_params(self) -> "ChildParamsCreate":
        """Validate pose_style and background_preset against the age group."""
        age_group = self.age_group

        # Validate pose
        allowed_poses = get_allowed_poses(age_group)
        if allowed_poses and self.pose_style not in allowed_poses:
            raise ValueError(
                f"pose_style '{self.pose_style}' is not allowed for age group '{age_group}'. "
                f"Allowed: {allowed_poses}"
            )

        # Validate background
        allowed_backgrounds = get_allowed_backgrounds(age_group)
        if allowed_backgrounds and self.background_preset not in allowed_backgrounds:
            raise ValueError(
                f"background_preset '{self.background_preset}' is not allowed for age group "
                f"'{age_group}'. Allowed: {allowed_backgrounds}"
            )

        return self


# ---------------------------------------------------------------------------
# Request schemas — Fiton module
# ---------------------------------------------------------------------------

class CustomerMeasurements(BaseModel):
    """Customer body measurements (cm) for virtual fit-on."""

    bust_cm: float = Field(..., ge=60.0, le=150.0, description="Chest / bust in cm")
    waist_cm: float = Field(..., ge=50.0, le=130.0, description="Waist in cm")
    hips_cm: float = Field(..., ge=70.0, le=160.0, description="Hips in cm")
    height_cm: float = Field(default=160.0, ge=100.0, le=220.0, description="Height in cm")
    shoulder_width_cm: float | None = Field(
        default=None, ge=30.0, le=60.0, description="Shoulder width in cm (optional)"
    )
    skin_tone: str = Field(default="medium", description="Skin tone preset key (e.g. fair, medium, deep)")
    gender: str = Field(default="female", description="Customer gender: female | male")

    model_config = {"extra": "forbid"}


class GarmentMeasurements(BaseModel):
    """Actual garment dimensions (cm) — optional alternative to size label."""

    bust_cm: float | None = Field(default=None, ge=60.0, le=200.0, description="Garment chest / bust in cm")
    waist_cm: float | None = Field(default=None, ge=50.0, le=180.0, description="Garment waist in cm")
    hips_cm: float | None = Field(default=None, ge=70.0, le=200.0, description="Garment hips in cm")
    length_cm: float | None = Field(default=None, ge=30.0, le=200.0, description="Garment length in cm")
    shoulder_width_cm: float | None = Field(
        default=None, ge=30.0, le=80.0, description="Garment shoulder width in cm"
    )

    model_config = {"extra": "forbid"}


class FitonParamsCreate(BaseModel):
    """Parameters for the Virtual Fit-On module.

    Requires either garment_measurements OR garment_size_label (or both).
    """

    customer_photo_url: str = Field(..., description="Storage path of the uploaded customer photo")
    customer_measurements: CustomerMeasurements = Field(
        ..., description="Customer body measurements in cm"
    )
    garment_measurements: GarmentMeasurements | None = Field(
        default=None, description="Actual garment dimensions; preferred over size label"
    )
    garment_size_label: Literal["XS", "S", "M", "L", "XL", "XXL", "3XL"] | None = Field(
        default=None,
        description="Labelled size — used for size-chart lookup when garment_measurements not provided",
    )
    fit_preference: Literal["loose", "regular", "slim"] = Field(
        default="regular",
        description="Customer's preferred fit style: slim | regular | loose",
    )
    garment_type: Literal["dress", "top", "saree", "bottom", "full_outfit"] = Field(
        default="dress",
        description="Type of garment being tried on",
    )
    garment_description: dict | None = Field(
        default=None,
        description="Optional garment visual attributes: color, material, details",
    )

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def require_measurements_or_size(self) -> "FitonParamsCreate":
        """Either garment_measurements or garment_size_label must be provided."""
        if self.garment_measurements is None and self.garment_size_label is None:
            raise ValueError(
                "Either garment_measurements or garment_size_label must be provided."
            )
        return self


# ---------------------------------------------------------------------------
# Request schemas — Accessories module
# ---------------------------------------------------------------------------

class AccessoryParamsCreate(BaseModel):
    """Parameters for accessories generation.

    Validates that display-mode-specific required fields are present:
    - on_model  → model_skin_tone required
    - flat_lay  → background_surface required
    - lifestyle → context_scene recommended but not required
    """

    accessory_category: Literal[
        "necklace", "earrings", "bracelet", "ring",
        "handbag", "hat", "scarf", "crochet", "hair_accessory"
    ] = Field(..., description="Accessory subcategory")
    display_mode: Literal["on_model", "flat_lay", "lifestyle"] = Field(
        ..., description="How the accessory is displayed in the image"
    )
    context_scene: Optional[str] = Field(
        default=None, description="Lifestyle context scene key"
    )
    model_skin_tone: Optional[str] = Field(
        default=None, description="Skin tone preset; required when display_mode=on_model"
    )
    background_surface: Optional[str] = Field(
        default=None, description="Surface material; required when display_mode=flat_lay"
    )

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_display_mode_requirements(self) -> "AccessoryParamsCreate":
        """Enforce required fields for each display mode."""
        if self.display_mode == "on_model" and not self.model_skin_tone:
            raise ValueError(
                "model_skin_tone is required when display_mode='on_model'"
            )
        if self.display_mode == "flat_lay" and not self.background_surface:
            raise ValueError(
                "background_surface is required when display_mode='flat_lay'"
            )
        return self


# ---------------------------------------------------------------------------
# Main create request
# ---------------------------------------------------------------------------

class CreateGenerationRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    idempotency_key: str | None = None
    module: Literal["adult", "children", "accessories", "fiton"] = Field(
        default="adult",
        description="Which DrapeStudio module to use"
    )
    product_type: str = Field(default="clothing", description="clothing | accessories")
    garment_images: list[str] = Field(..., min_length=1, max_length=5)
    model_params: ModelParams | None = Field(
        default=None,
        description="Required when module=adult"
    )
    scene: SceneParams | None = Field(
        default=None,
        description="Required when module=adult"
    )
    child_params: ChildParamsCreate | None = Field(
        default=None,
        description="Required when module=children"
    )
    accessory_params: AccessoryParamsCreate | None = Field(
        default=None,
        description="Required when module=accessories"
    )
    fiton_params: FitonParamsCreate | None = Field(
        default=None,
        description="Required when module=fiton"
    )
    views: list[str] = Field(
        default=["front"],
        description="Selected views: front (required), side, back"
    )
    quality: str = Field(
        default="1k",
        description="Image quality tier: 1k, 2k, 4k"
    )
    output: OutputParams = OutputParams()

    @model_validator(mode="after")
    def check_module_params(self) -> "CreateGenerationRequest":
        """Ensure required params are present for the selected module."""
        if self.module == "adult":
            if self.model_params is None:
                raise ValueError("model_params is required when module='adult'")
            if self.scene is None:
                raise ValueError("scene is required when module='adult'")
        elif self.module == "children":
            if self.child_params is None:
                raise ValueError("child_params is required when module='children'")
        elif self.module == "accessories":
            if self.accessory_params is None:
                raise ValueError("accessory_params is required when module='accessories'")
        elif self.module == "fiton":
            if self.fiton_params is None:
                raise ValueError("fiton_params is required when module='fiton'")

        # Validate views
        valid_views = {"front", "side", "back"}
        if not all(v in valid_views for v in self.views):
            raise ValueError(f"Invalid views. Must be from: {valid_views}")
        if "front" not in self.views:
            raise ValueError("Front view is required")

        # Validate quality
        if self.quality not in ("1k", "2k", "4k"):
            raise ValueError("Quality must be 1k, 2k, or 4k")

        return self


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
