"""SMS notification service via Notify.lk (Sri Lanka)."""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_NOTIFY_LK_URL = "https://app.notify.lk/api/v1/send"


class SMSService:
    """Send SMS messages via the Notify.lk API."""

    def send(self, phone: str, message: str) -> bool:
        """
        Send an SMS to a phone number.
        `phone` should be E.164 format, e.g. +94771234567.
        Returns True if the API accepted the request.
        """
        if not settings.NOTIFY_LK_USER_ID or not settings.NOTIFY_LK_API_KEY:
            logger.debug("Notify.lk credentials not configured — SMS skipped")
            return False

        # Notify.lk expects number without + prefix
        normalized = phone.lstrip("+")

        try:
            resp = httpx.post(
                _NOTIFY_LK_URL,
                data={
                    "user_id": settings.NOTIFY_LK_USER_ID,
                    "api_key": settings.NOTIFY_LK_API_KEY,
                    "sender_id": settings.NOTIFY_LK_SENDER_ID,
                    "to": normalized,
                    "message": message,
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                body = resp.json()
                if body.get("status") == "success":
                    logger.info("SMS sent to %s", phone)
                    return True
                logger.warning("Notify.lk rejected SMS: %s", body)
            else:
                logger.warning("Notify.lk HTTP %s: %s", resp.status_code, resp.text[:200])
        except Exception as exc:
            logger.error("SMS send error: %s", exc)

        return False


sms_service = SMSService()
