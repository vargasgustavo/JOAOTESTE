from flask import abort

from ..models import QueueEntry, QueueStatus
from ..repositories import QueueRepository, RestaurantRepository
from ..extensions import db
from .wait_time_service import WaitTimeService
from .table_allocation_service import TableAllocationService


class QueueService:
    def __init__(self):
        self._repo = QueueRepository()
        self._restaurant_repo = RestaurantRepository()
        self._wait_svc = WaitTimeService()

    def list_queue(self, restaurant_id: str, status: str | None = None) -> list[dict]:
        entries = self._repo.list_by_restaurant(restaurant_id, status)
        result = []
        position = 0
        for entry in entries:
            if entry.status == QueueStatus.WAITING:
                position += 1
                estimated = self._wait_svc.estimate_wait(position)
            else:
                estimated = None
            result.append({"entry": entry, "position": position if entry.status == QueueStatus.WAITING else None, "estimated_wait": estimated})
        return result

    def get_entry(self, entry_id: str, restaurant_id: str | None = None) -> dict:
        entry = self._repo.get_by_id(entry_id)
        if not entry:
            abort(404, "Queue entry not found")
        if restaurant_id and entry.restaurant_id != restaurant_id:
            abort(403, "Access denied")
        position = None
        estimated = None
        if entry.status == QueueStatus.WAITING:
            position = self._repo.get_position(entry.restaurant_id, entry_id)
            estimated = self._wait_svc.estimate_wait(position)
        return {"entry": entry, "position": position, "estimated_wait": estimated}

    def join_queue(self, restaurant_id: str, customer_name: str, customer_phone: str,
                   party_size: int, customer_id: str | None = None) -> dict:
        restaurant = self._restaurant_repo.get_by_id(restaurant_id)
        if not restaurant or not restaurant.is_active:
            abort(404, "Restaurant not found or inactive")

        with db.session.begin():
            entry = self._repo.create(
                restaurant_id=restaurant_id,
                customer_id=customer_id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                party_size=party_size,
                status=QueueStatus.WAITING,
            )
            db.session.flush()

            alloc_svc = TableAllocationService()
            alloc_svc.try_allocate_for_new_entry(entry)

        position = None
        estimated = None
        if entry.status == QueueStatus.WAITING:
            position = self._repo.get_position(restaurant_id, entry.id)
            estimated = self._wait_svc.estimate_wait(position)

        return {"entry": entry, "position": position, "estimated_wait": estimated}

    def cancel_entry(self, entry_id: str, requesting_user_id: str | None = None,
                     restaurant_id: str | None = None) -> QueueEntry:
        entry = self._repo.get_by_id(entry_id)
        if not entry:
            abort(404, "Queue entry not found")
        if restaurant_id and entry.restaurant_id != restaurant_id:
            abort(403, "Access denied")
        if requesting_user_id and entry.customer_id and entry.customer_id != requesting_user_id:
            abort(403, "Access denied")
        if entry.status not in (QueueStatus.WAITING, QueueStatus.CALLED):
            abort(409, "Cannot cancel entry in current status")

        from datetime import datetime, timezone
        with db.session.begin():
            entry.status = QueueStatus.CANCELLED
            entry.cancelled_at = datetime.now(timezone.utc)
        return entry
