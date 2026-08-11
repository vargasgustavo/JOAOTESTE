"""Rotas de restaurante: listagem publica, CRUD do tenant e dashboard."""

from __future__ import annotations

from flask import Blueprint, jsonify, make_response, request

from app.controllers.helpers import parse_body, parse_uuid, serialize, serialize_many
from app.controllers.serializers import (
    make_wait_time_service,
    restaurant_public_response,
    restaurant_response,
)
from app.models import Role
from app.schemas.auth import UserResponse
from app.schemas.dashboard import DashboardResponse
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate
from app.security import (
    assert_same_restaurant,
    auth_required,
    current_user,
    require_roles,
    set_auth_cookies,
)
from app.services import AuthService, DashboardService, RestaurantService, transaction

bp = Blueprint("restaurants", __name__, url_prefix="/restaurants")

MAX_PAGE_SIZE = 50


@bp.get("")
def list_restaurants():
    """Publico: apenas dados que o cliente precisa para escolher onde entrar na fila."""
    limit = min(request.args.get("limit", default=20, type=int) or 20, MAX_PAGE_SIZE)
    offset = max(request.args.get("offset", default=0, type=int) or 0, 0)
    with transaction() as session:
        service = RestaurantService(session, make_wait_time_service(session))
        views = service.list_public(limit=limit, offset=offset)
        body = serialize_many([restaurant_public_response(view) for view in views])
    return jsonify({"items": body, "limit": limit, "offset": offset}), 200


@bp.get("/<restaurant_id>")
def get_restaurant(restaurant_id: str):
    identifier = parse_uuid(restaurant_id, "restaurant_id")
    with transaction() as session:
        service = RestaurantService(session, make_wait_time_service(session))
        body = serialize(restaurant_public_response(service.get_public(identifier)))
    return jsonify(body), 200


@bp.post("")
@auth_required
def create_restaurant():
    """Quem cria assume RESTAURANT_ADMIN; os cookies sao reemitidos com as novas claims."""
    payload = parse_body(RestaurantCreate)
    user = current_user()
    with transaction() as session:
        service = RestaurantService(session, make_wait_time_service(session))
        restaurant = service.create(payload, user)
        tokens = AuthService(session).issue_tokens(user)
        body = serialize(restaurant_response(restaurant))
        user_body = serialize(UserResponse.model_validate(user))
    response = make_response(jsonify({**body, "user": user_body}), 201)
    return set_auth_cookies(response, tokens.access_token, tokens.refresh_token, tokens.csrf_token)


@bp.put("/<restaurant_id>")
@require_roles(Role.RESTAURANT_ADMIN)
def update_restaurant(restaurant_id: str):
    identifier = assert_same_restaurant(parse_uuid(restaurant_id, "restaurant_id"))
    payload = parse_body(RestaurantUpdate)
    with transaction() as session:
        service = RestaurantService(session, make_wait_time_service(session))
        body = serialize(restaurant_response(service.update(identifier, payload)))
    return jsonify(body), 200


@bp.get("/<restaurant_id>/dashboard")
@require_roles(Role.RESTAURANT_ADMIN, Role.STAFF)
def dashboard(restaurant_id: str):
    identifier = assert_same_restaurant(parse_uuid(restaurant_id, "restaurant_id"))
    with transaction() as session:
        service = DashboardService(session, make_wait_time_service(session))
        metrics = service.metrics(identifier)
        body = serialize(DashboardResponse.model_validate(metrics.as_dict()))
    return jsonify(body), 200
