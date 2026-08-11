from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models import Role, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.strip().lower())
        return self.session.execute(stmt).scalar_one_or_none()

    def email_exists(self, email: str) -> bool:
        stmt = select(User.id).where(User.email == email.strip().lower()).limit(1)
        return self.session.execute(stmt).first() is not None

    def list_by_restaurant(self, restaurant_id: uuid.UUID, role: Role | None = None) -> list[User]:
        stmt = select(User).where(User.restaurant_id == restaurant_id)
        if role is not None:
            stmt = stmt.where(User.role == role)
        return list(self.session.execute(stmt).scalars().all())
