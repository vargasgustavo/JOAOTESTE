from __future__ import annotations

import uuid

from sqlalchemy import Select, select

from app.models import Table, TableStatus
from app.repositories.base import BaseRepository


class TableRepository(BaseRepository[Table]):
    model = Table

    def get_scoped(self, table_id: uuid.UUID, restaurant_id: uuid.UUID) -> Table | None:
        """Sempre filtra por restaurant_id: barreira contra IDOR/BOLA."""
        stmt = select(Table).where(Table.id == table_id, Table.restaurant_id == restaurant_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_for_update(self, table_id: uuid.UUID, restaurant_id: uuid.UUID) -> Table | None:
        stmt = (
            select(Table)
            .where(Table.id == table_id, Table.restaurant_id == restaurant_id)
            .with_for_update()
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_restaurant(self, restaurant_id: uuid.UUID) -> list[Table]:
        stmt = (
            select(Table)
            .where(Table.restaurant_id == restaurant_id)
            .order_by(Table.pos_y, Table.pos_x, Table.number)
        )
        return list(self.session.execute(stmt).scalars().all())

    def number_exists(
        self, restaurant_id: uuid.UUID, number: str, exclude_id: uuid.UUID | None = None
    ) -> bool:
        stmt = select(Table.id).where(
            Table.restaurant_id == restaurant_id, Table.number == number
        )
        if exclude_id is not None:
            stmt = stmt.where(Table.id != exclude_id)
        return self.session.execute(stmt.limit(1)).first() is not None

    def select_available_for_party(
        self, restaurant_id: uuid.UUID, party_size: int, skip_locked: bool
    ) -> Select[tuple[Table]]:
        """Menor mesa AVAILABLE que comporta o grupo, travada para alocacao."""
        stmt = (
            select(Table)
            .where(
                Table.restaurant_id == restaurant_id,
                Table.status == TableStatus.AVAILABLE,
                Table.capacity >= party_size,
            )
            .order_by(Table.capacity, Table.number)
        )
        return stmt.with_for_update(skip_locked=True) if skip_locked else stmt.with_for_update()

    def find_available_for_party(
        self, restaurant_id: uuid.UUID, party_size: int, skip_locked: bool
    ) -> Table | None:
        stmt = self.select_available_for_party(restaurant_id, party_size, skip_locked).limit(1)
        return self.session.execute(stmt).scalars().first()
