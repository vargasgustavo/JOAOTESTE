from datetime import datetime, timezone

from flask import current_app

from ..models import Table, TableStatus, QueueEntry, QueueStatus
from ..repositories import TableRepository, QueueRepository, RestaurantRepository
from ..extensions import db
from .event_service import EventService, EVENT_TABLE_AVAILABLE, EVENT_TABLE_RESERVED, EVENT_CUSTOMER_ASSIGNED, EVENT_CUSTOMER_CALLED
from .notifications.notification_service import NotificationService
from ..tasks.notification_tasks import send_queue_called_task


class TableAllocationService:
    """Core allocation logic: FIFO, party size matching, SELECT FOR UPDATE SKIP LOCKED."""

    def __init__(self, session=None):
        self._table_repo = TableRepository(session)
        self._queue_repo = QueueRepository(session)
        self._restaurant_repo = RestaurantRepository(session)
        self._event_service = EventService(session)

    def try_allocate_for_table(self, table: Table) -> QueueEntry | None:
        """
        Called when a table becomes AVAILABLE.
        Finds the first WAITING entry whose party_size <= table.capacity.
        Returns the allocated QueueEntry or None.
        """
        waiting_entries = self._queue_repo.get_waiting_for_restaurant(table.restaurant_id)

        for entry in waiting_entries:
            if entry.party_size <= table.capacity:
                now = datetime.now(timezone.utc)

                entry.status = QueueStatus.CALLED
                entry.called_at = now
                entry.assigned_table_id = table.id

                table.status = TableStatus.RESERVED

                self._event_service.emit(
                    table.id,
                    EVENT_CUSTOMER_ASSIGNED,
                    {"queue_entry_id": entry.id, "customer_name": entry.customer_name},
                )
                self._event_service.emit(
                    table.id,
                    EVENT_CUSTOMER_CALLED,
                    {"queue_entry_id": entry.id},
                )

                restaurant = self._restaurant_repo.get_by_id(table.restaurant_id)
                restaurant_name = restaurant.name if restaurant else "restaurante"

                send_queue_called_task.delay(
                    queue_entry_id=entry.id,
                    customer_name=entry.customer_name,
                    customer_phone=entry.customer_phone,
                    restaurant_name=restaurant_name,
                )

                return entry

        return None

    def try_allocate_for_new_entry(self, entry: QueueEntry) -> Table | None:
        """
        Called when a new customer joins the queue.
        Checks for any compatible AVAILABLE table.
        """
        available_tables = self._table_repo.get_available_for_restaurant(entry.restaurant_id)
        for table in available_tables:
            if table.capacity >= entry.party_size:
                result = self.try_allocate_for_table(table)
                if result:
                    return table
        return None
