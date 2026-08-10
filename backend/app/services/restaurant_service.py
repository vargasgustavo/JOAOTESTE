from ..extensions import db
from ..models import Restaurant
from ..repositories import RestaurantRepository


class RestaurantService:
    def __init__(self):
        self._repo = RestaurantRepository()

    def list_restaurants(self, active_only: bool = True) -> list[Restaurant]:
        if active_only:
            return self._repo.list_active()
        return self._repo.list_all()

    def get_restaurant(self, restaurant_id: str) -> Restaurant:
        restaurant = self._repo.get_by_id(restaurant_id)
        if not restaurant:
            raise ValueError("Restaurant not found")
        return restaurant

    def create_restaurant(self, **kwargs) -> Restaurant:
        restaurant = self._repo.create(**kwargs)
        db.session.commit()
        return restaurant

    def update_restaurant(self, restaurant_id: str, **kwargs) -> Restaurant:
        restaurant = self.get_restaurant(restaurant_id)
        self._repo.update(restaurant, **kwargs)
        db.session.commit()
        return restaurant
