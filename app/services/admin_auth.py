"""Admin authentication service — email + bcrypt password auth."""

import logging
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models.db import User

logger = logging.getLogger(__name__)

# Try to import bcrypt, fall back gracefully
try:
    import bcrypt
    _HAS_BCRYPT = True
except ImportError:
    import hashlib
    _HAS_BCRYPT = False
    logger.warning("bcrypt not installed — using SHA-256 fallback for admin passwords")


class AdminAuthService:
    """Admin-specific auth: email + bcrypt password, separate JWT."""

    ALGORITHM = "HS256"
    ADMIN_TOKEN_EXPIRE_HOURS = 8  # Admin sessions are shorter

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash a password with bcrypt."""
        if _HAS_BCRYPT:
            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        # Fallback to SHA-256 (dev only)
        return "sha256:" + hashlib.sha256(password.encode()).hexdigest()

    @classmethod
    def verify_password(cls, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        if password_hash.startswith("sha256:"):
            return password_hash == "sha256:" + hashlib.sha256(password.encode()).hexdigest()
        if _HAS_BCRYPT:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        return False

    @classmethod
    def create_admin_token(cls, user_id: str, email: str) -> str:
        """Create a signed JWT for admin sessions."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "email": email,
            "role": "admin",
            "type": "admin_access",
            "iat": now,
            "exp": now + timedelta(hours=cls.ADMIN_TOKEN_EXPIRE_HOURS),
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=cls.ALGORITHM)

    @classmethod
    def verify_admin_token(cls, token: str) -> dict | None:
        """Verify an admin JWT. Returns payload or None."""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[cls.ALGORITHM])
            if payload.get("type") == "admin_access" and payload.get("role") == "admin":
                return payload
            return None
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None

    @classmethod
    def authenticate_admin(cls, email: str, password: str, db: Session) -> User | None:
        """Authenticate an admin by email + password. Returns User or None."""
        user = db.query(User).filter(User.email == email, User.role == "admin").first()
        if not user:
            return None
        if not user.admin_password_hash:
            return None
        if not cls.verify_password(password, user.admin_password_hash):
            return None
        # Record login
        user.last_login_at = datetime.utcnow()
        db.commit()
        return user

    @classmethod
    def create_admin_user(cls, email: str, password: str, name: str, db: Session) -> User:
        """Create or promote a user to admin with a password hash."""
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.role = "admin"
            user.admin_password_hash = cls.hash_password(password)
            if name:
                user.display_name = name
        else:
            user = User(
                email=email,
                display_name=name or "Admin",
                role="admin",
                admin_password_hash=cls.hash_password(password),
            )
            db.add(user)
        db.commit()
        db.refresh(user)
        return user
