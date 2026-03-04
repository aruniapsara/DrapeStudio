"""Phone OTP + JWT authentication API endpoints.

POST /api/v1/auth/request-otp  — send OTP to phone
POST /api/v1/auth/verify-otp   — verify OTP, issue JWT tokens
POST /api/v1/auth/refresh       — refresh access token
POST /api/v1/auth/logout        — clear JWT cookies
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services.auth import AuthService
from app.services.otp import OTPService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_COOKIE_OPTS: dict = {
    "httponly": True,
    "samesite": "lax",
    "secure": False,   # set True in production via settings if needed
}


# ── Request / Response schemas ────────────────────────────────────────────────

class RequestOTPBody(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not OTPService.validate_phone(v):
            raise ValueError("Phone must be in +94XXXXXXXXX format (Sri Lanka).")
        return v


class VerifyOTPBody(BaseModel):
    phone: str
    otp: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not OTPService.validate_phone(v):
            raise ValueError("Phone must be in +94XXXXXXXXX format (Sri Lanka).")
        return v

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() or len(v) != 6:
            raise ValueError("OTP must be a 6-digit number.")
        return v


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/request-otp")
async def request_otp(body: RequestOTPBody, db: Session = Depends(get_db)):
    """
    Send a 6-digit OTP to the given Sri Lankan phone number.
    Rate-limited: one request per 60 seconds per phone.
    """
    phone = body.phone

    if OTPService.check_cooldown(phone, db):
        raise HTTPException(
            status_code=429,
            detail="Please wait 60 seconds before requesting another OTP.",
        )

    _, otp = OTPService.create_otp_request(phone, db)

    sms_sent = await OTPService.send_otp_sms(phone, otp)
    if not sms_sent:
        logger.error("Failed to send OTP SMS to %s", phone)
        # We still return success to the client (don't reveal delivery failure)
        # In dev mode the OTP is logged, so this is fine.

    return {"message": "OTP sent successfully.", "expires_in_seconds": 300}


@router.post("/verify-otp")
async def verify_otp(
    body: VerifyOTPBody,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Verify OTP and issue JWT access + refresh tokens as httponly cookies.
    Creates a new user account on first verification.
    """
    success = OTPService.verify_and_consume(body.phone, body.otp, db)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OTP. Please try again.",
        )

    user, is_new = AuthService.get_or_create_user(body.phone, db)
    AuthService.record_login(user, db)

    access_token = AuthService.create_access_token(user.id, user.phone, user.role)
    refresh_token = AuthService.create_refresh_token(user.id)

    response.set_cookie(
        "access_token",
        access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **_COOKIE_OPTS,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        **_COOKIE_OPTS,
    )

    return {
        "is_new_user": is_new,
        "user_id": user.id,
        "display_name": user.display_name,
    }


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Exchange a valid refresh token cookie for a new access token.
    """
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token provided.")

    payload = AuthService.verify_refresh_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")

    from app.models.db import User
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")

    access_token = AuthService.create_access_token(user.id, user.phone, user.role)
    response.set_cookie(
        "access_token",
        access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **_COOKIE_OPTS,
    )
    return {"message": "Token refreshed."}


@router.post("/logout")
async def logout(response: Response):
    """Clear JWT cookies and end the session."""
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully."}


# ── Profile endpoints ─────────────────────────────────────────────────────────

class UpdateProfileBody(BaseModel):
    display_name: str | None = None


@router.get("/me")
async def get_me(request: Request, db: Session = Depends(get_db)):
    """Return profile data for the currently logged-in JWT user."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    user = AuthService.get_user_from_access_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")

    # Count total generation requests
    from app.models.db import GenerationRequest
    total_gens = (
        db.query(GenerationRequest)
        .filter(GenerationRequest.user_id == user.id)
        .count()
    )

    return {
        "user_id": user.id,
        "phone": user.phone,
        "display_name": user.display_name,
        "role": user.role,
        "credits_remaining": user.credits_remaining,
        "total_generations": total_gens,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


@router.patch("/me")
async def update_me(
    body: UpdateProfileBody,
    request: Request,
    db: Session = Depends(get_db),
):
    """Update display_name for the currently logged-in JWT user."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    user = AuthService.get_user_from_access_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")

    if body.display_name is not None:
        user.display_name = body.display_name.strip()[:100]
        db.commit()

    return {"display_name": user.display_name}
