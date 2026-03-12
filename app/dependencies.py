"""Shared FastAPI dependencies."""

import hashlib
import uuid

from fastapi import HTTPException, Request, Response


# ---------------------------------------------------------------------------
# Hardcoded users (password stored as SHA-256 hex digest)
# Legacy auth — kept for backward compatibility during JWT migration.
# Admin/test accounts bypass phone-OTP for easier development.
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
    """
    Return a user dict if the request is authenticated, else None.

    Priority:
    1. JWT access_token cookie  → {"user_id", "phone", "role", "username", "auth_type": "jwt"}
    2. Admin JWT admin_token cookie → {"user_id", "email", "role": "admin", "auth_type": "admin_jwt"}
    3. Legacy username/role cookies → {"username", "role", "auth_type": "legacy"}
    """
    # 1. JWT (user access token)
    access_token = request.cookies.get("access_token")
    if access_token:
        try:
            from app.services.auth import AuthService
            payload = AuthService.verify_access_token(access_token)
            if payload:
                email = payload.get("email", "")
                phone = payload.get("phone", "")
                return {
                    "user_id": payload["sub"],
                    "phone": phone,
                    "email": email,
                    "username": email or phone or "",  # compat alias
                    "role": payload.get("role", "user"),
                    "auth_type": "jwt",
                }
        except Exception:
            pass

    # 2. Admin JWT (admin_token cookie from /admin/login)
    admin_token = request.cookies.get("admin_token")
    if admin_token:
        try:
            from app.services.admin_auth import AdminAuthService
            payload = AdminAuthService.verify_admin_token(admin_token)
            if payload:
                return {
                    "user_id": payload["sub"],
                    "email": payload.get("email", ""),
                    "username": payload.get("email", ""),
                    "role": "admin",
                    "auth_type": "admin_jwt",
                }
        except Exception:
            pass

    # 3. Legacy cookie fallback
    username = request.cookies.get("username")
    role = request.cookies.get("role")
    if username and role and username in USERS:
        return {"username": username, "role": role, "auth_type": "legacy"}

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
