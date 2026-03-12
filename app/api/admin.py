"""Admin endpoints — usage reports, CSV export, and wallet management."""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models.db import (
    GenerationRequest,
    UsageCost,
    User,
    Wallet,
    WalletTransaction,
)
from app.services.wallet import WalletService

router = APIRouter(tags=["admin"])


@router.get("/admin/reports/usage")
def usage_report(
    request: Request,
    from_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    status: str | None = Query(None, description="Filter by status"),
    format: str = Query("json", description="Output format: json or csv"),
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Return usage/cost report with optional filters. Supports JSON and CSV."""

    # Build query joining GenerationRequest and UsageCost
    query = (
        db.query(GenerationRequest, UsageCost)
        .outerjoin(
            UsageCost,
            UsageCost.generation_request_id == GenerationRequest.id,
        )
    )

    # Apply filters
    if from_date:
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            query = query.filter(GenerationRequest.created_at >= from_dt)
        except ValueError:
            pass

    if to_date:
        try:
            to_dt = datetime.strptime(to_date, "%Y-%m-%d")
            # Include the entire to_date day
            to_dt = to_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(GenerationRequest.created_at <= to_dt)
        except ValueError:
            pass

    if status:
        query = query.filter(GenerationRequest.status == status)

    # Order by most recent first
    query = query.order_by(GenerationRequest.created_at.desc())

    results = query.all()

    # Build rows
    rows = []
    for gen, usage in results:
        row = {
            "id": gen.id,
            "session_id": gen.session_id,
            "status": gen.status,
            "output_count": gen.output_count,
            "prompt_template_version": gen.prompt_template_version,
            "model_name": usage.model_name if usage else None,
            "input_tokens": usage.input_tokens if usage else None,
            "output_tokens": usage.output_tokens if usage else None,
            "estimated_cost_usd": (
                float(usage.estimated_cost_usd)
                if usage and usage.estimated_cost_usd is not None
                else None
            ),
            "duration_ms": usage.duration_ms if usage else None,
            "error_message": gen.error_message,
            "created_at": gen.created_at.isoformat() if gen.created_at else None,
            "updated_at": gen.updated_at.isoformat() if gen.updated_at else None,
        }
        rows.append(row)

    # Return as CSV if requested
    if format == "csv":
        if not rows:
            csv_content = "No data"
        else:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
            csv_content = output.getvalue()

        return StreamingResponse(
            io.BytesIO(csv_content.encode("utf-8")),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=usage_report.csv"
            },
        )

    # Default: JSON
    return JSONResponse(content=rows)


# ── Wallet Management ──────────────────────────────────────────────────────


class AdminGrantBody(BaseModel):
    user_id: str
    amount_lkr: int
    reason: str


@router.get("/admin/wallet/users")
def wallet_users(
    request: Request,
    search: str | None = Query(None, description="Filter by name or phone"),
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all users with wallet balances for admin user management."""
    query = (
        db.query(User, Wallet)
        .outerjoin(Wallet, Wallet.user_id == User.id)
    )

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.display_name.ilike(pattern),
                User.phone.ilike(pattern),
            )
        )

    query = query.order_by(User.created_at.desc())
    results = query.all()

    rows = []
    for user, wallet in results:
        rows.append({
            "user_id": user.id,
            "name": user.display_name,
            "phone": user.phone,
            "role": user.role,
            "balance_lkr": wallet.balance_lkr if wallet else 0,
            "total_loaded": wallet.total_loaded if wallet else 0,
            "total_spent": wallet.total_spent if wallet else 0,
            "trial_images_used": wallet.trial_images_used if wallet else 0,
            "is_premium": wallet.is_premium if wallet else False,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        })

    return JSONResponse(content=rows)


@router.post("/admin/wallet/grant")
def wallet_grant(
    body: AdminGrantBody,
    request: Request,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin grants wallet balance to a user."""
    # Verify the target user exists
    user = db.query(User).filter(User.id == body.user_id).first()
    if not user:
        return JSONResponse(
            status_code=404,
            content={"error": f"User {body.user_id} not found."},
        )

    admin_user_id = _admin.get("user_id", _admin.get("username", "admin"))
    tx = WalletService.admin_grant(
        user_id=body.user_id,
        amount_lkr=body.amount_lkr,
        admin_user_id=admin_user_id,
        db=db,
    )

    return JSONResponse(content={
        "ok": True,
        "transaction_id": tx.id,
        "amount_lkr": tx.amount_lkr,
        "balance_after": tx.balance_after,
        "reason": body.reason,
    })


@router.post("/admin/wallet/refund/{generation_id}")
def wallet_refund(
    generation_id: str,
    request: Request,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin refunds a failed generation back to the user's wallet."""
    # Find the generation request to get the user_id
    gen = db.query(GenerationRequest).filter(
        GenerationRequest.id == generation_id,
    ).first()
    if not gen:
        return JSONResponse(
            status_code=404,
            content={"error": f"Generation {generation_id} not found."},
        )
    if not gen.user_id:
        return JSONResponse(
            status_code=400,
            content={"error": "Generation has no associated user."},
        )

    tx = WalletService.refund(
        user_id=gen.user_id,
        generation_id=generation_id,
        db=db,
    )

    if not tx:
        return JSONResponse(
            status_code=404,
            content={"error": "No deduction found for this generation (nothing to refund)."},
        )

    return JSONResponse(content={
        "ok": True,
        "transaction_id": tx.id,
        "refund_amount_lkr": tx.amount_lkr,
        "balance_after": tx.balance_after,
    })


@router.get("/admin/wallet/stats")
def wallet_stats(
    request: Request,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Return aggregate wallet statistics."""
    total_users = db.query(func.count(User.id)).scalar() or 0

    wallet_agg = db.query(
        func.coalesce(func.sum(Wallet.total_loaded), 0),
        func.coalesce(func.sum(Wallet.total_spent), 0),
    ).first()
    total_loaded_lkr = int(wallet_agg[0]) if wallet_agg else 0
    total_spent_lkr = int(wallet_agg[1]) if wallet_agg else 0

    total_transactions = db.query(func.count(WalletTransaction.id)).scalar() or 0

    now = datetime.utcnow()
    active_trials = (
        db.query(func.count(Wallet.id))
        .filter(Wallet.trial_expires_at > now)
        .scalar()
    ) or 0

    premium_users = (
        db.query(func.count(Wallet.id))
        .filter(
            Wallet.is_premium.is_(True),
            Wallet.premium_expires_at > now,
        )
        .scalar()
    ) or 0

    return JSONResponse(content={
        "total_users": total_users,
        "total_loaded_lkr": total_loaded_lkr,
        "total_spent_lkr": total_spent_lkr,
        "total_transactions": total_transactions,
        "active_trials": active_trials,
        "premium_users": premium_users,
    })
