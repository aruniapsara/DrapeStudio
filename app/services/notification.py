"""Multi-channel notification orchestrator.

Dispatches generation-complete notifications via:
  1. Web Push (if user has subscriptions)
  2. SMS via Notify.lk (if user opted in)
"""

import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.services.push_notification import push_notification_service
from app.services.sms import sms_service

logger = logging.getLogger(__name__)


class NotificationService:
    """Orchestrates notifications across push + SMS channels."""

    def notify_generation_complete(
        self,
        user,
        generation_id: str,
        module: str,
        db: Session,
    ) -> None:
        """
        Notify a user that their generation job finished.
        Silently swallows errors so the worker is never blocked.
        """
        if user is None:
            return

        user_id = getattr(user, "id", None)
        if not user_id:
            return

        # 1. Web Push
        try:
            sent = push_notification_service.send_generation_complete(
                user_id, generation_id, module, db
            )
            if sent:
                logger.info("Push notification sent (%d device(s)) for gen %s", sent, generation_id)
        except Exception as exc:
            logger.warning("Push notification failed for gen %s: %s", generation_id, exc)

        # 2. SMS (only if user opted in)
        if getattr(user, "sms_notifications_enabled", False):
            phone = getattr(user, "phone", None)
            if phone:
                try:
                    module_label = module.replace("_", " ").title()
                    message = (
                        f"DrapeStudio: Your {module_label} images are ready! "
                        f"View: {settings.BASE_URL}/results/{generation_id}"
                    )
                    sms_service.send(phone=phone, message=message)
                except Exception as exc:
                    logger.warning("SMS notification failed for gen %s: %s", generation_id, exc)


notification_service = NotificationService()
