"""Enums de dominio compartilhados entre models, schemas e services."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    CUSTOMER = "CUSTOMER"
    RESTAURANT_ADMIN = "RESTAURANT_ADMIN"
    STAFF = "STAFF"


class TableStatus(StrEnum):
    OCCUPIED = "OCCUPIED"
    CLEANING = "CLEANING"
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"


class QueueStatus(StrEnum):
    WAITING = "WAITING"
    CALLED = "CALLED"
    SEATED = "SEATED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class EventType(StrEnum):
    TABLE_OCCUPIED = "TABLE_OCCUPIED"
    TABLE_CLEANING = "TABLE_CLEANING"
    TABLE_AVAILABLE = "TABLE_AVAILABLE"
    CUSTOMER_ASSIGNED = "CUSTOMER_ASSIGNED"
    CUSTOMER_CALLED = "CUSTOMER_CALLED"
    CUSTOMER_SEATED = "CUSTOMER_SEATED"


class NotificationChannel(StrEnum):
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"
    WEB = "WEB"


class NotificationStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


#: Unica fonte de verdade das transicoes de mesa permitidas.
ALLOWED_TABLE_TRANSITIONS: dict[TableStatus, frozenset[TableStatus]] = {
    TableStatus.OCCUPIED: frozenset({TableStatus.CLEANING}),
    TableStatus.CLEANING: frozenset({TableStatus.AVAILABLE}),
    TableStatus.AVAILABLE: frozenset({TableStatus.RESERVED, TableStatus.OCCUPIED}),
    TableStatus.RESERVED: frozenset({TableStatus.OCCUPIED, TableStatus.AVAILABLE}),
}


def can_transition(current: TableStatus, target: TableStatus) -> bool:
    return target in ALLOWED_TABLE_TRANSITIONS.get(current, frozenset())
