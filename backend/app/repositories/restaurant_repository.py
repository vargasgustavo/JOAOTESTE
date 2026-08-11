from __future__ import annotations

from sqlalchemy import select

from app.models import Restaurant
from app.repositories.base import BaseRepository


class RestaurantRepository(BaseRepository[Restaurant]):
    model = Restaurant

    def list_active(self, limit: int = 100, offset: int = 0) -> list[Restaurant]:
        stmt = (
            select(Restaurant)
            .where(Restaurant.is_active.is_(True))
            .order_by(Restaurant.name)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.execute(stmt).scalars().all())
