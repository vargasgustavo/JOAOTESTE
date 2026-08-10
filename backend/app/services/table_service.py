from flask import abort

from ..models import Table, TableStatus, VALID_TRANSITIONS
from ..repositories import TableRepository
from ..extensions import db
from .event_service import (
    EventService,
    EVENT_TABLE_AVAILABLE, EVENT_TABLE_CLEANING, EVENT_TABLE_OCCUPIED, EVENT_TABLE_RESERVED,
    EVENT_CUSTOMER_SEATED,
)
from .table_allocation_service import TableAllocationService


STATUS_TO_EVENT = {
    TableStatus.AVAILABLE: EVENT_TABLE_AVAILABLE,
    TableStatus.CLEANING: EVENT_TABLE_CLEANING,
    TableStatus.OCCUPIED: EVENT_TABLE_OCCUPIED,
    TableStatus.RESERVED: EVENT_TABLE_RESERVED,
}


class TableService:
    def __init__(self):
        self._repo = TableRepository()

    def list_tables(self, restaurant_id: str) -> list[Table]:
        return self._repo.list_by_restaurant(restaurant_id)

    def get_table(self, table_id: str) -> Table:
        table = self._repo.get_by_id(table_id)
        if not table:
            abort(404, "Table not found")
        return table

    def create_table(self, restaurant_id: str, **kwargs) -> Table:
        with db.session.begin():
            table = self._repo.create(restaurant_id=restaurant_id, **kwargs)
        return table

    def update_table(self, table_id: str, **kwargs) -> Table:
        table = self.get_table(table_id)
        with db.session.begin():
            self._repo.update(table, **kwargs)
        return table

    def _transition(self, table_id: str, new_status: TableStatus) -> Table:
        with db.session.begin():
            table = self._repo.get_by_id(table_id)
            if not table:
                abort(404, "Table not found")
            if not table.can_transition_to(new_status):
                abort(409, f"Invalid transition: {table.status} → {new_status}")

            table.status = new_status

            event_type = STATUS_TO_EVENT.get(new_status)
            if event_type:
                event_svc = EventService()
                event_svc.emit(table.id, event_type)

            if new_status == TableStatus.AVAILABLE:
                alloc_svc = TableAllocationService()
                alloc_svc.try_allocate_for_table(table)

        return table

    def release_table(self, table_id: str) -> Table:
        """OCCUPIED → CLEANING (triggers allocation after full cycle)."""
        return self._transition(table_id, TableStatus.CLEANING)

    def mark_cleaning_done(self, table_id: str) -> Table:
        """CLEANING → AVAILABLE (triggers allocation)."""
        return self._transition(table_id, TableStatus.AVAILABLE)

    def occupy_table(self, table_id: str) -> Table:
        """RESERVED → OCCUPIED."""
        with db.session.begin():
            table = self._repo.get_by_id(table_id)
            if not table:
                abort(404, "Table not found")
            if not table.can_transition_to(TableStatus.OCCUPIED):
                abort(409, f"Invalid transition: {table.status} → OCCUPIED")
            table.status = TableStatus.OCCUPIED
            event_svc = EventService()
            event_svc.emit(table.id, EVENT_TABLE_OCCUPIED)
            event_svc.emit(table.id, EVENT_CUSTOMER_SEATED)
        return table
