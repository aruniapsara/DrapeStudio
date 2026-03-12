"""Admin dashboard API routes — dashboard stats, user management, sponsorship."""

import json
import logging
from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, case, and_, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db import (
    AdminAuditLog,
    GenerationRequest,
    User,
    Wallet,
    WalletTopup,
    WalletTransaction,
    generate_ulid,
)
from app.services.wallet import WalletService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/api", tags=["admin-dashboard"])


def _require_admin(request: Request) -> dict:
    """Extract admin user from request state (set by AdminAuthMiddleware)."""
    admin = getattr(request.state, "admin_user", None)
    if not admin:
        raise Exception("Not authenticated")
    return admin


def _audit_log(admin_user_id: str, action: str, target_user_id: str | None, details: dict, db: Session):
    """Write an entry to the admin audit log."""
    log = AdminAuditLog(
        admin_user_id=admin_user_id,
        action=action,
        target_user_id=target_user_id,
        details=json.dumps(details) if details else None,
    )
    db.add(log)
    db.flush()


# ── Dashboard Stats ───────────────────────────────────────────────────────────

@router.get("/dashboard/stats")
def dashboard_stats(request: Request, db: Session = Depends(get_db)):
    """Return aggregate stats for the admin dashboard."""
    try:
        admin = _require_admin(request)
    except Exception:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)
    seven_days_ago = now - timedelta(days=7)

    total_users = db.query(func.count(User.id)).scalar() or 0
    users_today = db.query(func.count(User.id)).filter(User.created_at >= today_start).scalar() or 0
    users_this_week = db.query(func.count(User.id)).filter(User.created_at >= week_start).scalar() or 0
    users_this_month = db.query(func.count(User.id)).filter(User.created_at >= month_start).scalar() or 0
    active_users_7d = db.query(func.count(User.id)).filter(User.last_login_at >= seven_days_ago).scalar() or 0

    gens_today = db.query(func.count(GenerationRequest.id)).filter(GenerationRequest.created_at >= today_start).scalar() or 0
    gens_this_week = db.query(func.count(GenerationRequest.id)).filter(GenerationRequest.created_at >= week_start).scalar() or 0
    gens_all_time = db.query(func.count(GenerationRequest.id)).scalar() or 0

    # Revenue = sum of wallet top-ups this month
    revenue_this_month = (
        db.query(func.coalesce(func.sum(WalletTopup.amount_paid_lkr), 0))
        .filter(WalletTopup.created_at >= month_start, WalletTopup.status == "completed")
        .scalar()
    ) or 0

    # Trial and premium counts
    active_trials = db.query(func.count(Wallet.id)).filter(Wallet.trial_expires_at > now).scalar() or 0
    premium_users = db.query(func.count(Wallet.id)).filter(Wallet.is_premium.is_(True), Wallet.premium_expires_at > now).scalar() or 0

    return JSONResponse({
        "total_users": total_users,
        "users_today": users_today,
        "users_this_week": users_this_week,
        "users_this_month": users_this_month,
        "active_users_7d": active_users_7d,
        "generations_today": gens_today,
        "generations_this_week": gens_this_week,
        "generations_all_time": gens_all_time,
        "revenue_this_month_lkr": int(revenue_this_month),
        "active_trials": active_trials,
        "premium_users": premium_users,
    })


@router.get("/dashboard/charts")
def dashboard_charts(request: Request, db: Session = Depends(get_db)):
    """Return chart data for signups and generations over 30 days."""
    try:
        admin = _require_admin(request)
    except Exception:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    today = date.today()
    days_30 = [today - timedelta(days=i) for i in range(29, -1, -1)]

    # Signups per day
    signups_raw = (
        db.query(
            func.date(User.created_at).label("d"),
            func.count(User.id).label("c"),
        )
        .filter(User.created_at >= datetime.combine(days_30[0], datetime.min.time()))
        .group_by(func.date(User.created_at))
        .all()
    )
    signups_map = {str(row.d): row.c for row in signups_raw}
    signups_30d = [{"date": d.strftime("%b %d"), "count": signups_map.get(str(d), 0)} for d in days_30]

    # Generations per day
    gens_raw = (
        db.query(
            func.date(GenerationRequest.created_at).label("d"),
            func.count(GenerationRequest.id).label("c"),
        )
        .filter(GenerationRequest.created_at >= datetime.combine(days_30[0], datetime.min.time()))
        .group_by(func.date(GenerationRequest.created_at))
        .all()
    )
    gens_map = {str(row.d): row.c for row in gens_raw}
    generations_30d = [{"date": d.strftime("%b %d"), "count": gens_map.get(str(d), 0)} for d in days_30]

    return JSONResponse({
        "signups_30d": signups_30d,
        "generations_30d": generations_30d,
    })


# ── User List ─────────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(
    request: Request,
    search: str = Query("", description="Search by name or email"),
    role: str = Query("", description="Filter by role"),
    sponsored: str = Query("", description="Filter by sponsored status"),
    sort: str = Query("created_at", description="Sort field"),
    dir: str = Query("desc", description="Sort direction"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List users with search, filters, sorting, and pagination."""
    try:
        admin = _require_admin(request)
    except Exception:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    query = db.query(User)

    # Search
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.display_name.ilike(pattern),
                User.email.ilike(pattern),
            )
        )

    # Role filter
    if role:
        query = query.filter(User.role == role)

    # Sponsored filter
    if sponsored == "yes":
        query = query.filter(User.is_sponsored.is_(True))
    elif sponsored == "no":
        query = query.filter(User.is_sponsored.is_(False))

    # Total count before pagination
    total = query.count()

    # Sorting
    sort_col = {
        "created_at": User.created_at,
        "display_name": User.display_name,
        "last_login_at": User.last_login_at,
    }.get(sort, User.created_at)

    if dir == "asc":
        query = query.order_by(sort_col.asc().nullslast())
    else:
        query = query.order_by(sort_col.desc().nullslast())

    # Pagination
    offset = (page - 1) * page_size
    users = query.offset(offset).limit(page_size).all()

    # Build response with wallet info
    user_ids = [u.id for u in users]
    wallets = {w.user_id: w for w in db.query(Wallet).filter(Wallet.user_id.in_(user_ids)).all()} if user_ids else {}

    # Generation counts
    gen_counts = {}
    if user_ids:
        counts = (
            db.query(GenerationRequest.user_id, func.count(GenerationRequest.id))
            .filter(GenerationRequest.user_id.in_(user_ids))
            .group_by(GenerationRequest.user_id)
            .all()
        )
        gen_counts = {uid: cnt for uid, cnt in counts}

    rows = []
    for u in users:
        w = wallets.get(u.id)
        rows.append({
            "id": u.id,
            "display_name": u.display_name,
            "email": u.email,
            "phone": u.phone,
            "avatar_url": u.avatar_url,
            "role": u.role,
            "is_sponsored": u.is_sponsored,
            "sponsored_by": u.sponsored_by,
            "wallet_balance": w.balance_lkr if w else 0,
            "total_generations": gen_counts.get(u.id, 0),
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })

    return JSONResponse({"users": rows, "total": total})


# ── User Detail ───────────────────────────────────────────────────────────────

@router.get("/users/{user_id}")
def get_user_detail(user_id: str, request: Request, db: Session = Depends(get_db)):
    """Get full user details for admin user detail page."""
    try:
        admin = _require_admin(request)
    except Exception:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse({"error": "User not found"}, status_code=404)

    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()

    # Recent transactions
    transactions = (
        db.query(WalletTransaction)
        .filter(WalletTransaction.user_id == user_id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(20)
        .all()
    )

    # Recent generations
    generations = (
        db.query(GenerationRequest)
        .filter(GenerationRequest.user_id == user_id)
        .order_by(GenerationRequest.created_at.desc())
        .limit(20)
        .all()
    )

    total_gens = db.query(func.count(GenerationRequest.id)).filter(GenerationRequest.user_id == user_id).scalar() or 0

    return JSONResponse({
        "user": {
            "id": user.id,
            "display_name": user.display_name,
            "email": user.email,
            "phone": user.phone,
            "avatar_url": user.avatar_url,
            "role": user.role,
            "language_preference": user.language_preference,
            "is_sponsored": user.is_sponsored,
            "sponsored_by": user.sponsored_by,
            "sponsored_until": str(user.sponsored_until) if user.sponsored_until else None,
            "admin_notes": user.admin_notes,
            "balance_lkr": wallet.balance_lkr if wallet else 0,
            "total_loaded": wallet.total_loaded if wallet else 0,
            "total_spent": wallet.total_spent if wallet else 0,
            "trial_images_used": wallet.trial_images_used if wallet else 0,
            "is_premium": wallet.is_premium if wallet else False,
            "total_generations": total_gens,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "is_active": True,  # We don't have a status field yet; all users are active
        },
        "transactions": [
            {
                "id": tx.id,
                "amount_lkr": tx.amount_lkr,
                "balance_after": tx.balance_after,
                "transaction_type": tx.transaction_type,
                "description": tx.description,
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
            }
            for tx in transactions
        ],
        "generations": [
            {
                "id": gen.id,
                "module": gen.module,
                "status": gen.status,
                "output_count": gen.output_count,
                "error_message": gen.error_message,
                "created_at": gen.created_at.isoformat() if gen.created_at else None,
            }
            for gen in generations
        ],
    })


# ── User Actions ──────────────────────────────────────────────────────────────

class SponsorBody(BaseModel):
    is_sponsored: bool
    sponsored_by: str = ""
    sponsored_until: str | None = None


class GrantCreditsBody(BaseModel):
    amount_lkr: int
    reason: str


class NotesBody(BaseModel):
    notes: str


class RoleBody(BaseModel):
    role: str


@router.post("/users/{user_id}/sponsor")
def toggle_sponsor(user_id: str, body: SponsorBody, request: Request, db: Session = Depends(get_db)):
    """Toggle sponsored account status."""
    try:
        admin = _require_admin(request)
    except Exception:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse({"error": "User not found"}, status_code=404)

    user.is_sponsored = body.is_sponsored
    user.sponsored_by = body.sponsored_by if body.is_sponsored else None
    if body.is_sponsored and body.sponsored_until:
        try:
            user.sponsored_until = date.fromisoformat(body.sponsored_until)
        except ValueError:
            user.sponsored_until = None
    else:
        user.sponsored_until = None

    _audit_log(admin["user_id"], "toggle_sponsor", user_id, {
        "is_sponsored": body.is_sponsored,
        "sponsored_by": body.sponsored_by,
        "sponsored_until": body.sponsored_until,
    }, db)

    db.commit()
    return JSONResponse({"ok": True, "is_sponsored": user.is_sponsored})


@router.post("/users/{user_id}/grant-credits")
def grant_credits(user_id: str, body: GrantCreditsBody, request: Request, db: Session = Depends(get_db)):
    """Grant wallet credits to a user."""
    try:
        admin = _require_admin(request)
    except Exception:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse({"error": "User not found"}, status_code=404)

    tx = WalletService.admin_grant(
        user_id=user_id,
        amount_lkr=body.amount_lkr,
        admin_user_id=admin["user_id"],
        db=db,
    )

    _audit_log(admin["user_id"], "grant_credits", user_id, {
        "amount_lkr": body.amount_lkr,
        "reason": body.reason,
    }, db)
    db.commit()

    return JSONResponse({
        "ok": True,
        "transaction_id": tx.id,
        "amount_lkr": tx.amount_lkr,
        "balance_after": tx.balance_after,
    })


@router.post("/users/{user_id}/notes")
def update_notes(user_id: str, body: NotesBody, request: Request, db: Session = Depends(get_db)):
    """Update admin notes for a user."""
    try:
        admin = _require_admin(request)
    except Exception:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse({"error": "User not found"}, status_code=404)

    user.admin_notes = body.notes
    db.commit()
    return JSONResponse({"ok": True})


@router.post("/users/{user_id}/role")
def change_role(user_id: str, body: RoleBody, request: Request, db: Session = Depends(get_db)):
    """Change a user's role."""
    try:
        admin = _require_admin(request)
    except Exception:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    if body.role not in ("user", "admin", "tester"):
        return JSONResponse({"error": "Invalid role"}, status_code=400)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse({"error": "User not found"}, status_code=404)

    old_role = user.role
    user.role = body.role

    _audit_log(admin["user_id"], "change_role", user_id, {
        "old_role": old_role,
        "new_role": body.role,
    }, db)
    db.commit()

    return JSONResponse({"ok": True, "role": user.role})


@router.post("/users/{user_id}/toggle-status")
def toggle_status(user_id: str, request: Request, db: Session = Depends(get_db)):
    """Toggle user active/inactive status (deactivate/reactivate)."""
    try:
        admin = _require_admin(request)
    except Exception:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse({"error": "User not found"}, status_code=404)

    # We don't have a dedicated 'is_active' column yet.
    # Use role to deactivate: set role to 'inactive', or restore to 'user'.
    if user.role == "inactive":
        user.role = "user"
        new_status = "active"
    else:
        old_role = user.role
        user.role = "inactive"
        new_status = "inactive"
        _audit_log(admin["user_id"], "deactivate_user", user_id, {"old_role": old_role}, db)

    db.commit()
    return JSONResponse({"ok": True, "status": new_status, "role": user.role})


@router.delete("/users/{user_id}")
def delete_user(user_id: str, request: Request, db: Session = Depends(get_db)):
    """Delete a user account (soft delete by setting role to 'deleted')."""
    try:
        admin = _require_admin(request)
    except Exception:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse({"error": "User not found"}, status_code=404)

    # Don't allow deleting other admins
    if user.role == "admin" and user.id != admin["user_id"]:
        return JSONResponse({"error": "Cannot delete another admin"}, status_code=403)

    _audit_log(admin["user_id"], "delete_user", user_id, {
        "email": user.email,
        "display_name": user.display_name,
    }, db)

    # Soft delete — mark as deleted, clear sensitive data
    user.role = "deleted"
    user.display_name = "[Deleted]"
    user.phone = None
    user.google_id = None
    db.commit()

    return JSONResponse({"ok": True})
