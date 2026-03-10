"""Notification API endpoints — push subscription management + preferences."""

import logging

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.db import User
from app.services.push_notification import push_notification_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _require_jwt_user(request: Request) -> dict:
    """Return the JWT user dict or raise 401."""
    user = getattr(request.state, "user", None)
    if not user or user.get("auth_type") != "jwt":
        raise HTTPException(status_code=401, detail="JWT authentication required")
    return user


# ── Push subscription ─────────────────────────────────────────────────────────

class PushSubscribeBody(BaseModel):
    endpoint: str
    keys: dict  # {p256dh, auth}


class PushUnsubscribeBody(BaseModel):
    endpoint: str


from fastapi import Depends


@router.post("/subscribe", status_code=201)
async def subscribe_push(body: PushSubscribeBody, request: Request, db: Session = Depends(_get_db)):
    """Save a Web Push subscription for the current user."""
    user = _require_jwt_user(request)
    push_notification_service.save_subscription(
        user_id=user["user_id"],
        subscription={"endpoint": body.endpoint, "keys": body.keys},
        db=db,
    )
    # Mark push_notifications_enabled = True on the user
    db_user = db.query(User).filter_by(id=user["user_id"]).first()
    if db_user:
        db_user.push_notifications_enabled = True
        db.commit()
    return {"status": "subscribed"}


@router.delete("/subscribe")
async def unsubscribe_push(body: PushUnsubscribeBody, request: Request, db: Session = Depends(_get_db)):
    """Remove a specific push subscription (device unsubscribed)."""
    user = _require_jwt_user(request)
    push_notification_service.delete_subscription(
        user_id=user["user_id"], endpoint=body.endpoint, db=db
    )
    return {"status": "unsubscribed"}


# ── Notification preferences ──────────────────────────────────────────────────

class PrefsBody(BaseModel):
    sms_notifications_enabled: bool | None = None
    push_notifications_enabled: bool | None = None


@router.patch("/preferences")
async def update_notification_preferences(
    body: PrefsBody, request: Request, db: Session = Depends(_get_db)
):
    """Update the user's notification channel preferences."""
    user = _require_jwt_user(request)
    db_user = db.query(User).filter_by(id=user["user_id"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.sms_notifications_enabled is not None:
        db_user.sms_notifications_enabled = body.sms_notifications_enabled
    if body.push_notifications_enabled is not None:
        db_user.push_notifications_enabled = body.push_notifications_enabled

    db.commit()
    return {
        "sms_notifications_enabled": db_user.sms_notifications_enabled,
        "push_notifications_enabled": db_user.push_notifications_enabled,
    }


@router.get("/preferences")
async def get_notification_preferences(request: Request, db: Session = Depends(_get_db)):
    """Get the user's current notification preferences."""
    user = _require_jwt_user(request)
    db_user = db.query(User).filter_by(id=user["user_id"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "sms_notifications_enabled": db_user.sms_notifications_enabled,
        "push_notifications_enabled": db_user.push_notifications_enabled,
    }
