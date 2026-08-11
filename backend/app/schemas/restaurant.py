from __future__ import annotations

import re
import uuid
from typing import Annotated, Any

from pydantic import Field, StringConstraints, field_validator

from app.schemas.common import NameStr, ResponseSchema, StrictSchema, normalize_phone

AddressStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=255)]
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _validate_opening_hours(value: dict[str, Any]) -> dict[str, Any]:
    """Formato: {"mon": {"open": "11:00", "close": "23:00"}} - validado campo a campo."""
    if len(value) > 7:
        raise ValueError("opening_hours aceita no maximo 7 dias.")
    for day, hours in value.items():
        if day not in WEEKDAYS:
            raise ValueError(f"Dia invalido: {day}. Use {list(WEEKDAYS)}.")
        if not isinstance(hours, dict) or set(hours) != {"open", "close"}:
            raise ValueError("Cada dia precisa de exatamente 'open' e 'close'.")
        for key in ("open", "close"):
            if not isinstance(hours[key], str) or not TIME_RE.match(hours[key]):
                raise ValueError(f"Horario invalido em {day}.{key}. Use HH:MM.")
    return value


class RestaurantCreate(StrictSchema):
    name: NameStr
    address: AddressStr
    phone: str = Field(max_length=32)
    opening_hours: dict[str, Any] = Field(default_factory=dict)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("opening_hours")
    @classmethod
    def _hours(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_opening_hours(value)


class RestaurantUpdate(StrictSchema):
    name: NameStr | None = None
    address: AddressStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    opening_hours: dict[str, Any] | None = None
    is_active: bool | None = None

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value else None

    @field_validator("opening_hours")
    @classmethod
    def _hours(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return _validate_opening_hours(value) if value is not None else None


class RestaurantResponse(ResponseSchema):
    id: uuid.UUID
    name: str
    address: str
    phone: str
    opening_hours: dict[str, Any]
    is_active: bool


class RestaurantPublicResponse(ResponseSchema):
    """Visao do cliente: sem dados operacionais internos do restaurante."""

    id: uuid.UUID
    name: str
    address: str
    opening_hours: dict[str, Any]
    waiting_groups: int
    estimated_wait_minutes: int
