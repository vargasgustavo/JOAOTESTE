from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from ..extensions import limiter
from ..schemas import QueueEntryCreateSchema, QueueEntrySchema
from ..services.queue_service import QueueService
from .middleware import require_auth, require_csrf, verify_restaurant_access

queue_bp = Blueprint("queue", __name__)
_create_schema = QueueEntryCreateSchema()
_schema = QueueEntrySchema()
_svc = QueueService()


@queue_bp.get("/restaurants/<restaurant_id>/queue")
@require_auth
def list_queue(restaurant_id: str):
    if not verify_restaurant_access(restaurant_id):
        return jsonify({"error": "Access denied"}), 403
    status = request.args.get("status")
    items = _svc.list_queue(restaurant_id, status)
    result = []
    for item in items:
        dumped = _schema.dump(item["entry"])
        dumped["position"] = item["position"]
        dumped["estimated_wait_minutes"] = item["estimated_wait"]
        result.append(dumped)
    return jsonify({"queue": result}), 200


@queue_bp.post("/restaurants/<restaurant_id>/queue")
@limiter.limit("3 per minute")
@require_csrf
def join_queue(restaurant_id: str):
    try:
        data = _create_schema.load(request.get_json(force=True) or {})
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.messages}), 422

    customer_id = None
    token = request.cookies.get("access_token")
    if token:
        try:
            from ..services.auth_service import AuthService
            auth_svc = AuthService()
            payload = auth_svc.decode_token(token)
            customer_id = payload["sub"]
        except ValueError:
            pass

    result = _svc.join_queue(
        restaurant_id=restaurant_id,
        customer_id=customer_id,
        **data,
    )
    dumped = _schema.dump(result["entry"])
    dumped["position"] = result["position"]
    dumped["estimated_wait_minutes"] = result["estimated_wait"]
    return jsonify({"queue_entry": dumped}), 201


@queue_bp.get("/queue/<entry_id>")
@require_auth
def get_queue_entry(entry_id: str):
    from ..services.auth_service import AuthService

    token = request.cookies.get("access_token")
    payload = AuthService().decode_token(token)
    role = payload.get("role", "")
    user_id = payload.get("sub")

    result = _svc.get_entry(entry_id)
    entry = result["entry"]

    # CUSTOMER may only view their own entry; STAFF/ADMIN can view any entry
    if role == "CUSTOMER" and str(entry.customer_id) != user_id:
        return jsonify({"error": "Access denied"}), 403

    dumped = _schema.dump(entry)
    dumped["position"] = result["position"]
    dumped["estimated_wait_minutes"] = result["estimated_wait"]
    return jsonify({"queue_entry": dumped}), 200


@queue_bp.post("/queue/<entry_id>/cancel")
@require_csrf
def cancel_queue_entry(entry_id: str):
    user_id = None
    restaurant_id = None
    token = request.cookies.get("access_token")
    if token:
        try:
            from ..services.auth_service import AuthService
            auth_svc = AuthService()
            payload = auth_svc.decode_token(token)
            user_id = payload["sub"]
            restaurant_id = payload.get("restaurant_id")
            if payload["role"] in ("STAFF", "RESTAURANT_ADMIN"):
                restaurant_id = None
        except ValueError:
            pass

    entry = _svc.cancel_entry(entry_id, requesting_user_id=user_id, restaurant_id=restaurant_id)
    return jsonify({"queue_entry": _schema.dump(entry), "message": "Cancelled"}), 200
