"""OTP generation, hashing, verification, and SMS delivery via Notify.lk."""

import hashlib
import logging
import random
import re
from datetime import datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.db import OTPRequest

logger = logging.getLogger(__name__)

# Phone format: +94 followed by 9 digits (Sri Lanka)
_PHONE_RE = re.compile(r"^\+94\d{9}$")

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
MAX_ATTEMPTS = 3
COOLDOWN_SECONDS = 60


class OTPService:
    """Phone-OTP authentication helpers."""

    # ── Validation ────────────────────────────────────────────────────────
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Return True if phone matches +94XXXXXXXXX format."""
        return bool(_PHONE_RE.match(phone))

    # ── OTP generation & hashing ──────────────────────────────────────────
    @staticmethod
    def generate_otp() -> str:
        """Generate a 6-digit zero-padded OTP string."""
        return str(random.randint(0, 10**OTP_LENGTH - 1)).zfill(OTP_LENGTH)

    @staticmethod
    def hash_otp(otp: str) -> str:
        """Return SHA-256 hex digest of the OTP."""
        return hashlib.sha256(otp.encode()).hexdigest()

    @staticmethod
    def _verify_hash(otp: str, otp_hash: str) -> bool:
        return hashlib.sha256(otp.encode()).hexdigest() == otp_hash

    # ── Rate limiting ─────────────────────────────────────────────────────
    @staticmethod
    def check_cooldown(phone: str, db: Session) -> bool:
        """Return True if the phone is still within the 60-second cooldown."""
        cutoff = datetime.utcnow() - timedelta(seconds=COOLDOWN_SECONDS)
        recent = (
            db.query(OTPRequest)
            .filter(OTPRequest.phone == phone, OTPRequest.created_at > cutoff)
            .first()
        )
        return recent is not None

    # ── Request lifecycle ─────────────────────────────────────────────────
    @staticmethod
    def create_otp_request(phone: str, db: Session) -> tuple["OTPRequest", str]:
        """Create a new OTP record. Returns (record, plain_otp)."""
        otp = OTPService.generate_otp()
        record = OTPRequest(
            phone=phone,
            otp_hash=OTPService.hash_otp(otp),
            expires_at=datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record, otp

    @staticmethod
    def verify_and_consume(phone: str, otp: str, db: Session) -> bool:
        """
        Verify the most recent un-verified, unexpired OTP for the phone.
        Increments attempt counter.  Returns True on success.
        """
        record = (
            db.query(OTPRequest)
            .filter(
                OTPRequest.phone == phone,
                OTPRequest.verified == False,  # noqa: E712
                OTPRequest.expires_at > datetime.utcnow(),
            )
            .order_by(OTPRequest.created_at.desc())
            .first()
        )
        if not record:
            return False

        record.attempts += 1

        if record.attempts > MAX_ATTEMPTS:
            db.commit()
            return False

        if not OTPService._verify_hash(otp, record.otp_hash):
            db.commit()
            return False

        record.verified = True
        db.commit()
        return True

    # ── SMS delivery ──────────────────────────────────────────────────────
    @staticmethod
    async def send_otp_sms(phone: str, otp: str) -> bool:
        """
        Send OTP via Notify.lk.
        Falls back to console logging when NOTIFY_LK_API_KEY is not set (dev mode).
        """
        message = (
            f"Your DrapeStudio verification code is: {otp}. "
            f"Valid for {OTP_EXPIRY_MINUTES} minutes. Do not share this code."
        )

        if not settings.NOTIFY_LK_API_KEY:
            # Development / test mode — log instead of sending
            logger.info("[DEV OTP] phone=%s otp=%s", phone, otp)
            print(f"\n{'='*50}\n[DEV OTP] phone={phone} otp={otp}\n{'='*50}\n", flush=True)
            return True

        url = "https://app.notify.lk/api/v1/send"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    data={
                        "user_id": settings.NOTIFY_LK_USER_ID,
                        "api_key": settings.NOTIFY_LK_API_KEY,
                        "sender_id": settings.NOTIFY_LK_SENDER_ID,
                        "to": phone,
                        "message": message,
                    },
                )
                data = resp.json()
                if data.get("status") == "success":
                    return True
                logger.warning("Notify.lk error response: %s", data)
                return False
        except Exception as exc:
            logger.error("Failed to send OTP SMS: %s", exc)
            return False
