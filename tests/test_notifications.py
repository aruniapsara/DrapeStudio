"""Tests for Prompt 20: PWA notifications, WhatsApp, push subscription API."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
TESTER_COOKIES = {"username": "tester", "role": "tester"}


# ── WhatsApp service ──────────────────────────────────────────────────────────

class TestWhatsAppService:
    def setup_method(self):
        from app.services.whatsapp import WhatsAppService
        self.svc = WhatsAppService()

    def test_generate_open_link_encodes_message(self):
        link = self.svc.generate_open_link("Hello World")
        assert "wa.me" in link
        assert "Hello" in link or "Hello%20World" in link

    def test_generate_share_link_includes_phone(self):
        link = self.svc.generate_share_link("94771234567", "Test message")
        assert "94771234567" in link
        assert "wa.me" in link

    def test_generate_share_link_strips_plus(self):
        link = self.svc.generate_share_link("+94771234567", "Hello")
        assert "+94" not in link
        assert "94771234567" in link

    def test_generate_catalogue_message_contains_business_name(self):
        msg = self.svc.generate_catalogue_message("MyShop", "https://example.com/results/123")
        assert "MyShop" in msg
        assert "DrapeStudio" in msg

    def test_generate_catalogue_message_contains_url(self):
        msg = self.svc.generate_catalogue_message("Shop", "https://example.com/p/123")
        assert "https://example.com/p/123" in msg

    def test_generate_fiton_message_contains_size_and_confidence(self):
        msg = self.svc.generate_fiton_message("L", 87, "https://example.com/results/abc")
        assert "L" in msg
        assert "87" in msg
        assert "DrapeStudio" in msg

    def test_social_share_urls_returns_dict(self):
        urls = self.svc.social_share_urls("https://example.com/page")
        assert "whatsapp" in urls
        assert "facebook" in urls
        assert "wa.me" in urls["whatsapp"]
        assert "facebook.com" in urls["facebook"]

    def test_social_share_urls_encodes_url(self):
        urls = self.svc.social_share_urls("https://example.com/a b")
        assert " " not in urls["whatsapp"]
        assert " " not in urls["facebook"]


# ── SMS service (no real calls) ───────────────────────────────────────────────

class TestSMSService:
    def test_send_skips_when_no_credentials(self):
        from app.services.sms import SMSService
        svc = SMSService()
        # With empty credentials (default test env), should return False without raising
        result = svc.send(phone="+94771234567", message="Test")
        assert result is False


# ── Push notification service (unit) ─────────────────────────────────────────

class TestPushNotificationService:
    def test_send_skips_when_no_vapid_keys(self, db_session):
        from app.services.push_notification import PushNotificationService
        svc = PushNotificationService()
        # No VAPID keys in test env — should return 0 without raising
        count = svc.send_generation_complete("user123", "gen123", "adult", db_session)
        assert count == 0

    def test_save_subscription_creates_record(self, db_session):
        from app.services.push_notification import PushNotificationService
        from app.models.db import PushSubscription, User, generate_ulid
        svc = PushNotificationService()

        # Create a real user first
        user = User(
            id=generate_ulid(),
            phone="+94700000001",
            role="user",
        )
        db_session.add(user)
        db_session.commit()

        sub = svc.save_subscription(
            user_id=user.id,
            subscription={
                "endpoint": "https://fcm.googleapis.com/fcm/test-endpoint",
                "keys": {"p256dh": "AAAA", "auth": "BBBB"},
            },
            db=db_session,
        )
        assert sub.id is not None
        assert sub.user_id == user.id
        assert sub.endpoint == "https://fcm.googleapis.com/fcm/test-endpoint"

    def test_save_subscription_upserts_on_same_endpoint(self, db_session):
        from app.services.push_notification import PushNotificationService
        from app.models.db import User, generate_ulid
        svc = PushNotificationService()

        user = User(id=generate_ulid(), phone="+94700000002", role="user")
        db_session.add(user)
        db_session.commit()

        endpoint = "https://fcm.googleapis.com/fcm/endpoint-upsert"
        svc.save_subscription(user.id, {"endpoint": endpoint, "keys": {"p256dh": "A", "auth": "B"}}, db_session)
        sub2 = svc.save_subscription(user.id, {"endpoint": endpoint, "keys": {"p256dh": "C", "auth": "D"}}, db_session)
        assert sub2.keys_p256dh == "C"
        assert sub2.keys_auth == "D"

    def test_delete_subscription(self, db_session):
        from app.services.push_notification import PushNotificationService
        from app.models.db import User, generate_ulid
        svc = PushNotificationService()

        user = User(id=generate_ulid(), phone="+94700000003", role="user")
        db_session.add(user)
        db_session.commit()

        endpoint = "https://fcm.googleapis.com/fcm/to-delete"
        svc.save_subscription(user.id, {"endpoint": endpoint, "keys": {"p256dh": "X", "auth": "Y"}}, db_session)
        deleted = svc.delete_subscription(user.id, endpoint, db_session)
        assert deleted is True
        # Second delete returns False
        deleted_again = svc.delete_subscription(user.id, endpoint, db_session)
        assert deleted_again is False


# ── Notification preferences API ─────────────────────────────────────────────

class TestNotificationPreferencesAPI:
    def setup_method(self):
        self.client = TestClient(app)

    def test_get_preferences_requires_jwt(self):
        resp = self.client.get("/api/v1/notifications/preferences")
        assert resp.status_code == 401

    def test_patch_preferences_requires_jwt(self):
        resp = self.client.patch(
            "/api/v1/notifications/preferences",
            json={"sms_notifications_enabled": True},
        )
        assert resp.status_code == 401

    def test_subscribe_push_requires_jwt(self):
        resp = self.client.post(
            "/api/v1/notifications/subscribe",
            json={"endpoint": "https://fcm.example.com/push", "keys": {"p256dh": "A", "auth": "B"}},
        )
        assert resp.status_code == 401

    def test_get_preferences_with_legacy_cookies_returns_401(self):
        resp = self.client.get(
            "/api/v1/notifications/preferences",
            cookies=TESTER_COOKIES,
        )
        # Legacy users cannot use notification API
        assert resp.status_code == 401


# ── Offline page ──────────────────────────────────────────────────────────────

class TestOfflinePage:
    def setup_method(self):
        self.client = TestClient(app)

    def test_offline_page_renders(self):
        resp = self.client.get("/offline.html")
        assert resp.status_code == 200
        assert "You're Offline" in resp.text

    def test_offline_page_has_retry_button(self):
        resp = self.client.get("/offline.html")
        assert "Try Again" in resp.text

    def test_offline_page_has_sync_message(self):
        resp = self.client.get("/offline.html")
        assert "sync" in resp.text.lower()


# ── Service worker ────────────────────────────────────────────────────────────

class TestServiceWorker:
    def setup_method(self):
        self.client = TestClient(app)

    def test_sw_js_served(self):
        resp = self.client.get("/static/sw.js")
        assert resp.status_code == 200
        assert "push" in resp.text.lower()

    def test_sw_js_has_push_listener(self):
        resp = self.client.get("/static/sw.js")
        assert "addEventListener('push'" in resp.text

    def test_sw_js_has_notification_click_listener(self):
        resp = self.client.get("/static/sw.js")
        assert "notificationclick" in resp.text

    def test_sw_js_has_background_sync(self):
        resp = self.client.get("/static/sw.js")
        assert "sync" in resp.text
