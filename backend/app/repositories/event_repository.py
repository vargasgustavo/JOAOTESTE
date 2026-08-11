from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models import EventType, TableEvent
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[TableEvent]):
    model = TableEvent

    def list_recent(
        self,
        restaurant_id: uuid.UUID,
        event_types: tuple[EventType, ...] | None = None,
        limit: int = 100,
    ) -> list[TableEvent]:
        stmt = select(TableEvent).where(TableEvent.restaurant_id == restaurant_id)
        if event_types:
            stmt = stmt.where(TableEvent.event_type.in_(event_types))
        stmt = stmt.order_by(TableEvent.timestamp.desc()).limit(limit)
        return list(self.session.execute(stmt).scalars().all())
