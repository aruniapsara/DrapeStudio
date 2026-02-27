"""Shared FastAPI dependencies."""

import uuid

from fastapi import Request, Response


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
