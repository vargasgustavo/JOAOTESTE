from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.models import QueueEntry, QueueStatus
from app.repositories.base import BaseRepository


class QueueRepository(BaseRepository[QueueEntry]):
    model = QueueEntry

    def get_scoped(self, entry_id: uuid.UUID, restaurant_id: uuid.UUID) -> QueueEntry | None:
        stmt = select(QueueEntry).where(
            QueueEntry.id == entry_id, QueueEntry.restaurant_id == restaurant_id
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_for_update(self, entry_id: uuid.UUID) -> QueueEntry | None:
        stmt = select(QueueEntry).where(QueueEntry.id == entry_id).with_for_update()
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_restaurant(
        self, restaurant_id: uuid.UUID, statuses: tuple[QueueStatus, ...] | None = None
    ) -> list[QueueEntry]:
        stmt = select(QueueEntry).where(QueueEntry.restaurant_id == restaurant_id)
        if statuses:
            stmt = stmt.where(QueueEntry.status.in_(statuses))
        stmt = stmt.order_by(QueueEntry.joined_at, QueueEntry.position)
        return list(self.session.execute(stmt).scalars().all())

    def next_position(self, restaurant_id: uuid.UUID) -> int:
        stmt = select(func.coalesce(func.max(QueueEntry.position), 0)).where(
            QueueEntry.restaurant_id == restaurant_id
        )
        return int(self.session.execute(stmt).scalar_one()) + 1

    def waiting_count(self, restaurant_id: uuid.UUID) -> int:
        stmt = select(func.count(QueueEntry.id)).where(
            QueueEntry.restaurant_id == restaurant_id, QueueEntry.status == QueueStatus.WAITING
        )
        return int(self.session.execute(stmt).scalar_one())

    def position_of(self, entry: QueueEntry) -> int | None:
        """Posicao 1-based entre os WAITING, calculada sob demanda (sem renumerar linhas)."""
        if entry.status != QueueStatus.WAITING:
            return None
        stmt = select(func.count(QueueEntry.id)).where(
            QueueEntry.restaurant_id == entry.restaurant_id,
            QueueEntry.status == QueueStatus.WAITING,
            QueueEntry.position < entry.position,
        )
        return int(self.session.execute(stmt).scalar_one()) + 1

    def has_open_entry_for_phone(self, restaurant_id: uuid.UUID, phone: str) -> bool:
        stmt = (
            select(QueueEntry.id)
            .where(
                QueueEntry.restaurant_id == restaurant_id,
                QueueEntry.customer_phone == phone,
                QueueEntry.status.in_((QueueStatus.WAITING, QueueStatus.CALLED)),
            )
            .limit(1)
        )
        return self.session.execute(stmt).first() is not None

    def lock_waiting_fifo(self, restaurant_id: uuid.UUID, skip_locked: bool) -> list[QueueEntry]:
        """FIFO travado; SKIP LOCKED evita que liberacoes simultaneas peguem a mesma entry."""
        stmt = (
            select(QueueEntry)
            .where(
                QueueEntry.restaurant_id == restaurant_id,
                QueueEntry.status == QueueStatus.WAITING,
            )
            .order_by(QueueEntry.joined_at, QueueEntry.position)
        )
        stmt = stmt.with_for_update(skip_locked=True) if skip_locked else stmt.with_for_update()
        return list(self.session.execute(stmt).scalars().all())

    def lock_first_compatible(
        self, restaurant_id: uuid.UUID, capacity: int, skip_locked: bool
    ) -> QueueEntry | None:
        """Primeiro WAITING (FIFO) que cabe na mesa, travando apenas essa linha.

        Travar somente a linha escolhida (em vez da fila inteira) permite que duas
        liberacoes simultaneas aloquem grupos diferentes em vez de disputar a mesma entry.
        """
        stmt = (
            select(QueueEntry)
            .where(
                QueueEntry.restaurant_id == restaurant_id,
                QueueEntry.status == QueueStatus.WAITING,
                QueueEntry.party_size <= capacity,
            )
            .order_by(QueueEntry.joined_at, QueueEntry.position)
            .limit(1)
        )
        stmt = stmt.with_for_update(skip_locked=True) if skip_locked else stmt.with_for_update()
        return self.session.execute(stmt).scalars().first()
