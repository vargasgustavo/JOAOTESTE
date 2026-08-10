from sqlalchemy import select
from sqlalchemy.orm import Session

from ..extensions import db
from ..models import User


class UserRepository:
    def __init__(self, session: Session | None = None):
        self._session = session or db.session

    def get_by_id(self, user_id: str) -> User | None:
        return self._session.get(User, user_id)

    def get_by_phone(self, phone: str) -> User | None:
        return self._session.execute(
            select(User).where(User.phone == phone)
        ).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        return self._session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

    def create(self, **kwargs) -> User:
        user = User(**kwargs)
        self._session.add(user)
        return user

    def list_by_restaurant(self, restaurant_id: str) -> list[User]:
        return list(
            self._session.execute(
                select(User).where(User.restaurant_id == restaurant_id)
            ).scalars().all()
        )
