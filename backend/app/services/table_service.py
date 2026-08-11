"""TableService: CRUD de mesas e transicoes de status (unica porta para mudar status)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError, ValidationError
from app.models import (
    EventType,
    QueueStatus,
    Table,
    TableStatus,
    can_transition,
    utcnow,
)
from app.repositories import QueueRepository, TableRepository
from app.schemas.table import TableCreate, TableUpdate
from app.services.allocation_service import AllocationResult, TableAllocationService
from app.services.event_service import EventService

STATUS_EVENT = {
    TableStatus.OCCUPIED: EventType.TABLE_OCCUPIED,
    TableStatus.CLEANING: EventType.TABLE_CLEANING,
    TableStatus.AVAILABLE: EventType.TABLE_AVAILABLE,
}


class TableService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.tables = TableRepository(session)
        self.queue = QueueRepository(session)
        self.events = EventService(session)
        self.allocation = TableAllocationService(session)

    # ------------------------------------------------------------------ CRUD
    def list_tables(self, restaurant_id: uuid.UUID) -> list[Table]:
        return self.tables.list_by_restaurant(restaurant_id)

    def get_table(self, table_id: uuid.UUID, restaurant_id: uuid.UUID) -> Table:
        table = self.tables.get_scoped(table_id, restaurant_id)
        if table is None:
            raise NotFoundError("Mesa nao encontrada.")
        return table

    def create_table(self, restaurant_id: uuid.UUID, payload: TableCreate) -> Table:
        if self.tables.number_exists(restaurant_id, payload.number):
            raise ConflictError("Ja existe uma mesa com esse numero neste restaurante.")
        table = Table(
            restaurant_id=restaurant_id,
            number=payload.number,
            capacity=payload.capacity,
            pos_x=payload.pos_x,
            pos_y=payload.pos_y,
            status=TableStatus.AVAILABLE,
        )
        return self.tables.add(table)

    def update_table(
        self, table_id: uuid.UUID, restaurant_id: uuid.UUID, payload: TableUpdate
    ) -> Table:
        table = self.get_table(table_id, restaurant_id)
        data = payload.model_dump(exclude_unset=True)
        if not data:
            raise ValidationError("Nenhum campo para atualizar.")
        if "number" in data and self.tables.number_exists(
            restaurant_id, data["number"], exclude_id=table.id
        ):
            raise ConflictError("Ja existe uma mesa com esse numero neste restaurante.")
        for field, value in data.items():
            setattr(table, field, value)
        self.session.flush()
        return table

    # ----------------------------------------------------------- transicoes
    def _transition(
        self,
        table: Table,
        target: TableStatus,
        actor_user_id: uuid.UUID | None,
        metadata: dict[str, object] | None = None,
    ) -> Table:
        if not can_transition(table.status, target):
            raise ConflictError(
                f"Transicao invalida: {table.status.value} -> {target.value}.",
                details={"from": table.status.value, "to": target.value},
            )
        table.status = target
        self.session.flush()
        event_type = STATUS_EVENT.get(target)
        if event_type is not None:
            self.events.record(
                event_type=event_type,
                restaurant_id=table.restaurant_id,
                table_id=table.id,
                actor_user_id=actor_user_id,
                metadata=metadata or {"table_number": table.number},
            )
        return table

    def start_cleaning(
        self, table_id: uuid.UUID, restaurant_id: uuid.UUID, actor_user_id: uuid.UUID | None
    ) -> Table:
        table = self._lock(table_id, restaurant_id)
        return self._transition(table, TableStatus.CLEANING, actor_user_id)

    def release_table(
        self, table_id: uuid.UUID, restaurant_id: uuid.UUID, actor_user_id: uuid.UUID | None
    ) -> tuple[Table, AllocationResult | None]:
        """LIBERAR MESA em um clique.

        De OCCUPIED passa por CLEANING automaticamente (ambos os eventos sao gerados),
        de CLEANING vai direto para AVAILABLE. Em seguida a alocacao automatica roda
        na mesma transacao.
        """
        table = self._lock(table_id, restaurant_id)
        if table.status == TableStatus.OCCUPIED:
            self._transition(table, TableStatus.CLEANING, actor_user_id)
        if table.status != TableStatus.CLEANING:
            raise ConflictError(
                f"Transicao invalida: {table.status.value} -> {TableStatus.AVAILABLE.value}.",
                details={"from": table.status.value, "to": TableStatus.AVAILABLE.value},
            )
        self._transition(table, TableStatus.AVAILABLE, actor_user_id)
        allocation = self.allocation.allocate_for_table(table, actor_user_id)
        return table, allocation

    def occupy_table(
        self, table_id: uuid.UUID, restaurant_id: uuid.UUID, actor_user_id: uuid.UUID | None
    ) -> Table:
        """RESERVED -> OCCUPIED conclui o atendimento do grupo chamado (SEATED)."""
        table = self._lock(table_id, restaurant_id)
        was_reserved = table.status == TableStatus.RESERVED
        self._transition(table, TableStatus.OCCUPIED, actor_user_id)
        if was_reserved:
            self._seat_called_entry(table, actor_user_id)
        return table

    def allocate_manually(
        self, table_id: uuid.UUID, restaurant_id: uuid.UUID, actor_user_id: uuid.UUID | None
    ) -> AllocationResult | None:
        """Fallback manual quando a alocacao automatica nao encontrou grupo na hora."""
        table = self._lock(table_id, restaurant_id)
        if table.status != TableStatus.AVAILABLE:
            raise ConflictError(
                "Somente mesas AVAILABLE podem receber alocacao.",
                details={"status": table.status.value},
            )
        return self.allocation.allocate_for_table(table, actor_user_id)

    # ------------------------------------------------------------- internos
    def _lock(self, table_id: uuid.UUID, restaurant_id: uuid.UUID) -> Table:
        table = self.tables.get_for_update(table_id, restaurant_id)
        if table is None:
            raise NotFoundError("Mesa nao encontrada.")
        return table

    def _seat_called_entry(self, table: Table, actor_user_id: uuid.UUID | None) -> None:
        entries = [
            entry
            for entry in self.queue.list_by_restaurant(
                table.restaurant_id, statuses=(QueueStatus.CALLED,)
            )
            if entry.assigned_table_id == table.id
        ]
        if not entries:
            return
        entry = entries[0]
        entry.status = QueueStatus.SEATED
        entry.seated_at = utcnow()
        self.session.flush()
        self.events.record(
            event_type=EventType.CUSTOMER_SEATED,
            restaurant_id=table.restaurant_id,
            table_id=table.id,
            queue_entry_id=entry.id,
            actor_user_id=actor_user_id,
            metadata={"table_number": table.number, "party_size": entry.party_size},
        )
