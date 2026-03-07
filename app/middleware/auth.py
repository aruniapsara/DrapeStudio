"""JWT-aware authentication middleware for DrapeStudio.

Checks the `access_token` cookie (JWT) first.
Falls back to legacy username/role cookies for backward compatibility
(used by existing tests and in-flight sessions during migration).
"""

from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


# Paths that never require authentication
_PUBLIC_PREFIXES = (
    "/static/",
    "/api/v1/auth/",  # auth endpoints
    "/v1/files/",     # file serving
)
_PUBLIC_EXACT = {
    "/login",
    "/health",
    "/health/detailed",
    "/metrics",
    "/sitemap.xml",
    "/robots.txt",
    "/favicon.ico",
    "/offline.html",
}


def _is_public(path: str) -> bool:
    if path in _PUBLIC_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)


def _is_api_path(path: str) -> bool:
    return path.startswith("/v1/") or path.startswith("/api/")


def get_request_user(request: Request) -> dict | None:
    """
    Resolve the current user from the request.

    Priority:
    1. JWT `access_token` cookie
    2. Legacy `username` / `role` cookies (backward compatibility)

    Returns a dict with at minimum: {role, auth_type}.
    """
    from app.services.auth import AuthService
    from app.dependencies import USERS

    # 1. JWT
    access_token = request.cookies.get("access_token")
    if access_token:
        payload = AuthService.verify_access_token(access_token)
        if payload:
            return {
                "user_id": payload["sub"],
                "phone": payload.get("phone", ""),
                # username alias so templates work with either auth system
                "username": payload.get("phone", ""),
                "role": payload.get("role", "user"),
                "auth_type": "jwt",
            }

    # 2. Legacy username/role cookies (dev / test fallback)
    username = request.cookies.get("username")
    role = request.cookies.get("role")
    if username and role and username in USERS:
        return {
            "username": username,
            "role": role,
            "auth_type": "legacy",
        }

    return None


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    - Allows public paths through without auth.
    - Checks JWT / legacy cookies for protected paths.
    - Redirects unauthenticated page requests to /login.
    - Returns 401 JSON for unauthenticated API requests.
    - Attaches / refreshes the session_id cookie.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if not _is_public(path):
            user = get_request_user(request)
            if not user:
                if _is_api_path(path):
                    return JSONResponse(
                        {"detail": "Not authenticated"}, status_code=401
                    )
                return RedirectResponse(url="/login", status_code=302)

        response = await call_next(request)

        # Ensure every response carries a session_id cookie
        if not request.cookies.get("session_id"):
            response.set_cookie(
                "session_id",
                str(uuid.uuid4()),
                httponly=True,
                samesite="lax",
                max_age=86400 * 30,
            )

        return response
