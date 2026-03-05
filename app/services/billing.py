"""Credit-based usage management and generation enforcement."""

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config.plans import PLANS
from app.models.db import CreditTransaction, GenerationRequest, Subscription, User

logger = logging.getLogger(__name__)

# Modules that cost 1 credit each
CREDIT_COST: dict[str, int] = {
    "adult": 1,
    "children": 1,
    "accessories": 1,
    "fiton": 1,
}


class BillingService:
    """Handles credit tracking, usage enforcement, and subscription management."""

    # ── Plan / subscription helpers ───────────────────────────────────────────

    @staticmethod
    def get_active_subscription(user_id: str, db: Session) -> Subscription | None:
        """Return the current active subscription for a user, or None (free tier)."""
        return (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.status == "active",
            )
            .first()
        )

    @staticmethod
    def get_user_plan(user_id: str, db: Session) -> tuple[str, Subscription | None]:
        """Return (plan_key, active_subscription_or_None)."""
        sub = BillingService.get_active_subscription(user_id, db)
        if sub:
            return sub.plan, sub
        return "free", None

    # ── Daily usage ───────────────────────────────────────────────────────────

    @staticmethod
    def get_daily_usage(user_id: str, module: str, db: Session) -> int:
        """Count generation credit deductions for the current UTC day."""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            db.query(CreditTransaction)
            .filter(
                CreditTransaction.user_id == user_id,
                CreditTransaction.transaction_type == "generation",
                CreditTransaction.amount < 0,
                CreditTransaction.created_at >= today_start,
            )
            .count()
        )

    @staticmethod
    def get_daily_fiton_usage(user_id: str, db: Session) -> int:
        """Count fiton-specific deductions for today."""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            db.query(CreditTransaction)
            .filter(
                CreditTransaction.user_id == user_id,
                CreditTransaction.transaction_type == "generation",
                CreditTransaction.description.ilike("%fiton%"),
                CreditTransaction.amount < 0,
                CreditTransaction.created_at >= today_start,
            )
            .count()
        )

    # ── Usage enforcement ─────────────────────────────────────────────────────

    @staticmethod
    def check_can_generate(
        user_id: str, module: str, db: Session
    ) -> tuple[bool, str]:
        """
        Check whether the user may generate an image.

        Returns (can_generate: bool, reason: str).
        reason is empty string on success, or a message on failure.
        """
        plan_key, sub = BillingService.get_user_plan(user_id, db)
        plan = PLANS.get(plan_key, PLANS["free"])

        # ── 1. Daily limit ────────────────────────────────────────────────
        daily_used = BillingService.get_daily_usage(user_id, module, db)
        daily_limit = plan.get("daily_limit", 3)
        if daily_used >= daily_limit:
            return False, f"daily_limit:{daily_used}/{daily_limit}"

        # ── 2. Monthly credit limit (paid plans only) ─────────────────────
        if plan_key != "free" and sub:
            if sub.credits_used >= sub.credits_total:
                return False, f"monthly_limit:{sub.credits_used}/{sub.credits_total}"

        # ── 3. Fit-on access ──────────────────────────────────────────────
        if module == "fiton":
            if not plan.get("fiton_enabled", False):
                return False, "fiton_not_enabled"
            fiton_daily_limit = plan.get("fiton_daily_limit", 0)
            if fiton_daily_limit > 0:
                fiton_used = BillingService.get_daily_fiton_usage(user_id, db)
                if fiton_used >= fiton_daily_limit:
                    return False, f"fiton_daily_limit:{fiton_used}/{fiton_daily_limit}"

        return True, ""

    # ── Credit deduction ──────────────────────────────────────────────────────

    @staticmethod
    def deduct_credit(
        user_id: str,
        generation_id: str,
        module: str,
        db: Session,
    ) -> None:
        """
        Deduct 1 credit for a completed generation and log the transaction.
        Updates subscription.credits_used for paid plans.
        Updates user.credits_remaining.
        """
        cost = CREDIT_COST.get(module, 1)
        plan_key, sub = BillingService.get_user_plan(user_id, db)

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning("deduct_credit: user %s not found", user_id)
            return

        new_balance = max(0, user.credits_remaining - cost)
        user.credits_remaining = new_balance

        tx = CreditTransaction(
            user_id=user_id,
            amount=-cost,
            balance_after=new_balance,
            transaction_type="generation",
            reference_id=generation_id,
            description=f"{module} generation",
        )
        db.add(tx)

        # Update subscription credits_used for paid plans
        if plan_key != "free" and sub:
            sub.credits_used = min(sub.credits_used + cost, sub.credits_total)

        db.commit()

    @staticmethod
    def refund_credit(user_id: str, generation_id: str, db: Session) -> None:
        """Refund 1 credit for a failed generation."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return

        # Find the original deduction
        original_tx = (
            db.query(CreditTransaction)
            .filter(
                CreditTransaction.user_id == user_id,
                CreditTransaction.reference_id == generation_id,
                CreditTransaction.amount < 0,
            )
            .first()
        )
        if not original_tx:
            return

        refund_amount = abs(original_tx.amount)
        new_balance = user.credits_remaining + refund_amount
        user.credits_remaining = new_balance

        tx = CreditTransaction(
            user_id=user_id,
            amount=refund_amount,
            balance_after=new_balance,
            transaction_type="refund",
            reference_id=generation_id,
            description="refund — generation failed",
        )
        db.add(tx)

        # Reverse subscription credits_used
        plan_key, sub = BillingService.get_user_plan(user_id, db)
        if plan_key != "free" and sub:
            sub.credits_used = max(0, sub.credits_used - refund_amount)

        db.commit()

    # ── Subscription management ───────────────────────────────────────────────

    @staticmethod
    def create_subscription(
        user_id: str,
        plan_key: str,
        payhere_subscription_id: str | None,
        db: Session,
    ) -> Subscription:
        """Create (or re-activate) a subscription and grant initial credits."""
        from app.config.plans import PLANS

        plan = PLANS[plan_key]
        now = datetime.utcnow()

        # Cancel any existing active subscription
        existing = BillingService.get_active_subscription(user_id, db)
        if existing:
            existing.status = "cancelled"
            existing.cancelled_at = now

        sub = Subscription(
            user_id=user_id,
            plan=plan_key,
            status="active",
            credits_total=plan["credits_monthly"],
            credits_used=0,
            credits_reset_date=now + timedelta(days=30),
            payhere_subscription_id=payhere_subscription_id,
            started_at=now,
            expires_at=now + timedelta(days=30),
        )
        db.add(sub)
        db.flush()

        # Grant monthly credits to user balance
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            new_balance = user.credits_remaining + plan["credits_monthly"]
            user.credits_remaining = new_balance
            tx = CreditTransaction(
                user_id=user_id,
                amount=plan["credits_monthly"],
                balance_after=new_balance,
                transaction_type="subscription_credit",
                reference_id=sub.id,
                description=f"{plan['name']} plan activation",
            )
            db.add(tx)

        db.commit()
        db.refresh(sub)
        return sub

    # ── Usage summary ─────────────────────────────────────────────────────────

    @staticmethod
    def get_usage_summary(user_id: str, db: Session) -> dict:
        """Return usage stats for the profile/billing pages."""
        plan_key, sub = BillingService.get_user_plan(user_id, db)
        plan = PLANS.get(plan_key, PLANS["free"])
        daily_used = BillingService.get_daily_usage(user_id, "adult", db)
        daily_limit = plan.get("daily_limit", 3)

        return {
            "plan": plan_key,
            "plan_name": plan["name"],
            "price_lkr": plan.get("price_lkr", 0),
            "daily_used": daily_used,
            "daily_limit": daily_limit,
            "monthly_used": sub.credits_used if sub else 0,
            "monthly_limit": sub.credits_total if sub else 0,
            "watermark": plan.get("watermark", True),
            "fiton_enabled": plan.get("fiton_enabled", False),
            "priority_queue": plan.get("priority_queue", False),
            "subscription_status": sub.status if sub else None,
            "expires_at": sub.expires_at.isoformat() if sub and sub.expires_at else None,
        }

    # ── Credit reset helpers (called by scheduler / cron) ────────────────────

    @staticmethod
    def reset_monthly_credits(subscription_id: str, db: Session) -> None:
        """Reset credits_used on a subscription renewal."""
        sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not sub:
            return
        sub.credits_used = 0
        sub.credits_reset_date = datetime.utcnow() + timedelta(days=30)
        sub.expires_at = datetime.utcnow() + timedelta(days=30)
        db.commit()
