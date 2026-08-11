from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.models import QueueStatus
from app.schemas.common import NameStr, ResponseSchema, StrictSchema, normalize_phone


class QueueJoinRequest(StrictSchema):
    customer_name: NameStr
    customer_phone: str = Field(max_length=32)
    party_size: int = Field(ge=1, le=20)

    @field_validator("customer_phone")
    @classmethod
    def _phone(cls, value: str) -> str:
        return normalize_phone(value)


class QueueEntryResponse(ResponseSchema):
    """Visao interna (staff/admin): inclui telefone para contato."""

    id: uuid.UUID
    customer_name: str
    customer_phone: str
    party_size: int
    status: QueueStatus
    position: int | None = None
    estimated_wait_minutes: int | None = None
    joined_at: datetime
    called_at: datetime | None = None
    seated_at: datetime | None = None
    cancelled_at: datetime | None = None
    assigned_table_id: uuid.UUID | None = None
    assigned_table_number: str | None = None


class QueueEntryPublicResponse(ResponseSchema):
    """Visao do cliente: sem telefone e sem ids internos alem do proprio ticket."""

    id: uuid.UUID
    customer_name: str
    party_size: int
    status: QueueStatus
    position: int | None = None
    estimated_wait_minutes: int | None = None
    joined_at: datetime
    called_at: datetime | None = None
    restaurant_name: str
    assigned_table_number: str | None = None
