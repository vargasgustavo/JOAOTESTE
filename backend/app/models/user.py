from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Role

if TYPE_CHECKING:  # pragma: no cover
    from app.models.queue_entry import QueueEntry
    from app.models.restaurant import Restaurant


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_restaurant_id_role", "restaurant_id", "role"),)

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role: Mapped[Role] = mapped_column(
        Enum(Role, native_enum=False, length=32, validate_strings=True),
        nullable=False,
        default=Role.CUSTOMER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    #: Sempre NULL para CUSTOMER; obrigatorio para STAFF/RESTAURANT_ADMIN.
    restaurant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=True
    )
    #: Invalida tokens emitidos antes desta versao (logout global / troca de senha).
    token_version: Mapped[int] = mapped_column(nullable=False, default=0)

    restaurant: Mapped[Restaurant | None] = relationship(back_populates="users")
    queue_entries: Mapped[list[QueueEntry]] = relationship(back_populates="user")

    @property
    def is_staff(self) -> bool:
        return self.role in (Role.STAFF, Role.RESTAURANT_ADMIN)
