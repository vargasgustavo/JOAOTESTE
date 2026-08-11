"""Mapeamento de objetos de dominio para os schemas de resposta."""

from __future__ import annotations

from flask import current_app
from sqlalchemy.orm import Session

from app.models import Restaurant, Table
from app.schemas.queue import QueueEntryPublicResponse, QueueEntryResponse
from app.schemas.restaurant import RestaurantPublicResponse, RestaurantResponse
from app.schemas.table import AllocationCustomerResponse, TableResponse
from app.services import AllocationResult, QueueEntryView, RestaurantPublicView, WaitTimeService


def make_wait_time_service(session: Session) -> WaitTimeService:
    config = current_app.config
    return WaitTimeService(
        session,
        default_wait_minutes=config["DEFAULT_WAIT_MINUTES"],
        sample_hours=config["TURNOVER_SAMPLE_HOURS"],
        sample_size=config["TURNOVER_SAMPLE_SIZE"],
    )


def table_response(table: Table) -> TableResponse:
    return TableResponse.model_validate(table)


def restaurant_response(restaurant: Restaurant) -> RestaurantResponse:
    return RestaurantResponse.model_validate(restaurant)


def restaurant_public_response(view: RestaurantPublicView) -> RestaurantPublicResponse:
    return RestaurantPublicResponse(
        id=view.restaurant.id,
        name=view.restaurant.name,
        address=view.restaurant.address,
        opening_hours=view.restaurant.opening_hours,
        waiting_groups=view.waiting_groups,
        estimated_wait_minutes=view.estimated_wait_minutes,
    )


def queue_entry_response(view: QueueEntryView) -> QueueEntryResponse:
    entry = view.entry
    return QueueEntryResponse(
        id=entry.id,
        customer_name=entry.customer_name,
        customer_phone=entry.customer_phone,
        party_size=entry.party_size,
        status=entry.status,
        position=view.position,
        estimated_wait_minutes=view.estimated_wait_minutes,
        joined_at=entry.joined_at,
        called_at=entry.called_at,
        seated_at=entry.seated_at,
        cancelled_at=entry.cancelled_at,
        assigned_table_id=entry.assigned_table_id,
        assigned_table_number=view.table_number,
    )


def queue_entry_public_response(
    view: QueueEntryView, restaurant_name: str
) -> QueueEntryPublicResponse:
    entry = view.entry
    return QueueEntryPublicResponse(
        id=entry.id,
        customer_name=entry.customer_name,
        party_size=entry.party_size,
        status=entry.status,
        position=view.position,
        estimated_wait_minutes=view.estimated_wait_minutes,
        joined_at=entry.joined_at,
        called_at=entry.called_at,
        restaurant_name=restaurant_name,
        assigned_table_number=view.table_number,
    )


def allocation_response(result: AllocationResult | None) -> AllocationCustomerResponse | None:
    if result is None:
        return None
    return AllocationCustomerResponse(
        queue_entry_id=result.queue_entry_id,
        customer_name=result.customer_name,
        party_size=result.party_size,
        table_id=result.table_id,
        table_number=result.table_number,
    )
