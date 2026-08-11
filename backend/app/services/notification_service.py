"""NotificationService: persiste a notificacao e delega o envio ao Celery (assincrono)."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.models import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    QueueEntry,
    Restaurant,
    Table,
    utcnow,
)
from app.repositories import NotificationRepository
from app.services.providers import get_provider
from app.services.unit_of_work import after_commit

logger = logging.getLogger(__name__)

TABLE_READY_TEMPLATE = "Ola, {name}! Sua mesa esta pronta no {restaurant}. Dirija-se a recepcao."


def build_table_ready_message(customer_name: str, restaurant_name: str) -> str:
    first_name = (customer_name or "").strip().split(" ")[0] or "cliente"
    return TABLE_READY_TEMPLATE.format(name=first_name, restaurant=restaurant_name)


class NotificationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.notifications = NotificationRepository(session)

    def queue_table_ready(
        self,
        entry: QueueEntry,
        table: Table,
        restaurant: Restaurant,
        channel: NotificationChannel = NotificationChannel.WHATSAPP,
    ) -> Notification:
        """Cria a notificacao PENDING na mesma transacao e enfileira apos o commit."""
        notification = Notification(
            queue_entry_id=entry.id,
            channel=channel,
            message=build_table_ready_message(entry.customer_name, restaurant.name),
            status=NotificationStatus.PENDING,
        )
        self.notifications.add(notification)
        notification_id = notification.id
        table_number = table.number
        after_commit(lambda: dispatch_notification(notification_id, table_number))
        return notification

    def deliver(self, notification_id: uuid.UUID, provider_name: str = "mock") -> Notification:
        """Executado pelo worker Celery: envia e registra o resultado."""
        notification = self.notifications.get(notification_id)
        if notification is None:
            raise ValueError("Notificacao inexistente.")
        if notification.status == NotificationStatus.SENT:
            return notification

        entry = notification.queue_entry
        provider = get_provider(provider_name)
        sender = {
            NotificationChannel.WHATSAPP: provider.send_whatsapp,
            NotificationChannel.SMS: provider.send_sms,
            NotificationChannel.WEB: provider.send_web_notification,
        }[notification.channel]

        result = sender(entry.customer_phone, notification.message)
        if result.success:
            notification.status = NotificationStatus.SENT
            notification.sent_at = utcnow()
            notification.provider_message_id = result.provider_message_id
            notification.error = None
        else:
            notification.status = NotificationStatus.FAILED
            notification.error = (result.error or "erro desconhecido")[:500]
        self.session.flush()
        return notification


def dispatch_notification(notification_id: uuid.UUID, table_number: str) -> None:
    """Enfileira no Celery; se o broker estiver fora, registra e segue (nao quebra o fluxo)."""
    from app.tasks.notifications import send_notification_task

    try:
        send_notification_task.delay(str(notification_id), table_number)
    except Exception:  # pragma: no cover - broker indisponivel
        logger.exception("Falha ao enfileirar notificacao %s.", notification_id)
