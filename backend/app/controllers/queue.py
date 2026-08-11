"""Rotas de fila: entrada publica do cliente e operacao interna do restaurante."""

from __future__ import annotations

import uuid

from flask import Blueprint, current_app, jsonify

from app.controllers.helpers import parse_body, parse_uuid, serialize, serialize_many
from app.controllers.serializers import (
    allocation_response,
    make_wait_time_service,
    queue_entry_public_response,
    queue_entry_response,
)
from app.errors import AuthorizationError, NotFoundError
from app.extensions import limiter
from app.models import QueueStatus, Role
from app.repositories import RestaurantRepository
from app.schemas.queue import QueueJoinRequest
from app.security import assert_same_restaurant, current_user_optional, require_roles
from app.services import QueueService, transaction

restaurant_queue_bp = Blueprint("restaurant_queue", __name__, url_prefix="/restaurants")
queue_bp = Blueprint("queue", __name__, url_prefix="/queue")

OPEN_STATUSES = (QueueStatus.WAITING, QueueStatus.CALLED)


def _queue_join_limit() -> str:
    return current_app.config["RATELIMIT_QUEUE_JOIN"]


@restaurant_queue_bp.get("/<restaurant_id>/queue")
@require_roles(Role.RESTAURANT_ADMIN, Role.STAFF)
def list_queue(restaurant_id: str):
    identifier = assert_same_restaurant(parse_uuid(restaurant_id, "restaurant_id"))
    with transaction() as session:
        service = QueueService(session, make_wait_time_service(session))
        views = service.list_entries(identifier, statuses=OPEN_STATUSES)
        body = serialize_many([queue_entry_response(view) for view in views])
    return jsonify({"items": body}), 200


@restaurant_queue_bp.post("/<restaurant_id>/queue")
@limiter.limit(_queue_join_limit)
def join_queue(restaurant_id: str):
    """Publico: cliente entra na fila; se houver mesa livre compativel, ja e chamado."""
    identifier = parse_uuid(restaurant_id, "restaurant_id")
    payload = parse_body(QueueJoinRequest)
    user = current_user_optional()
    user_id = user.id if user and user.role == Role.CUSTOMER else None
    with transaction() as session:
        service = QueueService(session, make_wait_time_service(session))
        entry, allocation = service.join(identifier, payload, user_id=user_id)
        view = service.get_entry_view(entry.id)
        restaurant = RestaurantRepository(session).get(identifier)
        body = serialize(queue_entry_public_response(view, restaurant.name if restaurant else ""))
        allocated = allocation_response(allocation)
        allocated_body = serialize(allocated) if allocated else None
    return jsonify({**body, "allocation": allocated_body}), 201


@queue_bp.get("/<entry_id>")
@limiter.limit("120 per minute")
def get_queue_entry(entry_id: str):
    """Consulta do ticket. O UUID v4 do ticket funciona como capability nao adivinhavel."""
    identifier = parse_uuid(entry_id, "entry_id")
    with transaction() as session:
        service = QueueService(session, make_wait_time_service(session))
        view = service.get_entry_view(identifier)
        _assert_can_read(view.entry.user_id, view.entry.restaurant_id)
        restaurant = RestaurantRepository(session).get(view.entry.restaurant_id)
        body = serialize(queue_entry_public_response(view, restaurant.name if restaurant else ""))
    return jsonify(body), 200


@queue_bp.post("/<entry_id>/cancel")
@limiter.limit("20 per minute")
def cancel_queue_entry(entry_id: str):
    identifier = parse_uuid(entry_id, "entry_id")
    user = current_user_optional()
    with transaction() as session:
        service = QueueService(session, make_wait_time_service(session))
        view = service.get_entry_view(identifier)
        _assert_can_read(view.entry.user_id, view.entry.restaurant_id)
        entry, reallocation = service.cancel(identifier, actor_user_id=user.id if user else None)
        refreshed = service.get_entry_view(entry.id)
        restaurant = RestaurantRepository(session).get(entry.restaurant_id)
        body = serialize(
            queue_entry_public_response(refreshed, restaurant.name if restaurant else "")
        )
        reallocated = allocation_response(reallocation)
        reallocated_body = serialize(reallocated) if reallocated else None
    return jsonify({**body, "reallocation": reallocated_body}), 200


def _assert_can_read(entry_user_id: uuid.UUID | None, restaurant_id: uuid.UUID) -> None:
    """Cliente logado so acessa o proprio ticket; staff so acessa o proprio restaurante."""
    user = current_user_optional()
    if user is None:
        if entry_user_id is not None:
            # Ticket pertence a uma conta: exige a sessao dessa conta.
            raise NotFoundError("Entrada da fila nao encontrada.")
        return
    if user.role in (Role.STAFF, Role.RESTAURANT_ADMIN):
        if user.restaurant_id != restaurant_id:
            raise NotFoundError("Entrada da fila nao encontrada.")
        return
    if entry_user_id is not None and entry_user_id != user.id:
        raise AuthorizationError("Voce nao tem acesso a esta entrada da fila.")
