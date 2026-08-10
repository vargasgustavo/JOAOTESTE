"""Test: Concurrent allocation doesn't double-allocate same queue entry."""
import threading
import pytest
from unittest.mock import patch


class TestRaceCondition:
    def test_concurrent_release_no_double_allocation(self, app, db, restaurant):
        """Two tables becoming available concurrently should not call same entry twice."""
        from app.models import Table, TableStatus, QueueEntry, QueueStatus
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

            results = []

            def allocate(tbl_id):
                with app.app_context():
                    from app.extensions import db as _db
                    from app.models import Table
                    tbl = _db.session.get(Table, tbl_id)
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
            # At most one allocation should succeed for the single entry
            assert len(allocated) <= 1, "Double allocation occurred!"
