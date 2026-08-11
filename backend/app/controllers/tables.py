"""Rotas de mesas: CRUD e as tres acoes de salao (limpeza, liberar, ocupar)."""

from __future__ import annotations

from flask import Blueprint, jsonify

from app.controllers.helpers import parse_body, parse_uuid, serialize, serialize_many
from app.controllers.serializers import allocation_response, table_response
from app.models import Role
from app.schemas.table import TableCreate, TableUpdate
from app.security import assert_same_restaurant, current_restaurant_id, current_user, require_roles
from app.services import TableService, transaction

restaurant_tables_bp = Blueprint("restaurant_tables", __name__, url_prefix="/restaurants")
tables_bp = Blueprint("tables", __name__, url_prefix="/tables")


@restaurant_tables_bp.get("/<restaurant_id>/tables")
@require_roles(Role.RESTAURANT_ADMIN, Role.STAFF)
def list_tables(restaurant_id: str):
    identifier = assert_same_restaurant(parse_uuid(restaurant_id, "restaurant_id"))
    with transaction() as session:
        tables = TableService(session).list_tables(identifier)
        body = serialize_many([table_response(table) for table in tables])
    return jsonify({"items": body}), 200


@restaurant_tables_bp.post("/<restaurant_id>/tables")
@require_roles(Role.RESTAURANT_ADMIN)
def create_table(restaurant_id: str):
    identifier = assert_same_restaurant(parse_uuid(restaurant_id, "restaurant_id"))
    payload = parse_body(TableCreate)
    with transaction() as session:
        table = TableService(session).create_table(identifier, payload)
        body = serialize(table_response(table))
    return jsonify(body), 201


@tables_bp.put("/<table_id>")
@require_roles(Role.RESTAURANT_ADMIN)
def update_table(table_id: str):
    identifier = parse_uuid(table_id, "table_id")
    payload = parse_body(TableUpdate)
    restaurant_id = current_restaurant_id()
    with transaction() as session:
        table = TableService(session).update_table(identifier, restaurant_id, payload)
        body = serialize(table_response(table))
    return jsonify(body), 200


@tables_bp.post("/<table_id>/cleaning")
@require_roles(Role.RESTAURANT_ADMIN, Role.STAFF)
def start_cleaning(table_id: str):
    identifier = parse_uuid(table_id, "table_id")
    restaurant_id = current_restaurant_id()
    actor_id = current_user().id
    with transaction() as session:
        table = TableService(session).start_cleaning(identifier, restaurant_id, actor_id)
        body = serialize(table_response(table))
    return jsonify({"table": body, "allocation": None}), 200


@tables_bp.post("/<table_id>/release")
@require_roles(Role.RESTAURANT_ADMIN, Role.STAFF)
def release_table(table_id: str):
    """LIBERAR MESA: um clique libera, aloca o proximo grupo compativel e notifica."""
    identifier = parse_uuid(table_id, "table_id")
    restaurant_id = current_restaurant_id()
    actor_id = current_user().id
    with transaction() as session:
        table, allocation = TableService(session).release_table(
            identifier, restaurant_id, actor_id
        )
        body = serialize(table_response(table))
        allocated = allocation_response(allocation)
        allocated_body = serialize(allocated) if allocated else None
    return jsonify({"table": body, "allocation": allocated_body}), 200


@tables_bp.post("/<table_id>/occupy")
@require_roles(Role.RESTAURANT_ADMIN, Role.STAFF)
def occupy_table(table_id: str):
    identifier = parse_uuid(table_id, "table_id")
    restaurant_id = current_restaurant_id()
    actor_id = current_user().id
    with transaction() as session:
        table = TableService(session).occupy_table(identifier, restaurant_id, actor_id)
        body = serialize(table_response(table))
    return jsonify({"table": body, "allocation": None}), 200


@tables_bp.post("/<table_id>/allocate")
@require_roles(Role.RESTAURANT_ADMIN, Role.STAFF)
def allocate_table(table_id: str):
    """Fallback manual: forca a alocacao em uma mesa que ja esta AVAILABLE."""
    identifier = parse_uuid(table_id, "table_id")
    restaurant_id = current_restaurant_id()
    actor_id = current_user().id
    with transaction() as session:
        service = TableService(session)
        allocation = service.allocate_manually(identifier, restaurant_id, actor_id)
        table = service.get_table(identifier, restaurant_id)
        body = serialize(table_response(table))
        allocated = allocation_response(allocation)
        allocated_body = serialize(allocated) if allocated else None
    return jsonify({"table": body, "allocation": allocated_body}), 200
