from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TableStatus

if TYPE_CHECKING:  # pragma: no cover
    from app.models.restaurant import Restaurant
    from app.models.table_event import TableEvent


class Table(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tables"
    __table_args__ = (
        Index("ix_tables_restaurant_id_status", "restaurant_id", "status"),
        Index("uq_tables_restaurant_id_number", "restaurant_id", "number", unique=True),
        CheckConstraint("capacity > 0", name="capacity_positive"),
    )

    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[str] = mapped_column(String(16), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    pos_x: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pos_y: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[TableStatus] = mapped_column(
        Enum(TableStatus, native_enum=False, length=32, validate_strings=True),
        nullable=False,
        default=TableStatus.AVAILABLE,
    )

    restaurant: Mapped[Restaurant] = relationship(back_populates="tables")
    events: Mapped[list[TableEvent]] = relationship(
        back_populates="table", cascade="all, delete-orphan"
    )
