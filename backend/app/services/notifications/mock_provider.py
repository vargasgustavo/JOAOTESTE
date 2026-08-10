import logging

from .base_provider import NotificationProvider

logger = logging.getLogger(__name__)


class MockProvider(NotificationProvider):
    """Logs notifications to stdout. Replace with WhatsApp/SMS provider in production."""

    def send(self, recipient_phone: str, message: str) -> bool:
        masked = "****" + recipient_phone[-4:] if len(recipient_phone) >= 4 else "****"
        logger.info("[MockNotification] To: %s | Message: %s", masked, message)
        return True
