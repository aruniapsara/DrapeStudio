"""Google OAuth 2.0 authentication service.

Handles the Sign in with Google flow using authlib:
- Redirect to Google consent screen
- Exchange authorization code for tokens
- Extract user profile (email, name, picture, google_id)
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx
import jwt
from authlib.integrations.starlette_client import OAuth

from app.config import settings

logger = logging.getLogger(__name__)

# ── OAuth client setup ──────────────────────────────────────────────────────

oauth = OAuth()

if settings.GOOGLE_CLIENT_ID:
    oauth.register(
        name="google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


# ── State token helpers ─────────────────────────────────────────────────────

def create_state_token(next_url: str = "/") -> str:
    """Create a JWT-signed state token for OAuth (10-minute expiry)."""
    payload = {
        "next": next_url,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def verify_state_token(token: str) -> dict | None:
    """Verify and decode a state token. Returns payload or None."""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ── User profile from Google ────────────────────────────────────────────────

async def fetch_google_user_info(access_token: str) -> dict | None:
    """Fetch user profile from Google's userinfo endpoint."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code == 200:
                return resp.json()
            logger.error("Google userinfo failed: %s %s", resp.status_code, resp.text)
    except Exception as exc:
        logger.error("Google userinfo request error: %s", exc)
    return None


# ── Database user lookup/creation ───────────────────────────────────────────

def get_or_create_google_user(
    google_id: str,
    email: str,
    name: str | None,
    picture: str | None,
    db,
) -> tuple:
    """
    Find or create a user from Google OAuth profile.

    Lookup order:
    1. By google_id (returning user)
    2. By email (merge with phone-created account)
    3. Create new user

    Returns (User, is_new: bool).
    """
    from app.models.db import User

    # 1. Look up by google_id
    user = db.query(User).filter(User.google_id == google_id).first()
    if user:
        # Update profile data on every login
        if picture:
            user.avatar_url = picture
        if name and not user.display_name:
            user.display_name = name
        user.last_login_at = datetime.utcnow()
        db.commit()
        return user, False

    # 2. Look up by email (merge with existing phone-OTP account)
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.google_id = google_id
        if picture:
            user.avatar_url = picture
        if name and not user.display_name:
            user.display_name = name
        user.last_login_at = datetime.utcnow()
        db.commit()
        return user, False

    # 3. Create new user
    user = User(
        google_id=google_id,
        email=email,
        display_name=name or "",
        avatar_url=picture or "",
        role="user",
        credits_remaining=3,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, True
