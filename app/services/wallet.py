"""Wallet-based billing service for DrapeStudio v2.

Replaces the subscription/credit model with a prepaid wallet that works
like a Sri Lankan mobile phone reload (Dialog, Mobitel pattern).
"""

import logging
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.config.wallet_pricing import (
    FITON_PRICE,
    IMAGE_PRICES,
    PACKAGES,
    TRIAL,
)
from app.models.db import (
    User,
    Wallet,
    WalletTopup,
    WalletTransaction,
    generate_ulid,
)

logger = logging.getLogger(__name__)


class WalletService:
    """Handles wallet balance, trial tracking, and per-image deductions."""

    # ── Wallet access ──────────────────────────────────────────────────────────

    @staticmethod
    def get_or_create_wallet(user_id: str, db: Session) -> Wallet:
        """Return the wallet for a user, creating one if it doesn't exist."""
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
        if wallet:
            return wallet

        wallet = Wallet(
            user_id=user_id,
            trial_expires_at=datetime.utcnow() + timedelta(days=TRIAL["duration_days"]),
        )
        db.add(wallet)
        db.flush()
        return wallet

    # ── Pricing ────────────────────────────────────────────────────────────────

    @staticmethod
    def get_image_cost(module: str, quality: str = "1k") -> int:
        """Get cost in LKR for generating one image."""
        if module == "fiton":
            return FITON_PRICE
        return IMAGE_PRICES.get(quality, IMAGE_PRICES["1k"])

    @staticmethod
    def get_total_cost(module: str, quality: str, image_count: int) -> int:
        """Get total cost in LKR for generating image_count images."""
        return WalletService.get_image_cost(module, quality) * image_count

    # ── Pre-generation check ───────────────────────────────────────────────────

    @staticmethod
    def check_can_generate(
        user: User,
        module: str,
        quality: str,
        image_count: int,
        db: Session,
    ) -> tuple[bool, str]:
        """Check if user can afford image_count images.

        Returns:
            (can_generate, source) where source is one of:
            "unrestricted", "trial", "premium_fiton", "premium", "wallet",
            or on failure: "insufficient_balance", "trial_exhausted".
        """
        # Admin/tester bypass
        if user.role in ("admin", "tester"):
            return True, "unrestricted"

        # Sponsored account bypass
        if user.is_sponsored:
            if user.sponsored_until is None or user.sponsored_until >= date.today():
                return True, "sponsored"
            else:
                # Sponsorship expired — auto-clear
                user.is_sponsored = False
                user.sponsored_by = None
                user.sponsored_until = None
                db.commit()

        wallet = WalletService.get_or_create_wallet(user.id, db)
        total_cost = WalletService.get_total_cost(module, quality, image_count)
        now = datetime.utcnow()

        # Trial period check
        if wallet.trial_expires_at and wallet.trial_expires_at > now:
            if module == "fiton":
                if wallet.trial_fiton_used < TRIAL.get("fiton_images", 1):
                    return True, "trial"
            else:
                remaining_trial = TRIAL["free_images"] - wallet.trial_images_used
                if remaining_trial >= image_count:
                    return True, "trial"

        # Premium check
        if wallet.is_premium and wallet.premium_expires_at and wallet.premium_expires_at > now:
            # Fit-on is unlimited for premium
            if module == "fiton":
                return True, "premium_fiton"
            # Premium wallet allocation
            if wallet.premium_balance_lkr >= total_cost:
                return True, "premium"
            # Fall through to prepaid wallet

        # Prepaid wallet check
        if wallet.balance_lkr >= total_cost:
            return True, "wallet"

        return False, "insufficient_balance"

    # ── Deduction ──────────────────────────────────────────────────────────────

    @staticmethod
    def deduct(
        user_id: str,
        generation_id: str,
        module: str,
        quality: str,
        image_count: int,
        source: str,
        db: Session,
    ) -> WalletTransaction | None:
        """Deduct from wallet and log transaction.

        Args:
            source: The billing source from check_can_generate
                    ("unrestricted", "trial", "premium", "premium_fiton", "wallet").
        """
        wallet = WalletService.get_or_create_wallet(user_id, db)
        cost = WalletService.get_total_cost(module, quality, image_count)

        if source == "unrestricted":
            # Admin/tester — no deduction, but still log
            tx = WalletTransaction(
                user_id=user_id,
                amount_lkr=0,
                balance_after=wallet.balance_lkr,
                transaction_type="generation",
                reference_id=generation_id,
                description=f"{module} {quality} x{image_count} (admin/tester)",
            )
            db.add(tx)
            db.flush()
            return tx

        if source == "sponsored":
            # Sponsored — no deduction, but log
            tx = WalletTransaction(
                user_id=user_id,
                amount_lkr=0,
                balance_after=wallet.balance_lkr,
                transaction_type="generation",
                reference_id=generation_id,
                description=f"{module} {quality} x{image_count} (sponsored)",
            )
            db.add(tx)
            db.flush()
            return tx

        if source == "trial":
            if module == "fiton":
                wallet.trial_fiton_used += 1
            else:
                wallet.trial_images_used += image_count
            tx = WalletTransaction(
                user_id=user_id,
                amount_lkr=0,
                balance_after=wallet.balance_lkr,
                transaction_type="trial",
                reference_id=generation_id,
                description=f"{module} {quality} x{image_count} (trial)",
            )
            db.add(tx)
            db.flush()
            return tx

        if source == "premium_fiton":
            # Fit-on unlimited for premium — no deduction
            tx = WalletTransaction(
                user_id=user_id,
                amount_lkr=0,
                balance_after=wallet.balance_lkr,
                transaction_type="generation",
                reference_id=generation_id,
                description=f"fiton (premium unlimited)",
            )
            db.add(tx)
            db.flush()
            return tx

        if source == "premium":
            wallet.premium_balance_lkr -= cost
            wallet.total_spent += cost
            balance_after = wallet.premium_balance_lkr
        else:
            # Regular prepaid wallet
            wallet.balance_lkr -= cost
            wallet.total_spent += cost
            balance_after = wallet.balance_lkr

        tx = WalletTransaction(
            user_id=user_id,
            amount_lkr=-cost,
            balance_after=balance_after,
            transaction_type="generation",
            reference_id=generation_id,
            description=f"{module} {quality} x{image_count}",
        )
        db.add(tx)
        db.flush()
        return tx

    # ── Top-up ─────────────────────────────────────────────────────────────────

    @staticmethod
    def process_topup(
        user_id: str,
        package_key: str,
        payhere_payment_id: str | None,
        db: Session,
    ) -> WalletTopup:
        """Process a wallet reload purchase."""
        package = PACKAGES.get(package_key)
        if not package:
            raise ValueError(f"Unknown package: {package_key}")

        wallet = WalletService.get_or_create_wallet(user_id, db)

        if package.get("type") == "subscription":
            # Premium subscription
            load_amount = package["wallet_load_lkr"]
            wallet.is_premium = True
            wallet.premium_balance_lkr = load_amount
            wallet.premium_expires_at = datetime.utcnow() + timedelta(days=30)
        else:
            # Prepaid package
            load_amount = package["total_lkr"]
            wallet.balance_lkr += load_amount

        wallet.total_loaded += load_amount

        topup = WalletTopup(
            user_id=user_id,
            package_key=package_key,
            amount_paid_lkr=package["price_lkr"],
            amount_loaded_lkr=load_amount,
            payhere_payment_id=payhere_payment_id,
            status="completed",
        )
        db.add(topup)
        db.flush()

        tx = WalletTransaction(
            user_id=user_id,
            amount_lkr=load_amount,
            balance_after=wallet.balance_lkr,
            transaction_type="topup",
            reference_id=topup.id,
            description=f"{package_key} package reload",
        )
        db.add(tx)
        db.commit()

        return topup

    # ── Admin operations ───────────────────────────────────────────────────────

    @staticmethod
    def admin_grant(
        user_id: str,
        amount_lkr: int,
        admin_user_id: str,
        db: Session,
    ) -> WalletTransaction:
        """Admin grants wallet balance to a user."""
        wallet = WalletService.get_or_create_wallet(user_id, db)
        wallet.balance_lkr += amount_lkr
        wallet.total_loaded += amount_lkr

        tx = WalletTransaction(
            user_id=user_id,
            amount_lkr=amount_lkr,
            balance_after=wallet.balance_lkr,
            transaction_type="admin_grant",
            reference_id=admin_user_id,
            description=f"Admin granted Rs. {amount_lkr}",
        )
        db.add(tx)
        db.commit()
        return tx

    @staticmethod
    def refund(
        user_id: str,
        generation_id: str,
        db: Session,
    ) -> WalletTransaction | None:
        """Refund a generation cost back to the wallet."""
        # Find the original deduction
        original_tx = (
            db.query(WalletTransaction)
            .filter(
                WalletTransaction.user_id == user_id,
                WalletTransaction.reference_id == generation_id,
                WalletTransaction.amount_lkr < 0,
            )
            .first()
        )
        if not original_tx:
            return None

        refund_amount = abs(original_tx.amount_lkr)
        wallet = WalletService.get_or_create_wallet(user_id, db)
        wallet.balance_lkr += refund_amount
        wallet.total_spent -= refund_amount

        tx = WalletTransaction(
            user_id=user_id,
            amount_lkr=refund_amount,
            balance_after=wallet.balance_lkr,
            transaction_type="refund",
            reference_id=generation_id,
            description="Refund — generation failed",
        )
        db.add(tx)
        db.commit()
        return tx

    # ── Usage summary ──────────────────────────────────────────────────────────

    @staticmethod
    def get_wallet_summary(user_id: str, db: Session) -> dict:
        """Return wallet stats for profile/billing pages."""
        wallet = WalletService.get_or_create_wallet(user_id, db)
        now = datetime.utcnow()

        in_trial = bool(
            wallet.trial_expires_at
            and wallet.trial_expires_at > now
            and wallet.trial_images_used < TRIAL["free_images"]
        )

        return {
            "balance_lkr": wallet.balance_lkr,
            "total_loaded": wallet.total_loaded,
            "total_spent": wallet.total_spent,
            "in_trial": in_trial,
            "trial_images_used": wallet.trial_images_used,
            "trial_images_total": TRIAL["free_images"],
            "trial_expires_at": (
                wallet.trial_expires_at.isoformat()
                if wallet.trial_expires_at
                else None
            ),
            "is_premium": wallet.is_premium,
            "premium_balance_lkr": wallet.premium_balance_lkr,
            "premium_expires_at": (
                wallet.premium_expires_at.isoformat()
                if wallet.premium_expires_at
                else None
            ),
        }
