"""Admin authentication middleware — separate from user auth.

Only applies to /admin/* routes. Uses the `admin_token` cookie
(separate from the user `access_token` cookie) so admin and user
sessions don't conflict.
"""

from __future__ import annotations

from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


# Admin paths that don't require authentication
_ADMIN_PUBLIC = {
    "/admin/login",
}


def get_admin_user(request: Request) -> dict | None:
    """Extract admin user info from admin_token cookie."""
    from app.services.admin_auth import AdminAuthService

    admin_token = request.cookies.get("admin_token")
    if not admin_token:
        return None

    payload = AdminAuthService.verify_admin_token(admin_token)
    if not payload:
        return None

    return {
        "user_id": payload["sub"],
        "email": payload.get("email", ""),
        "role": "admin",
        "auth_type": "admin_jwt",
    }


class AdminAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that protects /admin/* routes with admin JWT auth.

    - /admin/login is public (login page)
    - All other /admin/* routes require a valid admin_token cookie
    - Unauthenticated requests redirect to /admin/login
    - Static files and non-admin routes pass through unchanged
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Only apply to /admin/* routes
        if not path.startswith("/admin"):
            return await call_next(request)

        # Allow public admin paths
        if path in _ADMIN_PUBLIC:
            return await call_next(request)

        # Allow POST to /admin/login (form submission)
        if path == "/admin/login" and request.method == "POST":
            return await call_next(request)

        # Check admin authentication
        admin_user = get_admin_user(request)
        if not admin_user:
            # API requests get 401
            if path.startswith("/admin/api/"):
                return JSONResponse(
                    {"detail": "Admin authentication required"},
                    status_code=401,
                )
            # Page requests redirect to login
            return RedirectResponse(url="/admin/login", status_code=302)

        # Store admin user info on request state for downstream use
        request.state.admin_user = admin_user

        return await call_next(request)
