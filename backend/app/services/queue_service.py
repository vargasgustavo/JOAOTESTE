"""QueueService: entrada, consulta e cancelamento na fila."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError, ValidationError
from app.models import (
    EventType,
    QueueEntry,
    QueueStatus,
    Table,
    TableStatus,
    can_transition,
    utcnow,
)
from app.repositories import QueueRepository, RestaurantRepository, TableRepository
from app.schemas.queue import QueueJoinRequest
from app.services.allocation_service import AllocationResult, TableAllocationService
from app.services.event_service import EventService
from app.services.wait_time_service import WaitTimeService

MAX_OPEN_ENTRIES_PER_RESTAURANT = 500


@dataclass(frozen=True, slots=True)
class QueueEntryView:
    entry: QueueEntry
    position: int | None
    estimated_wait_minutes: int | None
    table_number: str | None


class QueueService:
    def __init__(self, session: Session, wait_time: WaitTimeService) -> None:
        self.session = session
        self.queue = QueueRepository(session)
        self.tables = TableRepository(session)
        self.restaurants = RestaurantRepository(session)
        self.events = EventService(session)
        self.allocation = TableAllocationService(session)
        self.wait_time = wait_time

    # --------------------------------------------------------------- entrada
    def join(
        self,
        restaurant_id: uuid.UUID,
        payload: QueueJoinRequest,
        user_id: uuid.UUID | None = None,
    ) -> tuple[QueueEntry, AllocationResult | None]:
        restaurant = self.restaurants.get(restaurant_id)
        if restaurant is None or not restaurant.is_active:
            raise NotFoundError("Restaurante nao encontrado.")
        if self.queue.has_open_entry_for_phone(restaurant_id, payload.customer_phone):
            raise ConflictError("Ja existe uma entrada ativa na fila para este telefone.")
        if self.queue.waiting_count(restaurant_id) >= MAX_OPEN_ENTRIES_PER_RESTAURANT:
            raise ConflictError("Fila cheia. Tente novamente mais tarde.")

        entry = QueueEntry(
            restaurant_id=restaurant_id,
            user_id=user_id,
            customer_name=payload.customer_name,
            customer_phone=payload.customer_phone,
            party_size=payload.party_size,
            status=QueueStatus.WAITING,
            position=self.queue.next_position(restaurant_id),
            joined_at=utcnow(),
        )
        self.queue.add(entry)
        allocation = self.allocation.allocate_for_entry(entry)
        return entry, allocation

    # -------------------------------------------------------------- consulta
    def list_entries(
        self, restaurant_id: uuid.UUID, statuses: tuple[QueueStatus, ...] | None = None
    ) -> list[QueueEntryView]:
        entries = self.queue.list_by_restaurant(restaurant_id, statuses)
        turnover = self.wait_time.average_turnover_minutes(restaurant_id)
        table_numbers = {
            table.id: table.number for table in self.tables.list_by_restaurant(restaurant_id)
        }
        views: list[QueueEntryView] = []
        waiting_seen = 0
        for entry in entries:
            position: int | None = None
            estimate: int | None = None
            if entry.status == QueueStatus.WAITING:
                waiting_seen += 1
                position = waiting_seen
                estimate = position * turnover
            views.append(
                QueueEntryView(
                    entry=entry,
                    position=position,
                    estimated_wait_minutes=estimate,
                    table_number=table_numbers.get(entry.assigned_table_id or uuid.uuid4()),
                )
            )
        return views

    def get_entry_view(self, entry_id: uuid.UUID) -> QueueEntryView:
        entry = self.queue.get(entry_id)
        if entry is None:
            raise NotFoundError("Entrada da fila nao encontrada.")
        position = self.queue.position_of(entry)
        estimate = self.wait_time.estimate_for_position(entry.restaurant_id, position)
        table_number = None
        if entry.assigned_table_id is not None:
            table = self.tables.get(entry.assigned_table_id)
            table_number = table.number if table else None
        return QueueEntryView(
            entry=entry,
            position=position,
            estimated_wait_minutes=estimate,
            table_number=table_number,
        )

    # ---------------------------------------------------------- cancelamento
    def cancel(
        self, entry_id: uuid.UUID, actor_user_id: uuid.UUID | None = None
    ) -> tuple[QueueEntry, AllocationResult | None]:
        entry = self.queue.get_for_update(entry_id)
        if entry is None:
            raise NotFoundError("Entrada da fila nao encontrada.")
        if entry.status in (QueueStatus.CANCELLED, QueueStatus.EXPIRED):
            raise ConflictError("Esta entrada ja foi encerrada.")
        if entry.status == QueueStatus.SEATED:
            raise ConflictError("Cliente ja foi sentado; nao e possivel cancelar.")

        previous_status = entry.status
        entry.status = QueueStatus.CANCELLED
        entry.cancelled_at = utcnow()
        released_table: Table | None = None
        if previous_status == QueueStatus.CALLED and entry.assigned_table_id is not None:
            released_table = self._release_reserved_table(entry, actor_user_id)
        entry.assigned_table_id = None
        self.session.flush()

        reallocation = None
        if released_table is not None:
            reallocation = self.allocation.allocate_for_table(released_table, actor_user_id)
        return entry, reallocation

    def _release_reserved_table(
        self, entry: QueueEntry, actor_user_id: uuid.UUID | None
    ) -> Table | None:
        table = self.tables.get_for_update(entry.assigned_table_id, entry.restaurant_id)  # type: ignore[arg-type]
        if table is None or table.status != TableStatus.RESERVED:
            return None
        if not can_transition(table.status, TableStatus.AVAILABLE):  # pragma: no cover
            raise ValidationError("Nao foi possivel liberar a mesa reservada.")
        table.status = TableStatus.AVAILABLE
        self.session.flush()
        self.events.record(
            event_type=EventType.TABLE_AVAILABLE,
            restaurant_id=table.restaurant_id,
            table_id=table.id,
            queue_entry_id=entry.id,
            actor_user_id=actor_user_id,
            metadata={"reason": "queue_entry_cancelled", "table_number": table.number},
        )
        return table
