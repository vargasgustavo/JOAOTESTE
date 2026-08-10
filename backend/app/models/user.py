import enum
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship
from .base import Base, utcnow, new_uuid


class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    RESTAURANT_ADMIN = "RESTAURANT_ADMIN"
    STAFF = "STAFF"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False, default=UserRole.CUSTOMER)
    restaurant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), default=utcnow)

    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="staff", foreign_keys=[restaurant_id])
    queue_entries: Mapped[list["QueueEntry"]] = relationship("QueueEntry", back_populates="customer")

    def __repr__(self) -> str:
        return f"<User {self.id} {self.role}>"
