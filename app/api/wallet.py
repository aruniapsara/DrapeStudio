"""Wallet API endpoints — balance check and transaction history."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_request_user
from app.models.db import User, Wallet, WalletTransaction
from app.services.wallet import WalletService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["wallet"])


def _require_jwt_user(request: Request) -> dict:
    """Return user dict for JWT-authenticated users only."""
    user = get_request_user(request)
    if not user or user.get("auth_type") != "jwt":
        raise HTTPException(status_code=401, detail="Login required.")
    return user


# ---------------------------------------------------------------------------
# GET /api/v1/wallet/balance
# ---------------------------------------------------------------------------
@router.get("/wallet/balance")
async def get_wallet_balance(request: Request, db: Session = Depends(get_db)):
    """Return current wallet balance and trial info for the authenticated user."""
    user = _require_jwt_user(request)
    user_id = user["user_id"]

    wallet = WalletService.get_or_create_wallet(user_id, db)
    db.commit()  # persist wallet if newly created

    now = datetime.utcnow()

    # Calculate trial remaining
    from app.config.wallet_pricing import TRIAL

    trial_remaining = 0
    trial_fiton_remaining = 0
    trial_expires_at = None

    if wallet.trial_expires_at and wallet.trial_expires_at > now:
        trial_remaining = max(0, TRIAL["free_images"] - wallet.trial_images_used)
        trial_fiton_remaining = max(0, TRIAL.get("fiton_images", 1) - wallet.trial_fiton_used)
        trial_expires_at = wallet.trial_expires_at.isoformat()

    return JSONResponse(content={
        "balance_lkr": wallet.balance_lkr,
        "trial_remaining": trial_remaining,
        "trial_fiton_remaining": trial_fiton_remaining,
        "trial_expires_at": trial_expires_at,
        "is_premium": wallet.is_premium,
        "premium_balance_lkr": wallet.premium_balance_lkr,
    })


# ---------------------------------------------------------------------------
# GET /api/v1/wallet/transactions
# ---------------------------------------------------------------------------
@router.get("/wallet/transactions")
async def get_wallet_transactions(request: Request, db: Session = Depends(get_db)):
    """Return the last 50 wallet transactions for the authenticated user."""
    user = _require_jwt_user(request)
    user_id = user["user_id"]

    transactions = (
        db.query(WalletTransaction)
        .filter(WalletTransaction.user_id == user_id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(50)
        .all()
    )

    result = [
        {
            "id": tx.id,
            "amount_lkr": tx.amount_lkr,
            "balance_after": tx.balance_after,
            "transaction_type": tx.transaction_type,
            "description": tx.description,
            "created_at": tx.created_at.isoformat() if tx.created_at else None,
        }
        for tx in transactions
    ]

    return JSONResponse(content=result)
