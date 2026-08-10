from sqlalchemy import select, func, case
from ..models import Table, TableStatus, QueueEntry, QueueStatus
from ..repositories import RestaurantRepository
from ..extensions import db
from .wait_time_service import WaitTimeService


class DashboardService:
    def __init__(self):
        self._restaurant_repo = RestaurantRepository()
        self._wait_svc = WaitTimeService()

    def get_dashboard(self, restaurant_id: str) -> dict:
        restaurant = self._restaurant_repo.get_by_id(restaurant_id)
        if not restaurant:
            return None

        total = db.session.execute(
            select(func.count(Table.id)).where(Table.restaurant_id == restaurant_id)
        ).scalar_one() or 0

        occupied = db.session.execute(
            select(func.count(Table.id)).where(
                Table.restaurant_id == restaurant_id,
                Table.status == TableStatus.OCCUPIED,
            )
        ).scalar_one() or 0

        cleaning = db.session.execute(
            select(func.count(Table.id)).where(
                Table.restaurant_id == restaurant_id,
                Table.status == TableStatus.CLEANING,
            )
        ).scalar_one() or 0

        available = db.session.execute(
            select(func.count(Table.id)).where(
                Table.restaurant_id == restaurant_id,
                Table.status == TableStatus.AVAILABLE,
            )
        ).scalar_one() or 0

        reserved = db.session.execute(
            select(func.count(Table.id)).where(
                Table.restaurant_id == restaurant_id,
                Table.status == TableStatus.RESERVED,
            )
        ).scalar_one() or 0

        queue_count = db.session.execute(
            select(func.count(QueueEntry.id)).where(
                QueueEntry.restaurant_id == restaurant_id,
                QueueEntry.status == QueueStatus.WAITING,
            )
        ).scalar_one() or 0

        avg_wait = self._wait_svc.estimate_wait(1)

        return {
            "restaurant_id": restaurant_id,
            "restaurant_name": restaurant.name,
            "total_tables": total,
            "occupied_tables": occupied,
            "cleaning_tables": cleaning,
            "available_tables": available,
            "reserved_tables": reserved,
            "queue_count": queue_count,
            "avg_wait_minutes": avg_wait,
        }
