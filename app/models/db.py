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
