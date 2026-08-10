"""Test: FIFO allocation, invalid transitions."""
import pytest
from unittest.mock import patch


class TestFIFOAllocation:
    """Table cap=4, queue=[João-4, Maria-2, Pedro-5] → João gets table."""

    def test_fifo_compatible_allocation(self, app, restaurant):
        from app.models import Table, TableStatus, QueueEntry, QueueStatus
        from app.services.table_allocation_service import TableAllocationService
        from app.extensions import db

        with app.app_context():
            table = Table(
                restaurant_id=restaurant.id,
                number=1,
                capacity=4,
                status=TableStatus.AVAILABLE,
            )
            db.session.add(table)

            joao = QueueEntry(
                restaurant_id=restaurant.id,
                customer_name="João",
                customer_phone="11111111111",
                party_size=4,
                status=QueueStatus.WAITING,
            )
            maria = QueueEntry(
                restaurant_id=restaurant.id,
                customer_name="Maria",
                customer_phone="11111111112",
                party_size=2,
                status=QueueStatus.WAITING,
            )
            pedro = QueueEntry(
                restaurant_id=restaurant.id,
                customer_name="Pedro",
                customer_phone="11111111113",
                party_size=5,
                status=QueueStatus.WAITING,
            )
            db.session.add_all([joao, maria, pedro])
            db.session.flush()

            with patch("app.tasks.notification_tasks.send_queue_called_task.delay"):
                svc = TableAllocationService()
                allocated = svc.try_allocate_for_table(table)

            assert allocated is not None
            assert allocated.customer_name == "João"
            assert allocated.status == QueueStatus.CALLED
            assert table.status == TableStatus.RESERVED
            db.session.commit()


class TestInvalidTableTransitions:
    def test_available_to_occupied_is_invalid(self, app, restaurant):
        from app.models import Table, TableStatus
        from app.extensions import db

        with app.app_context():
            table = Table(restaurant_id=restaurant.id, number=2, capacity=4, status=TableStatus.AVAILABLE)
            db.session.add(table)
            db.session.commit()
            assert not table.can_transition_to(TableStatus.OCCUPIED)

    def test_valid_full_cycle(self, app, restaurant):
        from app.models import Table, TableStatus
        from app.extensions import db

        with app.app_context():
            table = Table(restaurant_id=restaurant.id, number=3, capacity=4, status=TableStatus.OCCUPIED)
            db.session.add(table)
            db.session.commit()

            assert table.can_transition_to(TableStatus.CLEANING)
            table.status = TableStatus.CLEANING
            assert table.can_transition_to(TableStatus.AVAILABLE)
            table.status = TableStatus.AVAILABLE
            assert table.can_transition_to(TableStatus.RESERVED)
            table.status = TableStatus.RESERVED
            assert table.can_transition_to(TableStatus.OCCUPIED)

    def test_transition_endpoint_returns_409(self, client, app, restaurant, staff_user):
        from app.models import Table, TableStatus
        from app.extensions import db

        with app.app_context():
            table = Table(restaurant_id=restaurant.id, number=4, capacity=4, status=TableStatus.AVAILABLE)
            db.session.add(table)
            db.session.commit()
            table_id = table.id

        client.post("/api/auth/login", json={"phone": staff_user.phone, "password": "Staff@123"})
        resp = client.post(f"/api/tables/{table_id}/release")
        assert resp.status_code == 409
