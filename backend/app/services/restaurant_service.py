"""RestaurantService: CRUD do restaurante e visao publica para clientes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.errors import AuthorizationError, NotFoundError, ValidationError
from app.models import Restaurant, Role, User
from app.repositories import QueueRepository, RestaurantRepository
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate
from app.services.wait_time_service import WaitTimeService


@dataclass(frozen=True, slots=True)
class RestaurantPublicView:
    restaurant: Restaurant
    waiting_groups: int
    estimated_wait_minutes: int


class RestaurantService:
    def __init__(self, session: Session, wait_time: WaitTimeService) -> None:
        self.session = session
        self.restaurants = RestaurantRepository(session)
        self.queue = QueueRepository(session)
        self.wait_time = wait_time

    def list_public(self, limit: int = 50, offset: int = 0) -> list[RestaurantPublicView]:
        return [
            self._public_view(restaurant)
            for restaurant in self.restaurants.list_active(limit=limit, offset=offset)
        ]

    def get_public(self, restaurant_id: uuid.UUID) -> RestaurantPublicView:
        restaurant = self.restaurants.get(restaurant_id)
        if restaurant is None or not restaurant.is_active:
            raise NotFoundError("Restaurante nao encontrado.")
        return self._public_view(restaurant)

    def get_owned(self, restaurant_id: uuid.UUID) -> Restaurant:
        restaurant = self.restaurants.get(restaurant_id)
        if restaurant is None:
            raise NotFoundError("Restaurante nao encontrado.")
        return restaurant

    def create(self, payload: RestaurantCreate, owner: User) -> Restaurant:
        """Quem cria vira RESTAURANT_ADMIN do restaurante (1 restaurante por admin no V0)."""
        if owner.restaurant_id is not None:
            raise AuthorizationError("Este usuario ja administra um restaurante.")
        restaurant = Restaurant(
            name=payload.name,
            address=payload.address,
            phone=payload.phone,
            opening_hours=payload.opening_hours,
            is_active=True,
        )
        self.restaurants.add(restaurant)
        owner.restaurant_id = restaurant.id
        owner.role = Role.RESTAURANT_ADMIN
        # Invalida tokens antigos: as claims de tenant/role mudaram.
        owner.token_version += 1
        self.session.flush()
        return restaurant

    def update(self, restaurant_id: uuid.UUID, payload: RestaurantUpdate) -> Restaurant:
        restaurant = self.get_owned(restaurant_id)
        data = payload.model_dump(exclude_unset=True)
        if not data:
            raise ValidationError("Nenhum campo para atualizar.")
        for field, value in data.items():
            setattr(restaurant, field, value)
        self.session.flush()
        return restaurant

    def _public_view(self, restaurant: Restaurant) -> RestaurantPublicView:
        waiting = self.queue.waiting_count(restaurant.id)
        turnover = self.wait_time.average_turnover_minutes(restaurant.id)
        return RestaurantPublicView(
            restaurant=restaurant,
            waiting_groups=waiting,
            estimated_wait_minutes=(waiting + 1) * turnover,
        )
