"""JWT-based authentication service."""

import logging
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models.db import User

logger = logging.getLogger(__name__)


class AuthService:
    """JWT creation, verification, and user management helpers."""

    ALGORITHM: str = "HS256"

    # ── Token creation ────────────────────────────────────────────────────
    @classmethod
    def create_access_token(cls, user_id: str, phone: str, role: str = "user") -> str:
        """Create a signed 24-hour JWT access token."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "phone": phone,
            "role": role,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=cls.ALGORITHM)

    @classmethod
    def create_refresh_token(cls, user_id: str) -> str:
        """Create a signed 30-day JWT refresh token."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=cls.ALGORITHM)

    # ── Token verification ────────────────────────────────────────────────
    @classmethod
    def verify_token(cls, token: str) -> dict | None:
        """
        Decode and verify a JWT.
        Returns the payload dict, or None if invalid / expired.
        """
        try:
            return jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[cls.ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            logger.debug("JWT expired")
            return None
        except jwt.InvalidTokenError as exc:
            logger.debug("JWT invalid: %s", exc)
            return None

    @classmethod
    def verify_access_token(cls, token: str) -> dict | None:
        """Verify token and assert it is an access token. Returns payload or None."""
        payload = cls.verify_token(token)
        if payload and payload.get("type") == "access":
            return payload
        return None

    @classmethod
    def verify_refresh_token(cls, token: str) -> dict | None:
        """Verify token and assert it is a refresh token. Returns payload or None."""
        payload = cls.verify_token(token)
        if payload and payload.get("type") == "refresh":
            return payload
        return None

    # ── User management ───────────────────────────────────────────────────
    @staticmethod
    def get_or_create_user(phone: str, db: Session) -> tuple[User, bool]:
        """
        Look up a user by phone, creating a new one if not found.
        Returns (user, is_new_user).
        """
        user = db.query(User).filter(User.phone == phone).first()
        if user:
            return user, False

        user = User(phone=phone, role="user", credits_remaining=3)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user, True

    @staticmethod
    def record_login(user: User, db: Session) -> None:
        """Update last_login_at timestamp."""
        user.last_login_at = datetime.utcnow()
        db.commit()

    @classmethod
    def get_user_from_access_token(cls, token: str, db: Session) -> User | None:
        """Convenience: resolve a User from an access-token string."""
        payload = cls.verify_access_token(token)
        if not payload:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == user_id).first()
