"""Tests for trial period enforcement — 3 images, 1k only."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.config.wallet_pricing import TRIAL


class TestTrialConfig:
    """Verify trial configuration constants."""

    def test_trial_free_images_is_3(self):
        assert TRIAL["free_images"] == 3

    def test_trial_max_quality_is_1k(self):
        assert TRIAL["max_quality"] == "1k"

    def test_trial_duration_7_days(self):
        assert TRIAL["duration_days"] == 7

    def test_trial_fiton_images_is_1(self):
        assert TRIAL["fiton_images"] == 1


class TestTrialWalletEnforcement:
    """Test WalletService.check_can_generate() with trial restrictions."""

    def _make_user(self, role="user", is_sponsored=False):
        user = MagicMock()
        user.role = role
        user.is_sponsored = is_sponsored
        return user

    def _make_wallet(
        self,
        trial_images_used=0,
        trial_fiton_used=0,
        trial_expires_at=None,
        balance_lkr=0,
        total_loaded=0,
        is_premium=False,
        premium_balance_lkr=0,
        premium_expires_at=None,
    ):
        wallet = MagicMock()
        wallet.trial_images_used = trial_images_used
        wallet.trial_fiton_used = trial_fiton_used
        wallet.trial_expires_at = trial_expires_at or (datetime.utcnow() + timedelta(days=5))
        wallet.balance_lkr = balance_lkr
        wallet.total_loaded = total_loaded
        wallet.is_premium = is_premium
        wallet.premium_balance_lkr = premium_balance_lkr
        wallet.premium_expires_at = premium_expires_at
        return wallet

    @patch("app.services.wallet.WalletService.get_or_create_wallet")
    def test_trial_allows_1k_quality(self, mock_get_wallet):
        """Trial user generating 1k image should succeed."""
        from app.services.wallet import WalletService

        user = self._make_user()
        wallet = self._make_wallet(trial_images_used=0)
        mock_get_wallet.return_value = wallet

        can, source = WalletService.check_can_generate(
            user, "adult", "1k", 1, MagicMock()
        )
        assert can is True
        assert source == "trial"

    @patch("app.services.wallet.WalletService.get_or_create_wallet")
    def test_trial_rejects_2k_quality(self, mock_get_wallet):
        """Trial user generating 2k image should be rejected."""
        from app.services.wallet import WalletService

        user = self._make_user()
        wallet = self._make_wallet(trial_images_used=0)
        mock_get_wallet.return_value = wallet

        can, source = WalletService.check_can_generate(
            user, "adult", "2k", 1, MagicMock()
        )
        assert can is False
        assert source == "trial_quality_restricted"

    @patch("app.services.wallet.WalletService.get_or_create_wallet")
    def test_trial_rejects_4k_quality(self, mock_get_wallet):
        """Trial user generating 4k image should be rejected."""
        from app.services.wallet import WalletService

        user = self._make_user()
        wallet = self._make_wallet(trial_images_used=0)
        mock_get_wallet.return_value = wallet

        can, source = WalletService.check_can_generate(
            user, "adult", "4k", 1, MagicMock()
        )
        assert can is False
        assert source == "trial_quality_restricted"

    @patch("app.services.wallet.WalletService.get_or_create_wallet")
    def test_trial_exhausted_after_3_images(self, mock_get_wallet):
        """Trial user with 3 images used should be rejected."""
        from app.services.wallet import WalletService

        user = self._make_user()
        wallet = self._make_wallet(trial_images_used=3, total_loaded=0)
        mock_get_wallet.return_value = wallet

        can, source = WalletService.check_can_generate(
            user, "adult", "1k", 1, MagicMock()
        )
        assert can is False
        assert source == "trial_ended"

    @patch("app.services.wallet.WalletService.get_or_create_wallet")
    def test_trial_expired_days(self, mock_get_wallet):
        """Trial user with expired trial period should be rejected."""
        from app.services.wallet import WalletService

        user = self._make_user()
        wallet = self._make_wallet(
            trial_images_used=1,
            trial_expires_at=datetime.utcnow() - timedelta(days=1),
            total_loaded=0,
        )
        mock_get_wallet.return_value = wallet

        can, source = WalletService.check_can_generate(
            user, "adult", "1k", 1, MagicMock()
        )
        assert can is False
        assert source == "trial_ended"

    @patch("app.services.wallet.WalletService.get_or_create_wallet")
    def test_trial_2_of_3_used_allows_one_more(self, mock_get_wallet):
        """Trial user with 2 images used should allow 1 more."""
        from app.services.wallet import WalletService

        user = self._make_user()
        wallet = self._make_wallet(trial_images_used=2)
        mock_get_wallet.return_value = wallet

        can, source = WalletService.check_can_generate(
            user, "adult", "1k", 1, MagicMock()
        )
        assert can is True
        assert source == "trial"

    @patch("app.services.wallet.WalletService.get_or_create_wallet")
    def test_trial_fiton_still_works(self, mock_get_wallet):
        """Trial user should still get 1 free fiton image."""
        from app.services.wallet import WalletService

        user = self._make_user()
        wallet = self._make_wallet(trial_fiton_used=0)
        mock_get_wallet.return_value = wallet

        can, source = WalletService.check_can_generate(
            user, "fiton", "1k", 1, MagicMock()
        )
        assert can is True
        assert source == "trial"

    @patch("app.services.wallet.WalletService.get_or_create_wallet")
    def test_admin_bypasses_trial(self, mock_get_wallet):
        """Admin users should bypass all trial restrictions."""
        from app.services.wallet import WalletService

        user = self._make_user(role="admin")

        can, source = WalletService.check_can_generate(
            user, "adult", "4k", 5, MagicMock()
        )
        assert can is True
        assert source == "unrestricted"

    @patch("app.services.wallet.WalletService.get_or_create_wallet")
    def test_trial_ended_user_with_wallet_can_still_generate(self, mock_get_wallet):
        """User whose trial ended but has wallet balance should succeed via wallet."""
        from app.services.wallet import WalletService

        user = self._make_user()
        wallet = self._make_wallet(
            trial_images_used=3,
            balance_lkr=500,
            total_loaded=500,
        )
        mock_get_wallet.return_value = wallet

        can, source = WalletService.check_can_generate(
            user, "adult", "1k", 1, MagicMock()
        )
        assert can is True
        assert source == "wallet"
