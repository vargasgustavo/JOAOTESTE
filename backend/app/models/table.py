import enum

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .base import new_uuid, utcnow


class TableStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    OCCUPIED = "OCCUPIED"
    CLEANING = "CLEANING"


VALID_TRANSITIONS: dict[TableStatus, list[TableStatus]] = {
    TableStatus.OCCUPIED: [TableStatus.CLEANING],
    TableStatus.CLEANING: [TableStatus.AVAILABLE],
    TableStatus.AVAILABLE: [TableStatus.RESERVED],
    TableStatus.RESERVED: [TableStatus.OCCUPIED],
}


class Table(db.Model):
    __tablename__ = "tables"
    __table_args__ = (
        Index("ix_tables_restaurant_status", "restaurant_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    restaurant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    pos_x: Mapped[float] = mapped_column(Float, nullable=True)
    pos_y: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[TableStatus] = mapped_column(
        SAEnum(TableStatus), nullable=False, default=TableStatus.AVAILABLE
    )
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="tables")
    events: Mapped[list["TableEvent"]] = relationship("TableEvent", back_populates="table")

    def can_transition_to(self, new_status: TableStatus) -> bool:
        allowed = VALID_TRANSITIONS.get(self.status, [])
        return new_status in allowed

    def __repr__(self) -> str:
        return f"<Table {self.id} #{self.number} {self.status}>"
