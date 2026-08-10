from sqlalchemy import case, func, select

from ..extensions import db
from ..models import QueueEntry, QueueStatus, Table, TableStatus
from ..repositories import RestaurantRepository
from .wait_time_service import WaitTimeService


class DashboardService:
    def __init__(self):
        self._restaurant_repo = RestaurantRepository()
        self._wait_svc = WaitTimeService()

    def get_dashboard(self, restaurant_id: str) -> dict:
        restaurant = self._restaurant_repo.get_by_id(restaurant_id)
        if not restaurant:
            return None

        # Single aggregation query for all table counts
        row = db.session.execute(
            select(
                func.count(Table.id).label("total"),
                func.count(case((Table.status == TableStatus.OCCUPIED, 1))).label("occupied"),
                func.count(case((Table.status == TableStatus.CLEANING, 1))).label("cleaning"),
                func.count(case((Table.status == TableStatus.AVAILABLE, 1))).label("available"),
                func.count(case((Table.status == TableStatus.RESERVED, 1))).label("reserved"),
            ).where(Table.restaurant_id == restaurant_id)
        ).one()

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
            "total_tables": row.total,
            "occupied_tables": row.occupied,
            "cleaning_tables": row.cleaning,
            "available_tables": row.available,
            "reserved_tables": row.reserved,
            "queue_count": queue_count,
            "avg_wait_minutes": avg_wait,
        }
