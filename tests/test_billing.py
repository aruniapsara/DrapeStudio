"""Tests for billing system — credit management, plans, PayHere integration."""

import hashlib
from datetime import datetime, timedelta

import pytest

from app.config.plans import PLANS, PLAN_ORDER
from app.models.db import CreditTransaction, Subscription, User, generate_ulid
from app.services.billing import BillingService
from app.services.payhere import PayHereService


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_user(db, phone="+94771000001", credits=3) -> User:
    """Create and persist a test user."""
    user = User(
        id=generate_ulid(),
        phone=phone,
        display_name="Test User",
        role="user",
        credits_remaining=credits,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── Plan configuration ────────────────────────────────────────────────────────

class TestPlanConfiguration:
    def test_all_plans_exist(self):
        for key in ("free", "basic", "pro"):
            assert key in PLANS

    def test_plan_order(self):
        assert PLAN_ORDER == ["free", "basic", "pro"]

    def test_free_plan_has_no_price(self):
        assert PLANS["free"]["price_lkr"] == 0
        assert PLANS["free"]["credits_monthly"] == 0
        assert PLANS["free"]["daily_limit"] == 3
        assert PLANS["free"]["watermark"] is True
        assert PLANS["free"]["fiton_enabled"] is False

    def test_basic_plan_config(self):
        p = PLANS["basic"]
        assert p["price_lkr"] == 990
        assert p["credits_monthly"] == 150
        assert p["daily_limit"] == 30
        assert p["watermark"] is False
        assert p["fiton_enabled"] is True
        assert p["fiton_daily_limit"] == 3

    def test_pro_plan_config(self):
        p = PLANS["pro"]
        assert p["price_lkr"] == 2490
        assert p["credits_monthly"] == 500
        assert p["daily_limit"] == 100
        assert p["watermark"] is False
        assert p["fiton_enabled"] is True
        assert p["fiton_daily_limit"] == 0  # unlimited
        assert p["priority_queue"] is True


# ── BillingService ────────────────────────────────────────────────────────────

class TestBillingService:
    def test_get_user_plan_free_no_subscription(self, db_session):
        user = make_user(db_session)
        plan_key, sub = BillingService.get_user_plan(user.id, db_session)
        assert plan_key == "free"
        assert sub is None

    def test_get_user_plan_with_active_subscription(self, db_session):
        user = make_user(db_session)
        sub = Subscription(
            id=generate_ulid(),
            user_id=user.id,
            plan="basic",
            status="active",
            credits_total=150,
            credits_used=0,
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db_session.add(sub)
        db_session.commit()

        plan_key, fetched_sub = BillingService.get_user_plan(user.id, db_session)
        assert plan_key == "basic"
        assert fetched_sub is not None
        assert fetched_sub.id == sub.id

    def test_check_can_generate_free_within_limit(self, db_session):
        user = make_user(db_session)
        can, reason = BillingService.check_can_generate(user.id, "adult", db_session)
        assert can is True
        assert reason == ""

    def test_check_can_generate_free_at_daily_limit(self, db_session):
        user = make_user(db_session, credits=0)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Insert 3 generation transactions for today
        for i in range(3):
            tx = CreditTransaction(
                id=generate_ulid(),
                user_id=user.id,
                amount=-1,
                balance_after=max(0, 2 - i),
                transaction_type="generation",
                description="adult generation",
                created_at=today_start + timedelta(hours=i + 1),
            )
            db_session.add(tx)
        db_session.commit()

        can, reason = BillingService.check_can_generate(user.id, "adult", db_session)
        assert can is False
        assert "daily_limit" in reason

    def test_check_can_generate_paid_monthly_limit_exceeded(self, db_session):
        user = make_user(db_session, credits=0)
        sub = Subscription(
            id=generate_ulid(),
            user_id=user.id,
            plan="basic",
            status="active",
            credits_total=150,
            credits_used=150,  # exhausted
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db_session.add(sub)
        db_session.commit()

        can, reason = BillingService.check_can_generate(user.id, "adult", db_session)
        assert can is False
        assert "monthly_limit" in reason

    def test_check_can_generate_fiton_not_enabled_on_free(self, db_session):
        user = make_user(db_session)
        can, reason = BillingService.check_can_generate(user.id, "fiton", db_session)
        assert can is False
        assert reason == "fiton_not_enabled"

    def test_deduct_credit_reduces_balance(self, db_session):
        user = make_user(db_session, credits=10)
        gen_id = "gen_test001"

        BillingService.deduct_credit(user.id, gen_id, "adult", db_session)

        db_session.refresh(user)
        assert user.credits_remaining == 9

        tx = (
            db_session.query(CreditTransaction)
            .filter(CreditTransaction.user_id == user.id, CreditTransaction.reference_id == gen_id)
            .first()
        )
        assert tx is not None
        assert tx.amount == -1
        assert tx.balance_after == 9
        assert tx.transaction_type == "generation"

    def test_refund_credit_reverses_deduction(self, db_session):
        user = make_user(db_session, credits=10)
        gen_id = "gen_refund001"

        BillingService.deduct_credit(user.id, gen_id, "adult", db_session)
        db_session.refresh(user)
        assert user.credits_remaining == 9

        BillingService.refund_credit(user.id, gen_id, db_session)
        db_session.refresh(user)
        assert user.credits_remaining == 10

        refund_tx = (
            db_session.query(CreditTransaction)
            .filter(
                CreditTransaction.user_id == user.id,
                CreditTransaction.reference_id == gen_id,
                CreditTransaction.transaction_type == "refund",
            )
            .first()
        )
        assert refund_tx is not None
        assert refund_tx.amount == 1

    def test_create_subscription_grants_credits(self, db_session):
        user = make_user(db_session, credits=3)

        sub = BillingService.create_subscription(user.id, "basic", None, db_session)

        db_session.refresh(user)
        assert sub.plan == "basic"
        assert sub.status == "active"
        assert sub.credits_total == 150
        assert user.credits_remaining == 3 + 150  # initial + granted

    def test_create_subscription_cancels_existing(self, db_session):
        user = make_user(db_session, credits=3)

        old_sub = Subscription(
            id=generate_ulid(),
            user_id=user.id,
            plan="basic",
            status="active",
            credits_total=150,
            credits_used=0,
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db_session.add(old_sub)
        db_session.commit()

        BillingService.create_subscription(user.id, "pro", None, db_session)
        db_session.refresh(old_sub)

        assert old_sub.status == "cancelled"
        assert old_sub.cancelled_at is not None

    def test_get_usage_summary_free_plan(self, db_session):
        user = make_user(db_session)
        summary = BillingService.get_usage_summary(user.id, db_session)

        assert summary["plan"] == "free"
        assert summary["plan_name"] == "Free"
        assert summary["daily_limit"] == 3
        assert summary["monthly_limit"] == 0
        assert summary["watermark"] is True
        assert summary["fiton_enabled"] is False

    def test_reset_monthly_credits(self, db_session):
        user = make_user(db_session)
        sub = Subscription(
            id=generate_ulid(),
            user_id=user.id,
            plan="basic",
            status="active",
            credits_total=150,
            credits_used=80,
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=1),
        )
        db_session.add(sub)
        db_session.commit()

        BillingService.reset_monthly_credits(sub.id, db_session)
        db_session.refresh(sub)

        assert sub.credits_used == 0
        assert sub.credits_reset_date > datetime.utcnow()


# ── PayHereService ────────────────────────────────────────────────────────────

class TestPayHereService:
    def test_create_checkout_contains_required_fields(self, db_session):
        user = make_user(db_session, phone="+94771234567")
        service = PayHereService()
        data = service.create_checkout(user, "basic")

        required = ["merchant_id", "order_id", "amount", "currency", "hash",
                    "return_url", "cancel_url", "notify_url", "items"]
        for field in required:
            assert field in data, f"Missing field: {field}"

        assert data["currency"] == "LKR"
        assert data["amount"] == "990.00"

    def test_checkout_hash_format(self, db_session):
        user = make_user(db_session)
        service = PayHereService()
        data = service.create_checkout(user, "basic")
        # Hash should be uppercase hex of 32 chars
        assert len(data["hash"]) == 32
        assert data["hash"] == data["hash"].upper()

    def test_verify_notification_valid_signature(self):
        """Test that correct signature passes verification."""
        from unittest.mock import patch
        from app.config import settings

        with patch.object(settings, "PAYHERE_MERCHANT_ID", "TEST_MERCHANT"), \
             patch.object(settings, "PAYHERE_MERCHANT_SECRET", "TEST_SECRET"):
            service = PayHereService()
            merchant_id = "TEST_MERCHANT"
            secret = "TEST_SECRET"
            order_id = "ORD001"
            amount = "990.00"
            currency = "LKR"
            status_code = "2"

            secret_hash = hashlib.md5(secret.encode()).hexdigest().upper()
            sig = hashlib.md5(
                f"{merchant_id}{order_id}{amount}{currency}{status_code}{secret_hash}".encode()
            ).hexdigest().upper()

            params = {
                "merchant_id": merchant_id,
                "order_id": order_id,
                "payhere_amount": amount,
                "payhere_currency": currency,
                "status_code": status_code,
                "md5sig": sig,
            }
            assert service.verify_notification(params) is True

    def test_verify_notification_invalid_signature(self):
        service = PayHereService()
        params = {
            "merchant_id": "TEST",
            "order_id": "ORD001",
            "payhere_amount": "990.00",
            "payhere_currency": "LKR",
            "status_code": "2",
            "md5sig": "INVALIDHASH",
        }
        assert service.verify_notification(params) is False

    def test_verify_notification_missing_sig(self):
        service = PayHereService()
        params = {
            "merchant_id": "TEST",
            "order_id": "ORD001",
            "payhere_amount": "990.00",
            "payhere_currency": "LKR",
            "status_code": "2",
        }
        assert service.verify_notification(params) is False


# ── Billing API endpoints ─────────────────────────────────────────────────────

class TestBillingAPI:
    def test_usage_requires_jwt_auth(self, client):
        """Legacy-cookie auth (tester) should get 401 from JWT-only endpoint."""
        res = client.get("/api/v1/billing/usage")
        assert res.status_code == 401

    def test_history_requires_jwt_auth(self, client):
        res = client.get("/api/v1/billing/history")
        assert res.status_code == 401

    def test_subscribe_requires_jwt_auth(self, client):
        res = client.post("/api/v1/billing/subscribe/basic")
        assert res.status_code == 401

    def test_subscribe_invalid_plan(self, client, db_session):
        """Even with invalid plan, we need JWT — so 401 comes first."""
        res = client.post("/api/v1/billing/subscribe/invalid_plan")
        assert res.status_code == 401

    def test_pricing_page_renders(self, client):
        res = client.get("/pricing")
        assert res.status_code == 200
        assert b"DrapeStudio" in res.content

    def test_billing_history_page_renders(self, client):
        res = client.get("/billing/history")
        assert res.status_code == 200

    def test_billing_success_page_renders(self, client):
        res = client.get("/billing/success")
        assert res.status_code == 200

    def test_billing_cancel_page_renders(self, client):
        res = client.get("/billing/cancel")
        assert res.status_code == 200
