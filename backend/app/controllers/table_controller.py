from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from ..models import UserRole
from ..schemas import TableCreateSchema, TableSchema, TableUpdateSchema
from ..services.table_service import TableService
from .middleware import require_auth, require_csrf, require_roles, verify_restaurant_access

table_bp = Blueprint("tables", __name__)
_create_schema = TableCreateSchema()
_update_schema = TableUpdateSchema()
_schema = TableSchema()
_svc = TableService()


@table_bp.get("/restaurants/<restaurant_id>/tables")
@require_auth
def list_tables(restaurant_id: str):
    if not verify_restaurant_access(restaurant_id):
        return jsonify({"error": "Access denied"}), 403
    tables = _svc.list_tables(restaurant_id)
    return jsonify({"tables": _schema.dump(tables, many=True)}), 200


@table_bp.post("/restaurants/<restaurant_id>/tables")
@require_roles(UserRole.RESTAURANT_ADMIN, UserRole.STAFF)
@require_csrf
def create_table(restaurant_id: str):
    if not verify_restaurant_access(restaurant_id):
        return jsonify({"error": "Access denied"}), 403
    try:
        data = _create_schema.load(request.get_json(force=True) or {})
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.messages}), 422
    table = _svc.create_table(restaurant_id=restaurant_id, **data)
    return jsonify({"table": _schema.dump(table)}), 201


@table_bp.put("/tables/<table_id>")
@require_roles(UserRole.RESTAURANT_ADMIN, UserRole.STAFF)
@require_csrf
def update_table(table_id: str):
    try:
        data = _update_schema.load(request.get_json(force=True) or {})
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.messages}), 422
    table = _svc.update_table(table_id, **data)
    return jsonify({"table": _schema.dump(table)}), 200


@table_bp.post("/tables/<table_id>/release")
@require_roles(UserRole.STAFF, UserRole.RESTAURANT_ADMIN)
@require_csrf
def release_table(table_id: str):
    table = _svc.release_table(table_id)
    return jsonify({"table": _schema.dump(table), "message": "Table released for cleaning"}), 200


@table_bp.post("/tables/<table_id>/cleaning")
@require_roles(UserRole.STAFF, UserRole.RESTAURANT_ADMIN)
@require_csrf
def mark_cleaning(table_id: str):
    table = _svc.mark_cleaning_done(table_id)
    return jsonify({"table": _schema.dump(table), "message": "Table available"}), 200


@table_bp.post("/tables/<table_id>/occupy")
@require_roles(UserRole.STAFF, UserRole.RESTAURANT_ADMIN)
@require_csrf
def occupy_table(table_id: str):
    table = _svc.occupy_table(table_id)
    return jsonify({"table": _schema.dump(table), "message": "Table occupied"}), 200


@table_bp.post("/tables/<table_id>/allocate")
@require_roles(UserRole.STAFF, UserRole.RESTAURANT_ADMIN)
@require_csrf
def manual_allocate(table_id: str):
    from ..repositories import TableRepository
    from ..services.table_allocation_service import TableAllocationService
    repo = TableRepository()
    table = repo.get_by_id(table_id)
    if not table:
        return jsonify({"error": "Table not found"}), 404
    alloc_svc = TableAllocationService()
    entry = alloc_svc.try_allocate_for_table(table)
    from ..extensions import db
    db.session.commit()
    if entry:
        return jsonify({"message": "Allocated", "queue_entry_id": entry.id}), 200
    return jsonify({"message": "No compatible group found"}), 200
