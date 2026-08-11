from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    def list_for_entry(self, queue_entry_id: uuid.UUID) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.queue_entry_id == queue_entry_id)
            .order_by(Notification.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())
