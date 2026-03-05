"""PayHere.lk payment gateway integration."""

import hashlib
import logging

from app.config import settings
from app.config.plans import PLANS
from app.models.db import generate_ulid

logger = logging.getLogger(__name__)


class PayHereService:
    """PayHere.lk payment gateway integration (sandbox + production)."""

    SANDBOX_URL = "https://sandbox.payhere.lk/pay/checkout"
    PRODUCTION_URL = "https://www.payhere.lk/pay/checkout"

    @property
    def checkout_url(self) -> str:
        return self.SANDBOX_URL if settings.PAYHERE_SANDBOX else self.PRODUCTION_URL

    def create_checkout(self, user, plan_key: str) -> dict:
        """Generate PayHere checkout form data with MD5 hash."""
        plan = PLANS[plan_key]
        order_id = generate_ulid()
        amount = float(plan["price_lkr"])

        # PayHere hash: MD5(merchant_id + order_id + amount + currency + merchant_secret).upper()
        hash_str = (
            f"{settings.PAYHERE_MERCHANT_ID}"
            f"{order_id}"
            f"{amount:.2f}"
            "LKR"
            f"{settings.PAYHERE_MERCHANT_SECRET}"
        )
        hash_value = hashlib.md5(hash_str.encode()).hexdigest().upper()

        # Determine user fields
        phone = getattr(user, "phone", "") or ""
        name = getattr(user, "display_name", "") or ""
        first_name = name.split()[0] if name else "User"
        last_name = " ".join(name.split()[1:]) if len(name.split()) > 1 else ""
        email = getattr(user, "email", "") or ""

        return {
            "merchant_id": settings.PAYHERE_MERCHANT_ID,
            "return_url": f"{settings.BASE_URL}/billing/success",
            "cancel_url": f"{settings.BASE_URL}/billing/cancel",
            "notify_url": f"{settings.BASE_URL}/api/v1/billing/payhere-notify",
            "order_id": order_id,
            "items": f"DrapeStudio {plan['name']} Plan",
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
            # Recurring subscription fields
            "recurrence": "1 Month",
            "duration": "Forever",
            # Meta — used by success/cancel pages
            "_plan_key": plan_key,
            "_checkout_url": self.checkout_url,
        }

    def verify_notification(self, params: dict) -> bool:
        """
        Verify PayHere server-to-server notification is authentic.

        PayHere sends: merchant_id, order_id, payhere_amount, payhere_currency,
                       status_code, md5sig
        Verification: MD5(merchant_id + order_id + amount + currency +
                          status_code + MD5(merchant_secret).upper()).upper()
        """
        merchant_id = params.get("merchant_id", "")
        order_id = params.get("order_id", "")
        amount = params.get("payhere_amount", "")
        currency = params.get("payhere_currency", "")
        status_code = params.get("status_code", "")
        md5sig = params.get("md5sig", "")

        if not md5sig:
            return False

        # Inner hash: MD5 of merchant secret (upper-case)
        secret_hash = hashlib.md5(
            settings.PAYHERE_MERCHANT_SECRET.encode()
        ).hexdigest().upper()

        local_md5 = hashlib.md5(
            f"{merchant_id}{order_id}{amount}{currency}{status_code}{secret_hash}".encode()
        ).hexdigest().upper()

        return local_md5 == md5sig.upper()


payhere_service = PayHereService()
