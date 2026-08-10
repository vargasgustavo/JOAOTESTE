from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .base import new_uuid, utcnow


class Restaurant(db.Model):
    __tablename__ = "restaurants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(512), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    opening_hours: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), default=utcnow)

    tables: Mapped[list["Table"]] = relationship("Table", back_populates="restaurant")
    staff: Mapped[list["User"]] = relationship("User", back_populates="restaurant", foreign_keys="User.restaurant_id")
    queue_entries: Mapped[list["QueueEntry"]] = relationship("QueueEntry", back_populates="restaurant")

    def __repr__(self) -> str:
        return f"<Restaurant {self.id} {self.name}>"
