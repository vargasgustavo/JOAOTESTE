from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow
from app.models.enums import QueueStatus

if TYPE_CHECKING:  # pragma: no cover
    from app.models.notification import Notification
    from app.models.restaurant import Restaurant
    from app.models.user import User


class QueueEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "queue_entries"
    __table_args__ = (
        Index("ix_queue_entries_restaurant_status_joined", "restaurant_id", "status", "joined_at"),
        Index("ix_queue_entries_assigned_table_id", "assigned_table_id"),
        CheckConstraint("party_size > 0", name="party_size_positive"),
    )

    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    customer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[QueueStatus] = mapped_column(
        Enum(QueueStatus, native_enum=False, length=32, validate_strings=True),
        nullable=False,
        default=QueueStatus.WAITING,
    )
    #: Ordem de chegada monotonica por restaurante (desempate estavel do FIFO).
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
    called_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    seated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assigned_table_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tables.id", ondelete="SET NULL"), nullable=True
    )

    restaurant: Mapped[Restaurant] = relationship(back_populates="queue_entries")
    user: Mapped[User | None] = relationship(back_populates="queue_entries")
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="queue_entry", cascade="all, delete-orphan"
    )

    @property
    def is_open(self) -> bool:
        return self.status in (QueueStatus.WAITING, QueueStatus.CALLED)
