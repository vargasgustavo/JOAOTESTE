from sqlalchemy import text, select, func
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

        table_stats = db.session.execute(
            select(
                func.count(Table.id).label("total"),
                func.sum((Table.status == TableStatus.OCCUPIED).cast(db.Integer)).label("occupied"),
                func.sum((Table.status == TableStatus.CLEANING).cast(db.Integer)).label("cleaning"),
                func.sum((Table.status == TableStatus.AVAILABLE).cast(db.Integer)).label("available"),
                func.sum((Table.status == TableStatus.RESERVED).cast(db.Integer)).label("reserved"),
            ).where(Table.restaurant_id == restaurant_id)
        ).one()

        queue_count = db.session.execute(
            select(func.count(QueueEntry.id)).where(
                QueueEntry.restaurant_id == restaurant_id,
                QueueEntry.status == QueueStatus.WAITING,
            )
        ).scalar_one()

        avg_wait = self._wait_svc.estimate_wait(1)

        return {
            "restaurant_id": restaurant_id,
            "restaurant_name": restaurant.name,
            "total_tables": table_stats.total or 0,
            "occupied_tables": int(table_stats.occupied or 0),
            "cleaning_tables": int(table_stats.cleaning or 0),
            "available_tables": int(table_stats.available or 0),
            "reserved_tables": int(table_stats.reserved or 0),
            "queue_count": queue_count or 0,
            "avg_wait_minutes": avg_wait,
        }
