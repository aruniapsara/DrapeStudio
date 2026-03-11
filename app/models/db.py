"""All SQLAlchemy ORM models for DrapeStudio."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
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


class User(Base):
    """Registered user (Google OAuth or legacy phone-OTP auth)."""

    __tablename__ = "user"

    id = Column(String(26), primary_key=True, default=generate_ulid)
    phone = Column(String(20), unique=True, nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    avatar_url = Column(String(500), nullable=True)
    display_name = Column(String(100), nullable=True)
    role = Column(String(20), nullable=False, default="user")
    credits_remaining = Column(Integer, nullable=False, default=3)
    language_preference = Column(String(5), nullable=False, default="en")
    sms_notifications_enabled = Column(Boolean, nullable=False, default=False)
    push_notifications_enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    generation_requests = relationship("GenerationRequest", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    credit_transactions = relationship("CreditTransaction", back_populates="user")
    push_subscriptions = relationship("PushSubscription", back_populates="user")


class OTPRequest(Base):
    """One-time password requests for phone verification."""

    __tablename__ = "otp_request"

    id = Column(String(26), primary_key=True, default=generate_ulid)
    phone = Column(String(20), nullable=False, index=True)
    otp_hash = Column(String(64), nullable=False)    # SHA-256 hex
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class GenerationRequest(Base):
    __tablename__ = "generation_request"

    id = Column(String, primary_key=True, default=generate_gen_id)
    session_id = Column(String, nullable=False, index=True)
    user_id = Column(String(26), ForeignKey("user.id"), nullable=True, index=True)
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
    user = relationship("User", back_populates="generation_requests")
    child_params = relationship(
        "ChildParams", back_populates="generation_request", uselist=False
    )
    accessory_params = relationship(
        "AccessoryParams", back_populates="generation_request", uselist=False
    )
    fiton_request = relationship(
        "FitonRequest", back_populates="generation_request", uselist=False
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


class FitonRequest(Base):
    """Virtual Fit-On request parameters and size recommendation outputs."""

    __tablename__ = "fiton_request"

    id = Column(String(26), primary_key=True, default=generate_ulid)
    generation_request_id = Column(
        String(26),
        ForeignKey("generation_request.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # Customer inputs
    customer_photo_url = Column(String(500), nullable=False)
    customer_measurements = Column(JSON, nullable=False)
    # {bust_cm, waist_cm, hips_cm, height_cm, shoulder_width_cm}
    garment_measurements = Column(JSON, nullable=True)
    # {bust_cm, waist_cm, hips_cm, length_cm, shoulder_width_cm}
    garment_size_label = Column(String(10), nullable=True)  # XS, S, M, L, XL, XXL, 3XL
    fit_preference = Column(String(10), nullable=True)      # loose | regular | slim

    # Computed outputs (filled in by worker after size recommendation runs)
    recommended_size = Column(String(10), nullable=True)
    fit_confidence = Column(Float, nullable=True)            # 0–100%
    fit_details = Column(JSON, nullable=True)
    # {bust: "good", waist: "tight", hips: "perfect", length: "-2cm short"}

    created_at = Column(DateTime, default=datetime.utcnow)

    generation_request = relationship(
        "GenerationRequest", back_populates="fiton_request"
    )


# ── Billing models ────────────────────────────────────────────────────────────

class Subscription(Base):
    """User's subscription to a paid plan."""

    __tablename__ = "subscription"

    id = Column(String(26), primary_key=True, default=generate_ulid)
    user_id = Column(
        String(26), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan = Column(String(20), nullable=False)     # free | basic | pro
    status = Column(String(20), nullable=False)   # active | cancelled | expired | past_due
    credits_total = Column(Integer, nullable=False)
    credits_used = Column(Integer, nullable=False, default=0)
    credits_reset_date = Column(DateTime, nullable=True)
    payhere_subscription_id = Column(String(100), nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription")


class Payment(Base):
    """PayHere payment record."""

    __tablename__ = "payment"

    id = Column(String(26), primary_key=True, default=generate_ulid)
    user_id = Column(String(26), ForeignKey("user.id"), nullable=False, index=True)
    subscription_id = Column(String(26), ForeignKey("subscription.id"), nullable=True)
    amount_lkr = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="LKR")
    status = Column(String(20), nullable=False)   # pending | completed | failed | refunded
    payhere_payment_id = Column(String(100), nullable=True)
    payment_method = Column(String(50), nullable=True)
    description = Column(String(200), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")


class CreditTransaction(Base):
    """Credit ledger — every deduction and grant is recorded here."""

    __tablename__ = "credit_transaction"

    id = Column(String(26), primary_key=True, default=generate_ulid)
    user_id = Column(String(26), ForeignKey("user.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)         # +ve = credit, -ve = debit
    balance_after = Column(Integer, nullable=False)
    transaction_type = Column(String(30), nullable=False)
    # generation | subscription_credit | daily_free | refund | admin_grant
    reference_id = Column(String(26), nullable=True)  # generation_request.id
    description = Column(String(200), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="credit_transactions")


class SourceImage(Base):
    """Tracked source image (garment, accessory, or model photo) uploaded by a user."""

    __tablename__ = "source_image"

    id = Column(String(26), primary_key=True, default=generate_ulid)
    user_id = Column(String(26), ForeignKey("user.id"), nullable=True, index=True)
    session_id = Column(String, nullable=False, index=True)
    image_url = Column(String(500), nullable=False, unique=True)
    image_type = Column(String(20), nullable=False)  # garment | model_photo | accessory
    original_filename = Column(String(255), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class PushSubscription(Base):
    """Web Push API subscription stored per user device."""

    __tablename__ = "push_subscription"

    id = Column(String(26), primary_key=True, default=generate_ulid)
    user_id = Column(
        String(26), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    endpoint = Column(String(500), nullable=False, unique=True)
    keys_p256dh = Column(String(200), nullable=False)
    keys_auth = Column(String(200), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="push_subscriptions")
