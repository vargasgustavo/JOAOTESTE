"""EventService: toda acao relevante vira um TableEvent (auditoria + metricas)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import EventType, TableEvent
from app.repositories import EventRepository


class EventService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.events = EventRepository(session)

    def record(
        self,
        *,
        event_type: EventType,
        restaurant_id: uuid.UUID,
        table_id: uuid.UUID | None = None,
        queue_entry_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TableEvent:
        event = TableEvent(
            event_type=event_type,
            restaurant_id=restaurant_id,
            table_id=table_id,
            queue_entry_id=queue_entry_id,
            actor_user_id=actor_user_id,
            event_metadata=metadata or {},
        )
        return self.events.add(event)

    def list_recent(
        self, restaurant_id: uuid.UUID, limit: int = 50
    ) -> list[TableEvent]:
        return self.events.list_recent(restaurant_id, limit=limit)
