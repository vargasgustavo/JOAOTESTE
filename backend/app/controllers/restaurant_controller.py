from flask import Blueprint, request, jsonify, g
from marshmallow import ValidationError

from ..services.restaurant_service import RestaurantService
from ..schemas import RestaurantCreateSchema, RestaurantUpdateSchema, RestaurantSchema
from .middleware import require_auth, require_roles, require_csrf
from ..models import UserRole

restaurant_bp = Blueprint("restaurants", __name__)
_create_schema = RestaurantCreateSchema()
_update_schema = RestaurantUpdateSchema()
_schema = RestaurantSchema()
_svc = RestaurantService()


@restaurant_bp.get("/")
@require_auth
def list_restaurants():
    restaurants = _svc.list_restaurants(active_only=True)
    return jsonify({"restaurants": _schema.dump(restaurants, many=True)}), 200


@restaurant_bp.get("/<restaurant_id>")
@require_auth
def get_restaurant(restaurant_id: str):
    try:
        restaurant = _svc.get_restaurant(restaurant_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    return jsonify({"restaurant": _schema.dump(restaurant)}), 200


@restaurant_bp.post("/")
@require_roles(UserRole.RESTAURANT_ADMIN)
@require_csrf
def create_restaurant():
    try:
        data = _create_schema.load(request.get_json(force=True) or {})
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.messages}), 422

    restaurant = _svc.create_restaurant(**data)
    return jsonify({"restaurant": _schema.dump(restaurant)}), 201


@restaurant_bp.put("/<restaurant_id>")
@require_roles(UserRole.RESTAURANT_ADMIN)
@require_csrf
def update_restaurant(restaurant_id: str):
    role = getattr(g, "user_role", None)
    user_rest = getattr(g, "restaurant_id", None)
    if role != UserRole.RESTAURANT_ADMIN.value or user_rest != restaurant_id:
        return jsonify({"error": "Access denied"}), 403

    try:
        data = _update_schema.load(request.get_json(force=True) or {})
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.messages}), 422

    try:
        restaurant = _svc.update_restaurant(restaurant_id, **data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    return jsonify({"restaurant": _schema.dump(restaurant)}), 200
