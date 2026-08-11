from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONBType, UUIDPrimaryKeyMixin, utcnow
from app.models.enums import EventType

if TYPE_CHECKING:  # pragma: no cover
    from app.models.table import Table


class TableEvent(UUIDPrimaryKeyMixin, Base):
    """Trilha de auditoria imutavel; alimenta o WaitTimeService."""

    __tablename__ = "table_events"
    __table_args__ = (
        Index("ix_table_events_restaurant_type_ts", "restaurant_id", "event_type", "timestamp"),
        Index("ix_table_events_table_id_ts", "table_id", "timestamp"),
    )

    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    table_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tables.id", ondelete="CASCADE"), nullable=True
    )
    queue_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("queue_entries.id", ondelete="SET NULL"), nullable=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, native_enum=False, length=40, validate_strings=True), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
    #: Atributo `event_metadata` porque `metadata` e reservado pelo SQLAlchemy.
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONBType, nullable=False, default=dict
    )

    table: Mapped[Table | None] = relationship(back_populates="events")
