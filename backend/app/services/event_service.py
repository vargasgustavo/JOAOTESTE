from datetime import datetime, timezone

from ..models import TableEvent
from ..repositories import EventRepository

EVENT_TABLE_OCCUPIED = "TABLE_OCCUPIED"
EVENT_TABLE_CLEANING = "TABLE_CLEANING"
EVENT_TABLE_AVAILABLE = "TABLE_AVAILABLE"
EVENT_TABLE_RESERVED = "TABLE_RESERVED"
EVENT_CUSTOMER_ASSIGNED = "CUSTOMER_ASSIGNED"
EVENT_CUSTOMER_CALLED = "CUSTOMER_CALLED"
EVENT_CUSTOMER_SEATED = "CUSTOMER_SEATED"


class EventService:
    def __init__(self, session=None):
        self._repo = EventRepository(session)

    def emit(self, table_id: str, event_type: str, metadata: dict | None = None) -> TableEvent:
        return self._repo.create_table_event(
            table_id=table_id,
            event_type=event_type,
            metadata=metadata or {},
        )

    def get_avg_turn_time_minutes(self) -> float:
        repo = self._repo
        available_events = repo.list_recent_events([EVENT_TABLE_AVAILABLE], limit=50)
        occupied_events = repo.list_recent_events([EVENT_TABLE_OCCUPIED], limit=50)

        if not available_events or not occupied_events:
            return 15.0

        available_by_table: dict[str, list[datetime]] = {}
        for ev in available_events:
            available_by_table.setdefault(ev.table_id, []).append(ev.timestamp)

        occupied_by_table: dict[str, list[datetime]] = {}
        for ev in occupied_events:
            occupied_by_table.setdefault(ev.table_id, []).append(ev.timestamp)

        durations = []
        for table_id, avail_times in available_by_table.items():
            occ_times = occupied_by_table.get(table_id, [])
            for avail_ts in avail_times:
                if isinstance(avail_ts, str):
                    avail_ts = datetime.fromisoformat(avail_ts)
                avail_ts = avail_ts.replace(tzinfo=timezone.utc) if avail_ts.tzinfo is None else avail_ts
                for occ_ts in occ_times:
                    if isinstance(occ_ts, str):
                        occ_ts = datetime.fromisoformat(occ_ts)
                    occ_ts = occ_ts.replace(tzinfo=timezone.utc) if occ_ts.tzinfo is None else occ_ts
                    if occ_ts > avail_ts:
                        diff = (occ_ts - avail_ts).total_seconds() / 60.0
                        if 0 < diff < 240:
                            durations.append(diff)
                        break

        if not durations:
            return 15.0

        return sum(durations) / len(durations)
