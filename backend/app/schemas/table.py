from __future__ import annotations

import uuid

from pydantic import Field

from app.models import TableStatus
from app.schemas.common import ResponseSchema, StrictSchema, TableNumberStr


class TableCreate(StrictSchema):
    number: TableNumberStr
    capacity: int = Field(ge=1, le=50)
    pos_x: int = Field(default=0, ge=0, le=1000)
    pos_y: int = Field(default=0, ge=0, le=1000)


class TableUpdate(StrictSchema):
    number: TableNumberStr | None = None
    capacity: int | None = Field(default=None, ge=1, le=50)
    pos_x: int | None = Field(default=None, ge=0, le=1000)
    pos_y: int | None = Field(default=None, ge=0, le=1000)


class TableResponse(ResponseSchema):
    id: uuid.UUID
    number: str
    capacity: int
    pos_x: int
    pos_y: int
    status: TableStatus
    restaurant_id: uuid.UUID


class AllocationCustomerResponse(ResponseSchema):
    queue_entry_id: uuid.UUID
    customer_name: str
    party_size: int
    table_id: uuid.UUID
    table_number: str


class TableActionResponse(ResponseSchema):
    table: TableResponse
    allocation: AllocationCustomerResponse | None = None
