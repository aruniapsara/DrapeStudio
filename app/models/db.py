"""All SQLAlchemy ORM models for DrapeStudio."""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import relationship
from ulid import ULID

from app.database import Base


def generate_ulid() -> str:
    """Generate a new ULID string."""
    return str(ULID())


def generate_gen_id() -> str:
    """Generate a ULID prefixed with 'gen_' for generation requests."""
    return "gen_" + str(ULID())


class GenerationRequest(Base):
    __tablename__ = "generation_request"

    id = Column(String, primary_key=True, default=generate_gen_id)
    session_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="queued")
    # status values: queued | running | succeeded | failed
    module = Column(String(20), nullable=True, default="adult")
    garment_image_urls = Column(JSON, nullable=False)
    model_params = Column(JSON, nullable=False)
    scene_params = Column(JSON, nullable=False)
    output_count = Column(Integer, nullable=False, default=3)
    prompt_template_version = Column(String, nullable=False, default="v0.1")
    idempotency_key = Column(String, unique=True, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    outputs = relationship("GenerationOutput", back_populates="request")
    usage = relationship("UsageCost", back_populates="request", uselist=False)
    child_params = relationship(
        "ChildParams", back_populates="generation_request", uselist=False
    )
    accessory_params = relationship(
        "AccessoryParams", back_populates="generation_request", uselist=False
    )


class GenerationOutput(Base):
    __tablename__ = "generation_output"

    id = Column(String, primary_key=True, default=generate_ulid)
    generation_request_id = Column(
        String,
        ForeignKey("generation_request.id"),
        nullable=False,
    )
    image_url = Column(String, nullable=False)
    variation_index = Column(Integer, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    request = relationship("GenerationRequest", back_populates="outputs")


class UsageCost(Base):
    __tablename__ = "usage_cost"

    id = Column(String, primary_key=True, default=generate_ulid)
    generation_request_id = Column(
        String,
        ForeignKey("generation_request.id"),
        nullable=False,
    )
    provider = Column(String, nullable=False, default="google_gemini")
    model_name = Column(String, nullable=False)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    estimated_cost_usd = Column(Numeric(10, 6), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    request = relationship("GenerationRequest", back_populates="usage")


class AccessoryParams(Base):
    __tablename__ = "accessory_params"

    id = Column(String(26), primary_key=True, default=generate_ulid)
    generation_request_id = Column(
        String(26),
        ForeignKey("generation_request.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    accessory_category = Column(String(30), nullable=False)   # necklace | earrings | ...
    display_mode = Column(String(20), nullable=False)          # on_model | flat_lay | lifestyle
    context_scene = Column(String(30), nullable=True)
    model_skin_tone = Column(String(20), nullable=True)        # only for on_model
    background_surface = Column(String(30), nullable=True)     # only for flat_lay
    created_at = Column(DateTime, default=datetime.utcnow)

    generation_request = relationship(
        "GenerationRequest", back_populates="accessory_params"
    )


class ChildParams(Base):
    __tablename__ = "child_params"

    id = Column(String(26), primary_key=True, default=generate_ulid)
    generation_request_id = Column(
        String(26),
        ForeignKey("generation_request.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    age_group = Column(String(10), nullable=False)          # baby | toddler | kid | teen
    child_gender = Column(String(10), nullable=False)       # girl | boy | unisex
    pose_style = Column(String(30), nullable=False)
    background_preset = Column(String(30), nullable=False)
    hair_style = Column(String(30), nullable=True)
    expression = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    generation_request = relationship(
        "GenerationRequest", back_populates="child_params"
    )
