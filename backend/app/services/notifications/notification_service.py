from datetime import datetime, timezone

from ...extensions import db
from ...repositories import NotificationRepository
from .base_provider import NotificationProvider
from .mock_provider import MockProvider


class NotificationService:
    def __init__(self, provider: NotificationProvider | None = None, session=None):
        self._provider = provider or MockProvider()
        self._repo = NotificationRepository(session)

    def send_queue_called(self, queue_entry, restaurant_name: str) -> None:
        message = (
            f"Olá, {queue_entry.customer_name}! "
            f"Sua mesa está pronta no {restaurant_name}. "
            "Dirija-se à recepção."
        )
        success = self._provider.send(queue_entry.customer_phone, message)
        status = "SENT" if success else "FAILED"
        notif = self._repo.create(
            queue_entry_id=queue_entry.id,
            channel=self._provider.__class__.__name__.lower().replace("provider", ""),
            message=message,
            status=status,
            sent_at=datetime.now(timezone.utc) if success else None,
        )
        db.session.add(notif)

    def send(self, queue_entry_id: str, phone: str, message: str, channel: str = "mock") -> None:
        success = self._provider.send(phone, message)
        status = "SENT" if success else "FAILED"
        notif = self._repo.create(
            queue_entry_id=queue_entry_id,
            channel=channel,
            message=message,
            status=status,
            sent_at=datetime.now(timezone.utc) if success else None,
        )
        db.session.add(notif)
