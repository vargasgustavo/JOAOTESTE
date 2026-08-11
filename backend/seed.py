"""Seed de desenvolvimento: 1 restaurante, 10 mesas, 1 admin, 1 staff e 5 clientes na fila.

Uso: python seed.py  (senhas via SEED_ADMIN_PASSWORD / SEED_STAFF_PASSWORD)
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from app import create_app
from app.extensions import db
from app.models import (
    QueueEntry,
    QueueStatus,
    Restaurant,
    Role,
    Table,
    TableStatus,
    User,
    utcnow,
)
from app.repositories import UserRepository
from app.security import hash_password

ADMIN_EMAIL = "admin@cantinadoporto.com.br"
STAFF_EMAIL = "staff@cantinadoporto.com.br"
DEFAULT_DEV_PASSWORD = "TrocarEsta123"  # noqa: S105 - apenas ambiente de desenvolvimento

TABLE_LAYOUT = [
    ("1", 2, 0, 0),
    ("2", 2, 1, 0),
    ("3", 4, 2, 0),
    ("4", 4, 3, 0),
    ("5", 4, 0, 1),
    ("6", 6, 1, 1),
    ("7", 6, 2, 1),
    ("8", 8, 3, 1),
    ("9", 2, 0, 2),
    ("10", 4, 1, 2),
]

QUEUE_SEED = [
    ("Joao Almeida", "+5511999990001", 4),
    ("Maria Souza", "+5511999990002", 2),
    ("Pedro Lima", "+5511999990003", 5),
    ("Ana Ribeiro", "+5511999990004", 3),
    ("Carlos Dias", "+5511999990005", 6),
]


def _password(env_var: str) -> str:
    password = os.getenv(env_var)
    if password:
        return password
    if os.getenv("ENV", "development").lower() in {"production", "prod"}:
        raise SystemExit(f"Defina {env_var} para rodar o seed em producao.")
    return DEFAULT_DEV_PASSWORD


def seed() -> None:
    app = create_app()
    with app.app_context():
        session = db.s
        users = UserRepository(session)
        if users.email_exists(ADMIN_EMAIL):
            print("Seed ja aplicado (admin existente). Nada a fazer.")
            return

        restaurant = Restaurant(
            name="Cantina do Porto",
            address="Rua das Palmeiras, 120 - Sao Paulo/SP",
            phone="+551133334444",
            opening_hours={
                day: {"open": "11:00", "close": "23:00"}
                for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
            },
            is_active=True,
        )
        session.add(restaurant)
        session.flush()

        admin_password = _password("SEED_ADMIN_PASSWORD")
        staff_password = _password("SEED_STAFF_PASSWORD")
        session.add_all(
            [
                User(
                    email=ADMIN_EMAIL,
                    password_hash=hash_password(admin_password),
                    full_name="Administradora Cantina",
                    role=Role.RESTAURANT_ADMIN,
                    restaurant_id=restaurant.id,
                ),
                User(
                    email=STAFF_EMAIL,
                    password_hash=hash_password(staff_password),
                    full_name="Garcom Cantina",
                    role=Role.STAFF,
                    restaurant_id=restaurant.id,
                ),
            ]
        )

        # Salao cheio: 9 mesas ocupadas e a mesa 5 em limpeza, pronta para "LIBERAR MESA".
        for number, capacity, pos_x, pos_y in TABLE_LAYOUT:
            session.add(
                Table(
                    restaurant_id=restaurant.id,
                    number=number,
                    capacity=capacity,
                    pos_x=pos_x,
                    pos_y=pos_y,
                    status=TableStatus.CLEANING if number == "5" else TableStatus.OCCUPIED,
                )
            )

        for position, (name, phone, party_size) in enumerate(QUEUE_SEED, start=1):
            session.add(
                QueueEntry(
                    restaurant_id=restaurant.id,
                    customer_name=name,
                    customer_phone=phone,
                    party_size=party_size,
                    status=QueueStatus.WAITING,
                    position=position,
                    joined_at=utcnow(),
                )
            )

        session.commit()
        print("Seed concluido.")
        print(f"  Restaurante: {restaurant.name} ({restaurant.id})")
        print(f"  Admin: {ADMIN_EMAIL} / {admin_password}")
        print(f"  Staff: {STAFF_EMAIL} / {staff_password}")
        print("  10 mesas (mesa 5 em CLEANING) e 5 clientes aguardando.")


if __name__ == "__main__":
    load_dotenv()
    try:
        seed()
    except SystemExit as exc:  # pragma: no cover
        print(exc, file=sys.stderr)
        raise
