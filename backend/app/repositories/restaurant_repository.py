from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Restaurant
from ..extensions import db


class RestaurantRepository:
    def __init__(self, session: Session | None = None):
        self._session = session or db.session

    def get_by_id(self, restaurant_id: str) -> Restaurant | None:
        return self._session.get(Restaurant, restaurant_id)

    def list_active(self) -> list[Restaurant]:
        return list(
            self._session.execute(
                select(Restaurant).where(Restaurant.is_active == True)
            ).scalars().all()
        )

    def list_all(self) -> list[Restaurant]:
        return list(self._session.execute(select(Restaurant)).scalars().all())

    def create(self, **kwargs) -> Restaurant:
        restaurant = Restaurant(**kwargs)
        self._session.add(restaurant)
        return restaurant

    def update(self, restaurant: Restaurant, **kwargs) -> Restaurant:
        for key, value in kwargs.items():
            setattr(restaurant, key, value)
        return restaurant
