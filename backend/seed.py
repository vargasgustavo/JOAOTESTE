#!/usr/bin/env python3
"""Seed script: creates 1 restaurant, 10 tables, 1 admin, 1 staff, 5 queue customers."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("SECRET_KEY", "seed-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "seed-jwt-secret-key")
os.environ.setdefault("DATABASE_URL", "postgresql://restaurant:restaurant@localhost:5432/restaurant")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ARGON2_TIME_COST", "1")
os.environ.setdefault("ARGON2_MEMORY_COST", "8192")
os.environ.setdefault("ARGON2_PARALLELISM", "1")

from argon2 import PasswordHasher

from app import create_app
from app.extensions import db
from app.models import QueueEntry, QueueStatus, Restaurant, Table, TableStatus, User, UserRole

app = create_app("development")

with app.app_context():
    db.create_all()

    hasher = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)

    # Restaurant
    restaurant = Restaurant(
        name="Restaurante Modelo",
        address="Rua das Flores, 123 - São Paulo, SP",
        phone="11999999999",
        opening_hours={"mon-fri": "11:00-23:00", "sat-sun": "11:00-00:00"},
        is_active=True,
    )
    db.session.add(restaurant)
    db.session.flush()

    # Tables: 10 tables with mixed capacities 2-6
    capacities = [2, 2, 4, 4, 4, 6, 6, 2, 4, 6]
    statuses = [
        TableStatus.AVAILABLE, TableStatus.OCCUPIED, TableStatus.CLEANING,
        TableStatus.AVAILABLE, TableStatus.RESERVED, TableStatus.AVAILABLE,
        TableStatus.OCCUPIED, TableStatus.AVAILABLE, TableStatus.AVAILABLE, TableStatus.AVAILABLE,
    ]
    for i, (cap, status) in enumerate(zip(capacities, statuses), 1):
        table = Table(
            restaurant_id=restaurant.id,
            number=i,
            capacity=cap,
            pos_x=float((i - 1) % 5 * 150 + 50),
            pos_y=float((i - 1) // 5 * 120 + 50),
            status=status,
        )
        db.session.add(table)

    # Admin user
    admin = User(
        name="Admin Principal",
        phone="11111111111",
        email="admin@restaurante.com",
        password_hash=hasher.hash("Admin@123"),
        role=UserRole.RESTAURANT_ADMIN,
        restaurant_id=restaurant.id,
    )
    db.session.add(admin)

    # Staff user
    staff = User(
        name="Garçom João",
        phone="11222222222",
        email="staff@restaurante.com",
        password_hash=hasher.hash("Staff@123"),
        role=UserRole.STAFF,
        restaurant_id=restaurant.id,
    )
    db.session.add(staff)

    db.session.flush()

    # 5 customers in queue
    customers = [
        ("João Silva", "11333333333", 4),
        ("Maria Santos", "11444444444", 2),
        ("Pedro Oliveira", "11555555555", 5),
        ("Ana Costa", "11666666666", 3),
        ("Carlos Lima", "11777777777", 1),
    ]
    for name, phone, party_size in customers:
        customer = User(
            name=name,
            phone=phone,
            password_hash=hasher.hash("Customer@123"),
            role=UserRole.CUSTOMER,
        )
        db.session.add(customer)
        db.session.flush()

        entry = QueueEntry(
            restaurant_id=restaurant.id,
            customer_id=customer.id,
            customer_name=name,
            customer_phone=phone,
            party_size=party_size,
            status=QueueStatus.WAITING,
        )
        db.session.add(entry)

    db.session.commit()

    print("✅ Seed complete!")
    print(f"   Restaurant: {restaurant.name} (ID: {restaurant.id})")
    print("   Admin: admin@restaurante.com / Admin@123")
    print("   Staff: staff@restaurante.com / Staff@123")
    print("   Customer phone: 11333333333 / Customer@123")
    print(f"   Queue entries: {len(customers)}")
