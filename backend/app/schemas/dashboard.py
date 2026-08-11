from __future__ import annotations

import uuid

from app.schemas.common import ResponseSchema


class DashboardResponse(ResponseSchema):
    restaurant_id: uuid.UUID
    total_tables: int
    occupied_tables: int
    cleaning_tables: int
    available_tables: int
    reserved_tables: int
    waiting_customers: int
    called_customers: int
    average_wait_minutes: int
    average_turnover_minutes: int
