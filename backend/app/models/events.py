from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy import JSON
from sqlalchemy.orm import mapped_column, Mapped, relationship
from ..extensions import db
from .base import utcnow, new_uuid


class TableEvent(db.Model):
    __tablename__ = "table_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    table_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tables.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), default=utcnow)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=True, default=dict)

    table: Mapped["Table"] = relationship("Table", back_populates="events")

    def __repr__(self) -> str:
        return f"<TableEvent {self.id} {self.event_type}>"


class Notification(db.Model):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    queue_entry_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("queue_entries.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="mock")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    sent_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)

    queue_entry: Mapped["QueueEntry"] = relationship("QueueEntry", back_populates="notifications")

    def __repr__(self) -> str:
        return f"<Notification {self.id} {self.channel} {self.status}>"
