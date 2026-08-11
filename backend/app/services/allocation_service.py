"""TableAllocationService: o cerebro do V0.

Regra: ao surgir uma mesa AVAILABLE, o primeiro grupo WAITING (FIFO) cujo
party_size cabe na capacidade e chamado. Ao entrar um grupo novo, procura-se a
menor mesa AVAILABLE que o comporte.

Concorrencia: tudo roda dentro da transacao do caso de uso; as linhas de mesa e
de fila sao travadas com SELECT ... FOR UPDATE (SKIP LOCKED no PostgreSQL), o que
impede que duas liberacoes simultaneas chamem o mesmo cliente ou ocupem a mesma mesa.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.extensions import db
from app.models import (
    EventType,
    QueueEntry,
    QueueStatus,
    Restaurant,
    Table,
    TableStatus,
    utcnow,
)
from app.repositories import QueueRepository, RestaurantRepository, TableRepository
from app.services.event_service import EventService
from app.services.notification_service import NotificationService


@dataclass(frozen=True, slots=True)
class AllocationResult:
    queue_entry_id: uuid.UUID
    customer_name: str
    party_size: int
    table_id: uuid.UUID
    table_number: str


class TableAllocationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.tables = TableRepository(session)
        self.queue = QueueRepository(session)
        self.restaurants = RestaurantRepository(session)
        self.events = EventService(session)
        self.notifications = NotificationService(session)

    @property
    def _skip_locked(self) -> bool:
        return db.supports_skip_locked

    def allocate_for_table(
        self, table: Table, actor_user_id: uuid.UUID | None = None
    ) -> AllocationResult | None:
        """Chamado logo apos uma mesa virar AVAILABLE."""
        if table.status != TableStatus.AVAILABLE:
            return None
        entry = self.queue.lock_first_compatible(
            table.restaurant_id, table.capacity, self._skip_locked
        )
        if entry is None:
            return None
        return self._assign(entry, table, actor_user_id)

    def allocate_for_entry(
        self, entry: QueueEntry, actor_user_id: uuid.UUID | None = None
    ) -> AllocationResult | None:
        """Chamado quando um cliente entra na fila e ja existe mesa livre compativel."""
        if entry.status != QueueStatus.WAITING:
            return None
        table = self.tables.find_available_for_party(
            entry.restaurant_id, entry.party_size, self._skip_locked
        )
        if table is None:
            return None
        return self._assign(entry, table, actor_user_id)

    def _assign(
        self, entry: QueueEntry, table: Table, actor_user_id: uuid.UUID | None
    ) -> AllocationResult:
        now = utcnow()
        entry.status = QueueStatus.CALLED
        entry.called_at = now
        entry.assigned_table_id = table.id
        table.status = TableStatus.RESERVED
        self.session.flush()

        metadata = {
            "table_number": table.number,
            "party_size": entry.party_size,
            "capacity": table.capacity,
        }
        for event_type in (EventType.CUSTOMER_ASSIGNED, EventType.CUSTOMER_CALLED):
            self.events.record(
                event_type=event_type,
                restaurant_id=table.restaurant_id,
                table_id=table.id,
                queue_entry_id=entry.id,
                actor_user_id=actor_user_id,
                metadata=metadata,
            )

        restaurant = self._restaurant(table.restaurant_id)
        self.notifications.queue_table_ready(entry, table, restaurant)

        return AllocationResult(
            queue_entry_id=entry.id,
            customer_name=entry.customer_name,
            party_size=entry.party_size,
            table_id=table.id,
            table_number=table.number,
        )

    def _restaurant(self, restaurant_id: uuid.UUID) -> Restaurant:
        restaurant = self.restaurants.get(restaurant_id)
        if restaurant is None:  # pragma: no cover - FK garante existencia
            raise ValueError("Restaurante inexistente para alocacao.")
        return restaurant
