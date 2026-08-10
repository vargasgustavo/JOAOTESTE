import enum
from sqlalchemy import String, Integer, DateTime, Enum as SAEnum, ForeignKey, Index
from sqlalchemy.orm import mapped_column, Mapped, relationship
from ..extensions import db
from .base import utcnow, new_uuid


class QueueStatus(str, enum.Enum):
    WAITING = "WAITING"
    CALLED = "CALLED"
    SEATED = "SEATED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class QueueEntry(db.Model):
    __tablename__ = "queue_entries"
    __table_args__ = (
        Index("ix_queue_entries_restaurant_status_joined", "restaurant_id", "status", "joined_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    restaurant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[QueueStatus] = mapped_column(
        SAEnum(QueueStatus), nullable=False, default=QueueStatus.WAITING
    )
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assigned_table_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tables.id", ondelete="SET NULL"), nullable=True
    )
    joined_at: Mapped[str] = mapped_column(DateTime(timezone=True), default=utcnow)
    called_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    seated_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)

    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="queue_entries")
    customer: Mapped["User"] = relationship("User", back_populates="queue_entries")
    assigned_table: Mapped["Table"] = relationship("Table", foreign_keys=[assigned_table_id])
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="queue_entry")

    def __repr__(self) -> str:
        return f"<QueueEntry {self.id} {self.customer_name} {self.status}>"
