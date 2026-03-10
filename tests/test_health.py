"""Tests for Prompt 21: Health check, metrics, and monitoring endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

TESTER_COOKIES = {"username": "tester", "role": "tester"}


class TestHealthEndpoints:
    def setup_method(self):
        self.tc = TestClient(app)

    def test_health_returns_200(self):
        resp = self.tc.get("/health")
        assert resp.status_code == 200

    def test_health_returns_status_ok(self):
        resp = self.tc.get("/health")
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_returns_version(self):
        resp = self.tc.get("/health")
        data = resp.json()
        assert "version" in data
        assert data["version"]  # non-empty

    def test_health_is_public(self):
        """Health endpoint must be accessible without authentication."""
        resp = self.tc.get("/health")
        assert resp.status_code == 200
        # Should not redirect to login
        assert resp.headers.get("location", "") != "/login"

    def test_health_detailed_returns_200(self):
        resp = self.tc.get("/health/detailed")
        assert resp.status_code == 200

    def test_health_detailed_has_checks(self):
        resp = self.tc.get("/health/detailed")
        data = resp.json()
        assert "checks" in data
        assert "database" in data["checks"]
        assert "redis" in data["checks"]
        assert "gemini" in data["checks"]

    def test_health_detailed_has_uptime(self):
        resp = self.tc.get("/health/detailed")
        data = resp.json()
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0

    def test_health_detailed_database_ok(self):
        """Database should be reachable in test environment."""
        resp = self.tc.get("/health/detailed")
        data = resp.json()
        assert data["checks"]["database"] == "ok"

    def test_health_detailed_is_public(self):
        resp = self.tc.get("/health/detailed")
        assert resp.status_code == 200

    def test_metrics_returns_200(self):
        resp = self.tc.get("/metrics", cookies=TESTER_COOKIES)
        assert resp.status_code == 200

    def test_metrics_is_public(self):
        """Metrics endpoint is public (no auth required)."""
        resp = self.tc.get("/metrics")
        assert resp.status_code == 200

    def test_metrics_has_expected_fields(self):
        resp = self.tc.get("/metrics")
        data = resp.json()
        assert "total_users" in data
        assert "total_generations" in data
        assert "generations_today" in data
        assert "queue_depth" in data
        assert "uptime_seconds" in data

    def test_metrics_counts_are_non_negative(self):
        resp = self.tc.get("/metrics")
        data = resp.json()
        assert data["total_users"] >= 0
        assert data["total_generations"] >= 0
        assert data["generations_today"] >= 0


class TestSitemap:
    def setup_method(self):
        self.tc = TestClient(app)

    def test_sitemap_returns_200(self):
        resp = self.tc.get("/sitemap.xml")
        assert resp.status_code == 200

    def test_sitemap_content_type_is_xml(self):
        resp = self.tc.get("/sitemap.xml")
        assert "xml" in resp.headers.get("content-type", "")

    def test_sitemap_contains_home_url(self):
        resp = self.tc.get("/sitemap.xml")
        assert "<loc>" in resp.text
        assert "/</loc>" in resp.text or "http" in resp.text

    def test_sitemap_contains_pricing(self):
        resp = self.tc.get("/sitemap.xml")
        assert "/pricing" in resp.text

    def test_sitemap_is_public(self):
        resp = self.tc.get("/sitemap.xml")
        assert resp.status_code == 200


class TestRobotsTxt:
    def setup_method(self):
        self.tc = TestClient(app)

    def test_robots_txt_served(self):
        resp = self.tc.get("/static/robots.txt")
        assert resp.status_code == 200

    def test_robots_txt_allows_root(self):
        resp = self.tc.get("/static/robots.txt")
        assert "Allow: /" in resp.text

    def test_robots_txt_disallows_api(self):
        resp = self.tc.get("/static/robots.txt")
        assert "Disallow: /api/" in resp.text

    def test_robots_txt_has_sitemap(self):
        resp = self.tc.get("/static/robots.txt")
        assert "Sitemap:" in resp.text


class TestSecurityHeaders:
    def setup_method(self):
        self.tc = TestClient(app)

    def test_health_has_x_content_type_options(self):
        resp = self.tc.get("/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_health_has_x_frame_options(self):
        resp = self.tc.get("/health")
        assert resp.headers.get("x-frame-options") == "DENY"

    def test_health_has_referrer_policy(self):
        resp = self.tc.get("/health")
        assert "strict-origin" in resp.headers.get("referrer-policy", "")


class TestBaseTemplateContext:
    """Verify that new template context vars are injected."""

    def setup_method(self):
        self.tc = TestClient(app)

    def test_home_page_includes_app_version_in_asset_url(self):
        resp = self.tc.get("/", cookies=TESTER_COOKIES)
        assert resp.status_code == 200
        # Cache-busted CSS URL should contain ?v=
        assert "style.css?v=" in resp.text

    def test_home_page_has_seo_title(self):
        resp = self.tc.get("/", cookies=TESTER_COOKIES)
        assert resp.status_code == 200
        assert "<title>" in resp.text

    def test_home_page_has_og_tags(self):
        resp = self.tc.get("/", cookies=TESTER_COOKIES)
        assert resp.status_code == 200
        assert 'property="og:title"' in resp.text
