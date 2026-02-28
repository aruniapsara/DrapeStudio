"""Shared FastAPI dependencies."""

import hashlib
import uuid

from fastapi import HTTPException, Request, Response


# ---------------------------------------------------------------------------
# Hardcoded users (password stored as SHA-256 hex digest)
# ---------------------------------------------------------------------------
def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


USERS = {
    "aruni": {"password_hash": _sha256("Fashion#2026"), "role": "admin"},
    "tester": {"password_hash": _sha256("Fa#shion$2026"), "role": "tester"},
}


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------
def get_or_create_session_id(request: Request, response: Response) -> str:
    """Get or create session_id from browser cookie."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(
            "session_id",
            session_id,
            httponly=True,
            samesite="lax",
            max_age=86400 * 30,
        )
    return session_id


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def get_current_user(request: Request) -> dict | None:
    """Return {"username": str, "role": str} if logged in, else None."""
    username = request.cookies.get("username")
    role = request.cookies.get("role")
    if username and role and username in USERS:
        return {"username": username, "role": role}
    return None


def require_admin(request: Request) -> dict:
    """Dependency that raises 403 if the user is not an admin."""
    user = get_current_user(request)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


def verify_credentials(username: str, password: str) -> dict | None:
    """Check username/password. Returns user dict or None."""
    user_record = USERS.get(username)
    if not user_record:
        return None
    if user_record["password_hash"] != _sha256(password):
        return None
    return {"username": username, "role": user_record["role"]}
