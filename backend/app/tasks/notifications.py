"""Tasks assincronas de notificacao (retry com backoff, sem PII nos logs)."""

from __future__ import annotations

import logging
import uuid

from flask import current_app

from app.extensions import db
from app.services.notification_service import NotificationService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="notifications.send",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_notification_task(self, notification_id: str, table_number: str = "") -> str:  # noqa: ANN001, ARG001
    session = db.s
    try:
        service = NotificationService(session)
        notification = service.deliver(
            uuid.UUID(notification_id), current_app.config["NOTIFICATION_PROVIDER"]
        )
        session.commit()
        logger.info(
            "Notificacao %s finalizada com status %s (mesa %s).",
            notification_id,
            notification.status.value,
            table_number or "-",
        )
        return notification.status.value
    except Exception:
        session.rollback()
        raise
