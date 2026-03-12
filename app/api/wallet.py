"""Wallet API endpoints — balance check, transaction history, and topup."""

import hashlib
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.config.wallet_pricing import PACKAGES
from app.database import get_db
from app.middleware.auth import get_request_user
from app.models.db import User, Wallet, WalletTransaction, generate_ulid
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


# ---------------------------------------------------------------------------
# POST /api/v1/wallet/topup/{package_key}
# ---------------------------------------------------------------------------
@router.post("/wallet/topup/{package_key}")
async def initiate_topup(package_key: str, request: Request, db: Session = Depends(get_db)):
    """Initiate a wallet topup via PayHere. Returns checkout form data."""
    user = _require_jwt_user(request)
    user_id = user["user_id"]

    package = PACKAGES.get(package_key)
    if not package:
        raise HTTPException(status_code=400, detail=f"Unknown package: {package_key!r}")

    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Generate PayHere checkout form data
    order_id = generate_ulid()
    amount = float(package["price_lkr"])

    checkout_url = (
        "https://sandbox.payhere.lk/pay/checkout"
        if settings.PAYHERE_SANDBOX
        else "https://www.payhere.lk/pay/checkout"
    )

    # PayHere hash: MD5(merchant_id + order_id + amount + currency + merchant_secret).upper()
    hash_str = (
        f"{settings.PAYHERE_MERCHANT_ID}"
        f"{order_id}"
        f"{amount:.2f}"
        "LKR"
        f"{settings.PAYHERE_MERCHANT_SECRET}"
    )
    hash_value = hashlib.md5(hash_str.encode()).hexdigest().upper()

    # Get user display fields
    phone = getattr(db_user, "phone", "") or ""
    name = getattr(db_user, "display_name", "") or ""
    first_name = name.split()[0] if name else "User"
    last_name = " ".join(name.split()[1:]) if len(name.split()) > 1 else ""
    email = getattr(db_user, "email", "") or ""

    # Get package name (use English fallback)
    pkg_name = package["name"]
    if isinstance(pkg_name, dict):
        pkg_name = pkg_name.get("en", package_key)

    form_data = {
        "merchant_id": settings.PAYHERE_MERCHANT_ID,
        "return_url": f"{settings.BASE_URL}/pricing?topup=success",
        "cancel_url": f"{settings.BASE_URL}/pricing?topup=cancelled",
        "notify_url": f"{settings.BASE_URL}/api/v1/wallet/payhere-notify",
        "order_id": order_id,
        "items": f"DrapeStudio {pkg_name}",
        "currency": "LKR",
        "amount": f"{amount:.2f}",
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "address": "",
        "city": "Colombo",
        "country": "Sri Lanka",
        "hash": hash_value,
        "custom_1": user_id,
        "custom_2": package_key,
        # Meta keys (stripped by frontend before form submit)
        "_checkout_url": checkout_url,
        "_package_key": package_key,
    }

    # For subscription packages, add recurrence fields
    if package.get("type") == "subscription":
        form_data["recurrence"] = "1 Month"
        form_data["duration"] = "Forever"

    logger.info(
        "Wallet topup initiated: user=%s package=%s order=%s amount=%.2f",
        user_id, package_key, order_id, amount,
    )

    return JSONResponse(content=form_data)


# ---------------------------------------------------------------------------
# POST /api/v1/wallet/payhere-notify  (server-to-server callback)
# ---------------------------------------------------------------------------
@router.post("/wallet/payhere-notify")
async def wallet_payhere_notify(request: Request, db: Session = Depends(get_db)):
    """
    PayHere server-to-server payment notification for wallet topups.
    Verifies the signature and credits the user's wallet on success.
    """
    form = await request.form()
    params = dict(form)

    # Verify signature
    merchant_id = params.get("merchant_id", "")
    order_id = params.get("order_id", "")
    amount = params.get("payhere_amount", "")
    currency = params.get("payhere_currency", "")
    status_code_str = params.get("status_code", "0")
    md5sig = params.get("md5sig", "")

    if md5sig:
        secret_hash = hashlib.md5(
            settings.PAYHERE_MERCHANT_SECRET.encode()
        ).hexdigest().upper()
        local_md5 = hashlib.md5(
            f"{merchant_id}{order_id}{amount}{currency}{status_code_str}{secret_hash}".encode()
        ).hexdigest().upper()
        if local_md5 != md5sig.upper():
            logger.warning("Wallet PayHere notification signature mismatch: %s", params)
            raise HTTPException(status_code=400, detail="Invalid signature.")

    status_code = int(status_code_str)
    user_id = params.get("custom_1", "")
    package_key = params.get("custom_2", "")
    payhere_payment_id = params.get("payment_id", "")

    logger.info(
        "Wallet PayHere notify: order=%s status=%d user=%s package=%s",
        order_id, status_code, user_id, package_key,
    )

    # Status 2 = payment success
    if status_code == 2 and user_id and package_key:
        try:
            topup = WalletService.process_topup(
                user_id=user_id,
                package_key=package_key,
                payhere_payment_id=payhere_payment_id,
                db=db,
            )
            logger.info(
                "Wallet topup completed: user=%s package=%s topup_id=%s",
                user_id, package_key, topup.id,
            )
        except ValueError as exc:
            logger.error("Wallet topup failed: %s", exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Wallet topup unexpected error: %s", exc)
            db.rollback()
            raise HTTPException(status_code=500, detail="Topup processing failed.") from exc
    else:
        logger.info(
            "Wallet PayHere notify: non-success status %d for order %s",
            status_code, order_id,
        )

    return JSONResponse(content={"status": "ok"})
