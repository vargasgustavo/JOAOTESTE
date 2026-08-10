from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..models import QueueEntry, QueueStatus
from ..extensions import db


class QueueRepository:
    def __init__(self, session: Session | None = None):
        self._session = session or db.session

    def get_by_id(self, entry_id: str) -> QueueEntry | None:
        return self._session.get(QueueEntry, entry_id)

    def get_waiting_for_restaurant(self, restaurant_id: str) -> list[QueueEntry]:
        return list(
            self._session.execute(
                select(QueueEntry)
                .where(
                    QueueEntry.restaurant_id == restaurant_id,
                    QueueEntry.status == QueueStatus.WAITING,
                )
                .order_by(QueueEntry.joined_at.asc())
                .with_for_update(skip_locked=True)
            ).scalars().all()
        )

    def list_by_restaurant(self, restaurant_id: str, status: str | None = None) -> list[QueueEntry]:
        stmt = select(QueueEntry).where(QueueEntry.restaurant_id == restaurant_id)
        if status:
            stmt = stmt.where(QueueEntry.status == status)
        stmt = stmt.order_by(QueueEntry.joined_at.asc())
        return list(self._session.execute(stmt).scalars().all())

    def count_waiting(self, restaurant_id: str) -> int:
        result = self._session.execute(
            select(func.count(QueueEntry.id)).where(
                QueueEntry.restaurant_id == restaurant_id,
                QueueEntry.status == QueueStatus.WAITING,
            )
        ).scalar_one()
        return result or 0

    def create(self, **kwargs) -> QueueEntry:
        entry = QueueEntry(**kwargs)
        self._session.add(entry)
        return entry

    def update(self, entry: QueueEntry, **kwargs) -> QueueEntry:
        for key, value in kwargs.items():
            setattr(entry, key, value)
        return entry

    def get_position(self, restaurant_id: str, entry_id: str) -> int:
        waiting = self.list_by_restaurant(restaurant_id, status=QueueStatus.WAITING.value)
        for i, e in enumerate(waiting, 1):
            if e.id == entry_id:
                return i
        return 0
