"""Schema inicial: restaurantes, mesas, usuarios, fila, eventos e notificacoes.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.models.base import JSONBType

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW = sa.text("CURRENT_TIMESTAMP")

TABLE_STATUS = sa.Enum(
    "OCCUPIED", "CLEANING", "AVAILABLE", "RESERVED", name="tablestatus", native_enum=False, length=32
)
ROLE = sa.Enum(
    "CUSTOMER", "RESTAURANT_ADMIN", "STAFF", name="role", native_enum=False, length=32
)
QUEUE_STATUS = sa.Enum(
    "WAITING",
    "CALLED",
    "SEATED",
    "CANCELLED",
    "EXPIRED",
    name="queuestatus",
    native_enum=False,
    length=32,
)
NOTIFICATION_CHANNEL = sa.Enum(
    "WHATSAPP", "SMS", "WEB", name="notificationchannel", native_enum=False, length=32
)
NOTIFICATION_STATUS = sa.Enum(
    "PENDING", "SENT", "FAILED", name="notificationstatus", native_enum=False, length=32
)
EVENT_TYPE = sa.Enum(
    "TABLE_OCCUPIED",
    "TABLE_CLEANING",
    "TABLE_AVAILABLE",
    "CUSTOMER_ASSIGNED",
    "CUSTOMER_CALLED",
    "CUSTOMER_SEATED",
    name="eventtype",
    native_enum=False,
    length=40,
)


def upgrade() -> None:
    op.create_table(
        "restaurants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("opening_hours", JSONBType, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_restaurants")),
    )
    op.create_index(op.f("ix_restaurants_name"), "restaurants", ["name"])

    op.create_table(
        "tables",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("restaurant_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.String(length=16), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("pos_x", sa.Integer(), nullable=False),
        sa.Column("pos_y", sa.Integer(), nullable=False),
        sa.Column("status", TABLE_STATUS, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint("capacity > 0", name=op.f("ck_tables_capacity_positive")),
        sa.ForeignKeyConstraint(
            ["restaurant_id"],
            ["restaurants.id"],
            name=op.f("fk_tables_restaurant_id_restaurants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tables")),
    )
    # Indice que sustenta a busca de mesas AVAILABLE por restaurante.
    op.create_index("ix_tables_restaurant_id_status", "tables", ["restaurant_id", "status"])
    op.create_index(
        "uq_tables_restaurant_id_number", "tables", ["restaurant_id", "number"], unique=True
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("role", ROLE, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("restaurant_id", sa.Uuid(), nullable=True),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(
            ["restaurant_id"],
            ["restaurants.id"],
            name=op.f("fk_users_restaurant_id_restaurants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index("ix_users_restaurant_id_role", "users", ["restaurant_id", "role"])

    op.create_table(
        "queue_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("restaurant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("customer_name", sa.String(length=120), nullable=False),
        sa.Column("customer_phone", sa.String(length=32), nullable=False),
        sa.Column("party_size", sa.Integer(), nullable=False),
        sa.Column("status", QUEUE_STATUS, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("called_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("seated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_table_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint("party_size > 0", name=op.f("ck_queue_entries_party_size_positive")),
        sa.ForeignKeyConstraint(
            ["assigned_table_id"],
            ["tables.id"],
            name=op.f("fk_queue_entries_assigned_table_id_tables"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["restaurant_id"],
            ["restaurants.id"],
            name=op.f("fk_queue_entries_restaurant_id_restaurants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_queue_entries_user_id_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_queue_entries")),
    )
    # Indice que sustenta o FIFO da fila por restaurante.
    op.create_index(
        "ix_queue_entries_restaurant_status_joined",
        "queue_entries",
        ["restaurant_id", "status", "joined_at"],
    )
    op.create_index(
        "ix_queue_entries_assigned_table_id", "queue_entries", ["assigned_table_id"]
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("queue_entry_id", sa.Uuid(), nullable=False),
        sa.Column("channel", NOTIFICATION_CHANNEL, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", NOTIFICATION_STATUS, nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_message_id", sa.String(length=120), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(
            ["queue_entry_id"],
            ["queue_entries.id"],
            name=op.f("fk_notifications_queue_entry_id_queue_entries"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index("ix_notifications_queue_entry_id", "notifications", ["queue_entry_id"])

    op.create_table(
        "table_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("restaurant_id", sa.Uuid(), nullable=False),
        sa.Column("table_id", sa.Uuid(), nullable=True),
        sa.Column("queue_entry_id", sa.Uuid(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", EVENT_TYPE, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("metadata", JSONBType, nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_table_events_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["queue_entry_id"],
            ["queue_entries.id"],
            name=op.f("fk_table_events_queue_entry_id_queue_entries"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["restaurant_id"],
            ["restaurants.id"],
            name=op.f("fk_table_events_restaurant_id_restaurants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["table_id"], ["tables.id"], name=op.f("fk_table_events_table_id_tables"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_table_events")),
    )
    op.create_index(
        "ix_table_events_restaurant_type_ts",
        "table_events",
        ["restaurant_id", "event_type", "timestamp"],
    )
    op.create_index("ix_table_events_table_id_ts", "table_events", ["table_id", "timestamp"])


def downgrade() -> None:
    op.drop_index("ix_table_events_table_id_ts", table_name="table_events")
    op.drop_index("ix_table_events_restaurant_type_ts", table_name="table_events")
    op.drop_table("table_events")
    op.drop_index("ix_notifications_queue_entry_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_queue_entries_assigned_table_id", table_name="queue_entries")
    op.drop_index("ix_queue_entries_restaurant_status_joined", table_name="queue_entries")
    op.drop_table("queue_entries")
    op.drop_index("ix_users_restaurant_id_role", table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index("uq_tables_restaurant_id_number", table_name="tables")
    op.drop_index("ix_tables_restaurant_id_status", table_name="tables")
    op.drop_table("tables")
    op.drop_index(op.f("ix_restaurants_name"), table_name="restaurants")
    op.drop_table("restaurants")
