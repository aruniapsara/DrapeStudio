"""Tests for phone OTP + JWT authentication system."""

import hashlib
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Environment must be set before imports
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_drapestudio.db")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-testing-only")
os.environ.setdefault("NOTIFY_LK_API_KEY", "")   # dev mode — logs, doesn't send

from app.models.db import OTPRequest, User
from app.services.auth import AuthService
from app.services.otp import OTPService


# ── OTPService unit tests ─────────────────────────────────────────────────────

class TestOTPValidation:
    """Phone number format validation."""

    def test_valid_sri_lanka_phone(self):
        assert OTPService.validate_phone("+94771234567") is True
        assert OTPService.validate_phone("+94712345678") is True
        assert OTPService.validate_phone("+94701234567") is True

    def test_invalid_phones(self):
        assert OTPService.validate_phone("0771234567") is False   # no country code
        assert OTPService.validate_phone("+1234567890") is False  # wrong country
        assert OTPService.validate_phone("+9477123456") is False  # too short
        assert OTPService.validate_phone("+947712345678") is False # too long
        assert OTPService.validate_phone("") is False


class TestOTPGeneration:
    """OTP generation and hashing."""

    def test_generate_otp_is_6_digits(self):
        otp = OTPService.generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()

    def test_generate_otp_is_random(self):
        # Generate 20 OTPs and check they're not all the same
        otps = {OTPService.generate_otp() for _ in range(20)}
        assert len(otps) > 1

    def test_generate_otp_zero_padded(self):
        # Even if random gives 0, it should be "000000"
        with patch("app.services.otp.random.randint", return_value=42):
            otp = OTPService.generate_otp()
            assert otp == "000042"
            assert len(otp) == 6

    def test_hash_otp_is_sha256(self):
        otp = "123456"
        expected = hashlib.sha256(otp.encode()).hexdigest()
        assert OTPService.hash_otp(otp) == expected

    def test_verify_hash_correct(self):
        otp = "654321"
        h = OTPService.hash_otp(otp)
        assert OTPService._verify_hash(otp, h) is True

    def test_verify_hash_wrong(self):
        assert OTPService._verify_hash("111111", OTPService.hash_otp("999999")) is False


class TestOTPRequestLifecycle:
    """DB-backed OTP creation and verification."""

    def test_create_otp_request(self, db_session):
        _, otp = OTPService.create_otp_request("+94771234567", db_session)
        assert len(otp) == 6
        record = db_session.query(OTPRequest).filter(
            OTPRequest.phone == "+94771234567"
        ).first()
        assert record is not None
        assert record.verified is False
        assert record.attempts == 0
        assert record.expires_at > datetime.utcnow()

    def test_verify_and_consume_success(self, db_session):
        phone = "+94771234567"
        _, otp = OTPService.create_otp_request(phone, db_session)
        assert OTPService.verify_and_consume(phone, otp, db_session) is True
        # Should be marked as verified
        record = db_session.query(OTPRequest).filter(
            OTPRequest.phone == phone
        ).first()
        assert record.verified is True

    def test_verify_and_consume_wrong_otp(self, db_session):
        phone = "+94771234567"
        OTPService.create_otp_request(phone, db_session)
        assert OTPService.verify_and_consume(phone, "000000", db_session) is False

    def test_verify_and_consume_no_pending_request(self, db_session):
        assert OTPService.verify_and_consume("+94771234567", "123456", db_session) is False

    def test_verify_and_consume_expired(self, db_session):
        phone = "+94771234567"
        record, otp = OTPService.create_otp_request(phone, db_session)
        # Force-expire the record
        record.expires_at = datetime.utcnow() - timedelta(seconds=1)
        db_session.commit()
        assert OTPService.verify_and_consume(phone, otp, db_session) is False

    def test_verify_and_consume_max_attempts(self, db_session):
        phone = "+94771234567"
        _, otp = OTPService.create_otp_request(phone, db_session)
        # Use up all attempts with wrong OTPs
        for _ in range(3):
            OTPService.verify_and_consume(phone, "000000", db_session)
        # Now the correct OTP should also fail
        assert OTPService.verify_and_consume(phone, otp, db_session) is False

    def test_cooldown_check_after_request(self, db_session):
        phone = "+94771234567"
        OTPService.create_otp_request(phone, db_session)
        assert OTPService.check_cooldown(phone, db_session) is True

    def test_no_cooldown_for_fresh_phone(self, db_session):
        assert OTPService.check_cooldown("+94779999999", db_session) is False


# ── AuthService unit tests ────────────────────────────────────────────────────

class TestJWTTokens:
    """JWT creation and verification."""

    def test_create_and_verify_access_token(self):
        token = AuthService.create_access_token("user_123", "+94771234567", "user")
        payload = AuthService.verify_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user_123"
        assert payload["phone"] == "+94771234567"
        assert payload["role"] == "user"
        assert payload["type"] == "access"

    def test_create_and_verify_refresh_token(self):
        token = AuthService.create_refresh_token("user_123")
        payload = AuthService.verify_refresh_token(token)
        assert payload is not None
        assert payload["sub"] == "user_123"
        assert payload["type"] == "refresh"

    def test_access_token_rejected_as_refresh(self):
        token = AuthService.create_access_token("u1", "+94771234567")
        assert AuthService.verify_refresh_token(token) is None

    def test_refresh_token_rejected_as_access(self):
        token = AuthService.create_refresh_token("u1")
        assert AuthService.verify_access_token(token) is None

    def test_verify_invalid_token(self):
        assert AuthService.verify_token("not.a.valid.jwt") is None

    def test_verify_expired_token(self):
        import jwt as pyjwt
        from app.config import settings
        payload = {
            "sub": "u1",
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        }
        token = pyjwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
        assert AuthService.verify_token(token) is None

    def test_verify_tampered_token(self):
        token = AuthService.create_access_token("u1", "+94771234567")
        tampered = token[:-5] + "XXXXX"
        assert AuthService.verify_token(tampered) is None


class TestGetOrCreateUser:
    """User creation and retrieval."""

    def test_creates_new_user(self, db_session):
        user, is_new = AuthService.get_or_create_user("+94771234567", db_session)
        assert is_new is True
        assert user.phone == "+94771234567"
        assert user.role == "user"
        assert user.credits_remaining == 3

    def test_returns_existing_user(self, db_session):
        user1, _ = AuthService.get_or_create_user("+94771234567", db_session)
        user2, is_new = AuthService.get_or_create_user("+94771234567", db_session)
        assert is_new is False
        assert user1.id == user2.id

    def test_different_phones_create_different_users(self, db_session):
        u1, _ = AuthService.get_or_create_user("+94771234567", db_session)
        u2, _ = AuthService.get_or_create_user("+94779876543", db_session)
        assert u1.id != u2.id


# ── Auth API endpoint tests ───────────────────────────────────────────────────

class TestRequestOTP:
    """POST /api/v1/auth/request-otp"""

    def test_request_otp_valid_phone(self, client, db_session):
        resp = client.post(
            "/api/v1/auth/request-otp",
            json={"phone": "+94771234567"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "expires_in_seconds" in data
        # Record should be created in DB
        record = db_session.query(OTPRequest).filter(
            OTPRequest.phone == "+94771234567"
        ).first()
        assert record is not None

    def test_request_otp_invalid_phone(self, client):
        resp = client.post(
            "/api/v1/auth/request-otp",
            json={"phone": "0771234567"},
        )
        assert resp.status_code == 422

    def test_request_otp_rate_limit(self, client, db_session):
        phone = "+94771234561"
        # First request succeeds
        r1 = client.post("/api/v1/auth/request-otp", json={"phone": phone})
        assert r1.status_code == 200
        # Second request within cooldown is rejected
        r2 = client.post("/api/v1/auth/request-otp", json={"phone": phone})
        assert r2.status_code == 429


class TestVerifyOTP:
    """POST /api/v1/auth/verify-otp"""

    def test_verify_otp_success_creates_user(self, client, db_session):
        phone = "+94771234568"
        _, otp = OTPService.create_otp_request(phone, db_session)

        resp = client.post(
            "/api/v1/auth/verify-otp",
            json={"phone": phone, "otp": otp},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "user_id" in data
        assert data["is_new_user"] is True
        # JWT cookie should be set
        assert "access_token" in resp.cookies

    def test_verify_otp_existing_user_is_not_new(self, client, db_session):
        phone = "+94771234569"
        # Create user first
        AuthService.get_or_create_user(phone, db_session)
        _, otp = OTPService.create_otp_request(phone, db_session)

        resp = client.post(
            "/api/v1/auth/verify-otp",
            json={"phone": phone, "otp": otp},
        )
        assert resp.status_code == 200
        assert resp.json()["is_new_user"] is False

    def test_verify_otp_wrong_code(self, client, db_session):
        phone = "+94771234570"
        OTPService.create_otp_request(phone, db_session)

        resp = client.post(
            "/api/v1/auth/verify-otp",
            json={"phone": phone, "otp": "000000"},
        )
        assert resp.status_code == 400

    def test_verify_otp_invalid_format(self, client):
        resp = client.post(
            "/api/v1/auth/verify-otp",
            json={"phone": "+94771234567", "otp": "12345"},  # only 5 digits
        )
        assert resp.status_code == 422


class TestLogout:
    """POST /api/v1/auth/logout"""

    def test_logout_clears_cookies(self, client):
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        # access_token cookie should be cleared (value empty or deleted)
        if "access_token" in resp.cookies:
            assert resp.cookies["access_token"] == ""


class TestProfileMe:
    """GET /api/v1/auth/me and PATCH /api/v1/auth/me"""

    def _get_jwt_client(self, db_session) -> tuple["TestClient", User]:
        """Create a JWT-authenticated test client."""
        from fastapi.testclient import TestClient
        from app.main import app as fastapi_app
        from app.database import get_db

        phone = "+94771111111"
        user, _ = AuthService.get_or_create_user(phone, db_session)
        token = AuthService.create_access_token(user.id, user.phone, user.role)

        client = TestClient(fastapi_app)
        client.cookies.set("access_token", token)
        return client, user

    def test_get_me_with_valid_jwt(self, db_session):
        jwt_client, user = self._get_jwt_client(db_session)
        resp = jwt_client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == user.id
        assert data["phone"] == user.phone

    def test_get_me_without_token(self, client):
        # client fixture uses legacy username/role cookies (no JWT)
        # The /me endpoint requires JWT
        fresh = TestClient(__import__("app.main", fromlist=["app"]).app)
        resp = fresh.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_patch_me_updates_display_name(self, db_session):
        jwt_client, user = self._get_jwt_client(db_session)
        resp = jwt_client.patch(
            "/api/v1/auth/me",
            json={"display_name": "Sandi Perera"},
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Sandi Perera"
        # Verify DB
        db_session.refresh(user)
        assert user.display_name == "Sandi Perera"
