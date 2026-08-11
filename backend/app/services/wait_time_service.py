"""WaitTimeService: estimativa isolada, baseada no giro real das mesas."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EventType, TableEvent, utcnow


class WaitTimeService:
    """Tempo medio de giro = intervalo TABLE_AVAILABLE -> TABLE_OCCUPIED da mesma mesa."""

    def __init__(
        self,
        session: Session,
        *,
        default_wait_minutes: int = 15,
        sample_hours: int = 24,
        sample_size: int = 50,
    ) -> None:
        self.session = session
        self.default_wait_minutes = default_wait_minutes
        self.sample_hours = sample_hours
        self.sample_size = sample_size

    def average_turnover_minutes(self, restaurant_id: uuid.UUID) -> int:
        since = utcnow() - timedelta(hours=self.sample_hours)
        # func.lag() nao herda o tipo da coluna: sem type_ explicito o SQLite devolve
        # a string crua em vez de datetime/enum.
        prev_ts = func.lag(TableEvent.timestamp, type_=TableEvent.timestamp.type).over(
            partition_by=TableEvent.table_id, order_by=TableEvent.timestamp
        )
        prev_type = func.lag(TableEvent.event_type, type_=TableEvent.event_type.type).over(
            partition_by=TableEvent.table_id, order_by=TableEvent.timestamp
        )
        paired = (
            select(
                TableEvent.timestamp.label("occupied_at"),
                prev_ts.label("available_at"),
                prev_type.label("previous_type"),
                TableEvent.event_type.label("event_type"),
            )
            .where(
                TableEvent.restaurant_id == restaurant_id,
                TableEvent.event_type.in_(
                    (EventType.TABLE_AVAILABLE, EventType.TABLE_OCCUPIED)
                ),
                TableEvent.timestamp >= since,
            )
            .subquery()
        )
        stmt = (
            select(paired.c.occupied_at, paired.c.available_at)
            .where(
                paired.c.event_type == EventType.TABLE_OCCUPIED,
                paired.c.previous_type == EventType.TABLE_AVAILABLE,
                paired.c.available_at.is_not(None),
            )
            .order_by(paired.c.occupied_at.desc())
            .limit(self.sample_size)
        )
        rows = self.session.execute(stmt).all()
        durations = [
            (occupied_at - available_at).total_seconds() / 60
            for occupied_at, available_at in rows
            if occupied_at and available_at and occupied_at > available_at
        ]
        if not durations:
            return self.default_wait_minutes
        return max(1, round(sum(durations) / len(durations)))

    def estimate_for_position(self, restaurant_id: uuid.UUID, position: int | None) -> int | None:
        """Estimativa V0: posicao na fila x tempo medio de giro."""
        if position is None or position < 1:
            return None
        return position * self.average_turnover_minutes(restaurant_id)
