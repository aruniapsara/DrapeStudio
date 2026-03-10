"""Web Push notification service using pywebpush + VAPID."""

import json
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models.db import PushSubscription, generate_ulid

logger = logging.getLogger(__name__)


class PushNotificationService:
    """Send Web Push notifications to subscribed users."""

    def send_generation_complete(
        self, user_id: str, generation_id: str, module: str, db: Session
    ) -> int:
        """
        Send push notification to all of a user's registered devices.
        Returns count of notifications successfully sent.
        """
        if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
            logger.debug("VAPID keys not configured — skipping push notification")
            return 0

        subscriptions = self._get_user_subscriptions(user_id, db)
        if not subscriptions:
            return 0

        module_label = module.replace("_", " ").title()
        payload = json.dumps({
            "title": "Your images are ready! 🎉",
            "body": f"Your {module_label} generation is complete. Tap to view.",
            "url": f"/results/{generation_id}",
        })

        sent = 0
        dead_endpoints: list[str] = []

        for sub in subscriptions:
            try:
                from pywebpush import webpush, WebPushException
                webpush(
                    subscription_info={
                        "endpoint": sub.endpoint,
                        "keys": {
                            "p256dh": sub.keys_p256dh,
                            "auth": sub.keys_auth,
                        },
                    },
                    data=payload,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": f"mailto:{settings.VAPID_EMAIL}"},
                )
                sent += 1
            except Exception as exc:
                err_str = str(exc)
                if "410" in err_str or "404" in err_str:
                    # Subscription expired/unsubscribed — remove it
                    dead_endpoints.append(sub.endpoint)
                else:
                    logger.warning("Push send failed for sub %s: %s", sub.id, exc)

        # Clean up dead subscriptions
        if dead_endpoints:
            db.query(PushSubscription).filter(
                PushSubscription.endpoint.in_(dead_endpoints)
            ).delete(synchronize_session=False)
            db.commit()

        return sent

    def save_subscription(self, user_id: str, subscription: dict, db: Session) -> PushSubscription:
        """
        Store or update a push subscription for a user device.
        `subscription` matches the Web Push API subscription JSON shape:
        {endpoint, keys: {p256dh, auth}}.
        """
        endpoint = subscription.get("endpoint", "")
        keys = subscription.get("keys", {})
        p256dh = keys.get("p256dh", "")
        auth = keys.get("auth", "")

        existing = db.query(PushSubscription).filter_by(endpoint=endpoint).first()
        if existing:
            existing.keys_p256dh = p256dh
            existing.keys_auth = auth
            db.commit()
            db.refresh(existing)
            return existing

        sub = PushSubscription(
            id=generate_ulid(),
            user_id=user_id,
            endpoint=endpoint,
            keys_p256dh=p256dh,
            keys_auth=auth,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        return sub

    def delete_subscription(self, user_id: str, endpoint: str, db: Session) -> bool:
        """Remove a push subscription (user unsubscribed on this device)."""
        deleted = (
            db.query(PushSubscription)
            .filter_by(user_id=user_id, endpoint=endpoint)
            .delete()
        )
        db.commit()
        return deleted > 0

    def _get_user_subscriptions(self, user_id: str, db: Session) -> list[PushSubscription]:
        return db.query(PushSubscription).filter_by(user_id=user_id).all()


push_notification_service = PushNotificationService()
