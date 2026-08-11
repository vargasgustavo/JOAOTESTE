from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONBType, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.queue_entry import QueueEntry
    from app.models.table import Table
    from app.models.user import User


class Restaurant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "restaurants"

    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    #: {"mon": {"open": "11:00", "close": "23:00"}, ...}
    opening_hours: Mapped[dict[str, Any]] = mapped_column(
        JSONBType, nullable=False, default=dict
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tables: Mapped[list[Table]] = relationship(
        back_populates="restaurant", cascade="all, delete-orphan"
    )
    queue_entries: Mapped[list[QueueEntry]] = relationship(
        back_populates="restaurant", cascade="all, delete-orphan"
    )
    users: Mapped[list[User]] = relationship(back_populates="restaurant")
