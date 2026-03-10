"""Billing API endpoints — usage, subscribe, PayHere notifications, history."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_request_user
from app.models.db import CreditTransaction, Payment, Subscription, User, generate_ulid
from app.services.billing import BillingService
from app.services.payhere import payhere_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


def _require_jwt_user(request: Request) -> dict:
    """Return user dict for JWT-authenticated users only."""
    user = get_request_user(request)
    if not user or user.get("auth_type") != "jwt":
        raise HTTPException(status_code=401, detail="Login required.")
    return user


# ---------------------------------------------------------------------------
# GET /api/v1/billing/usage
# ---------------------------------------------------------------------------
@router.get("/usage")
async def get_usage(request: Request, db: Session = Depends(get_db)):
    """Get current user's usage summary."""
    user = _require_jwt_user(request)
    user_id = user["user_id"]
    summary = BillingService.get_usage_summary(user_id, db)
    return JSONResponse(content=summary)


# ---------------------------------------------------------------------------
# POST /api/v1/billing/subscribe/{plan}
# ---------------------------------------------------------------------------
@router.post("/subscribe/{plan}")
async def subscribe(plan: str, request: Request, db: Session = Depends(get_db)):
    """Initiate subscription checkout via PayHere. Returns form data for redirect."""
    from app.config.plans import PLANS

    user_info = _require_jwt_user(request)
    if plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {plan!r}")
    if PLANS[plan]["price_lkr"] == 0:
        raise HTTPException(status_code=400, detail="Free plan does not require payment.")

    db_user = db.query(User).filter(User.id == user_info["user_id"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found.")

    checkout_data = payhere_service.create_checkout(db_user, plan)
    return JSONResponse(content=checkout_data)


# ---------------------------------------------------------------------------
# POST /api/v1/billing/payhere-notify  (server-to-server callback)
# ---------------------------------------------------------------------------
@router.post("/payhere-notify")
async def payhere_notify(request: Request, db: Session = Depends(get_db)):
    """
    PayHere server-to-server payment notification.
    PayHere sends a form-encoded POST with payment result.
    """
    form = await request.form()
    params = dict(form)

    # Verify signature
    if not payhere_service.verify_notification(params):
        logger.warning("PayHere notification signature mismatch: %s", params)
        raise HTTPException(status_code=400, detail="Invalid signature.")

    status_code = int(params.get("status_code", 0))
    order_id = params.get("order_id", "")
    amount_str = params.get("payhere_amount", "0")
    currency = params.get("payhere_currency", "LKR")
    payhere_payment_id = params.get("payment_id", "")
    merchant_id = params.get("merchant_id", "")
    # Custom fields passed via PayHere custom_* fields
    user_id = params.get("custom_1", "")
    plan_key = params.get("custom_2", "")

    logger.info(
        "PayHere notify: order=%s status=%s user=%s plan=%s",
        order_id, status_code, user_id, plan_key,
    )

    try:
        amount_lkr = float(amount_str)
    except ValueError:
        amount_lkr = 0.0

    # Map status_code: 2 = success, -1 = cancelled, -2 = failed, -3 = chargedback
    if status_code == 2:
        payment_status = "completed"
    elif status_code == -1:
        payment_status = "cancelled"
    elif status_code in (-2, -3):
        payment_status = "failed"
    else:
        payment_status = "pending"

    # Record payment
    payment = Payment(
        id=generate_ulid(),
        user_id=user_id,
        amount_lkr=amount_lkr,
        currency=currency,
        status=payment_status,
        payhere_payment_id=payhere_payment_id,
        description=f"{plan_key} plan via PayHere",
    )
    db.add(payment)

    if status_code == 2 and user_id and plan_key:
        try:
            sub = BillingService.create_subscription(
                user_id=user_id,
                plan_key=plan_key,
                payhere_subscription_id=payhere_payment_id,
                db=db,
            )
            payment.subscription_id = sub.id
            logger.info("Subscription created: %s for user %s", sub.id, user_id)
        except Exception as exc:
            logger.exception("Failed to create subscription: %s", exc)
            db.rollback()
            raise HTTPException(status_code=500, detail="Subscription creation failed.") from exc
    else:
        db.commit()

    return JSONResponse(content={"status": "ok"})


# ---------------------------------------------------------------------------
# POST /api/v1/billing/cancel
# ---------------------------------------------------------------------------
@router.post("/cancel")
async def cancel_subscription(request: Request, db: Session = Depends(get_db)):
    """Cancel current subscription (remains active until period end)."""
    user_info = _require_jwt_user(request)
    user_id = user_info["user_id"]

    sub = BillingService.get_active_subscription(user_id, db)
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription found.")

    sub.status = "cancelled"
    sub.cancelled_at = datetime.utcnow()
    db.commit()

    return JSONResponse(content={"status": "cancelled", "expires_at": sub.expires_at.isoformat() if sub.expires_at else None})


# ---------------------------------------------------------------------------
# GET /api/v1/billing/history
# ---------------------------------------------------------------------------
@router.get("/history")
async def billing_history(request: Request, db: Session = Depends(get_db)):
    """Get payment and credit transaction history."""
    user_info = _require_jwt_user(request)
    user_id = user_info["user_id"]

    payments = (
        db.query(Payment)
        .filter(Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
        .limit(50)
        .all()
    )
    transactions = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.user_id == user_id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(100)
        .all()
    )

    return JSONResponse(content={
        "payments": [
            {
                "id": p.id,
                "amount_lkr": p.amount_lkr,
                "currency": p.currency,
                "status": p.status,
                "description": p.description,
                "created_at": p.created_at.isoformat(),
            }
            for p in payments
        ],
        "transactions": [
            {
                "id": t.id,
                "amount": t.amount,
                "balance_after": t.balance_after,
                "transaction_type": t.transaction_type,
                "description": t.description,
                "created_at": t.created_at.isoformat(),
            }
            for t in transactions
        ],
    })
