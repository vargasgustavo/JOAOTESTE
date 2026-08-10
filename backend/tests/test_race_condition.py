"""Test: Concurrent allocation doesn't double-allocate same queue entry."""
import threading
from unittest.mock import patch

import pytest


class TestRaceCondition:
    def test_second_allocation_skips_already_called_entry(self, app, restaurant):
        """
        Logical invariant: once an entry is CALLED, a subsequent allocation
        attempt for another table must not re-allocate the same entry.
        This tests the status-check guard that protects against double allocation.
        """
        from app.extensions import db
        from app.models import QueueEntry, QueueStatus, Table, TableStatus
        from app.services.table_allocation_service import TableAllocationService

        with app.app_context():
            table1 = Table(
                restaurant_id=restaurant.id, number=20, capacity=4,
                status=TableStatus.AVAILABLE,
            )
            table2 = Table(
                restaurant_id=restaurant.id, number=21, capacity=4,
                status=TableStatus.AVAILABLE,
            )
            entry = QueueEntry(
                restaurant_id=restaurant.id,
                customer_name="Race Customer",
                customer_phone="11222333444",
                party_size=4,
                status=QueueStatus.WAITING,
            )
            db.session.add_all([table1, table2, entry])
            db.session.commit()

            with patch("app.tasks.notification_tasks.send_queue_called_task.delay"):
                svc = TableAllocationService()
                result1 = svc.try_allocate_for_table(table1)
                db.session.commit()

                # Second table tries to allocate — entry is now CALLED, not WAITING
                result2 = svc.try_allocate_for_table(table2)
                db.session.commit()

            assert result1 is not None, "First allocation should succeed"
            assert result2 is None, "Second allocation must find no WAITING entries"

    @pytest.mark.skip(
        reason=(
            "SQLite does not support SELECT FOR UPDATE SKIP LOCKED. "
            "Run this test against PostgreSQL to validate row-level locking."
        )
    )
    def test_concurrent_release_no_double_allocation(self, app, restaurant):
        """Two tables becoming available concurrently should not call same entry twice.
        Requires PostgreSQL for SELECT FOR UPDATE SKIP LOCKED to be effective.
        """
        from app.extensions import db
        from app.models import QueueEntry, QueueStatus, Table, TableStatus
        from app.services.table_allocation_service import TableAllocationService

        with app.app_context():
            table1 = Table(
                restaurant_id=restaurant.id, number=22, capacity=4,
                status=TableStatus.AVAILABLE,
            )
            table2 = Table(
                restaurant_id=restaurant.id, number=23, capacity=4,
                status=TableStatus.AVAILABLE,
            )
            entry = QueueEntry(
                restaurant_id=restaurant.id,
                customer_name="Race Customer Pg",
                customer_phone="11222333445",
                party_size=4,
                status=QueueStatus.WAITING,
            )
            db.session.add_all([table1, table2, entry])
            db.session.commit()

            results = []

            def allocate(tbl_id):
                with app.app_context():
                    from app.extensions import db as _db
                    from app.models import Table as T
                    tbl = _db.session.get(T, tbl_id)
                    with patch("app.tasks.notification_tasks.send_queue_called_task.delay"):
                        svc = TableAllocationService()
                        result = svc.try_allocate_for_table(tbl)
                    _db.session.commit()
                    results.append(result)

            t1 = threading.Thread(target=allocate, args=(table1.id,))
            t2 = threading.Thread(target=allocate, args=(table2.id,))
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            allocated = [r for r in results if r is not None]
            assert len(allocated) <= 1, "Double allocation occurred!"
