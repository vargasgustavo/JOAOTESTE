from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import TableEvent, Notification
from ..extensions import db


class EventRepository:
    def __init__(self, session: Session | None = None):
        self._session = session or db.session

    def create_table_event(self, table_id: str, event_type: str, metadata: dict | None = None) -> TableEvent:
        event = TableEvent(
            table_id=table_id,
            event_type=event_type,
            metadata_=metadata or {},
        )
        self._session.add(event)
        return event

    def list_by_table(self, table_id: str, limit: int = 100) -> list[TableEvent]:
        return list(
            self._session.execute(
                select(TableEvent)
                .where(TableEvent.table_id == table_id)
                .order_by(TableEvent.timestamp.desc())
                .limit(limit)
            ).scalars().all()
        )

    def list_recent_events(self, event_types: list[str], limit: int = 100) -> list[TableEvent]:
        return list(
            self._session.execute(
                select(TableEvent)
                .where(TableEvent.event_type.in_(event_types))
                .order_by(TableEvent.timestamp.desc())
                .limit(limit)
            ).scalars().all()
        )


class NotificationRepository:
    def __init__(self, session: Session | None = None):
        self._session = session or db.session

    def create(self, **kwargs) -> Notification:
        notif = Notification(**kwargs)
        self._session.add(notif)
        return notif

    def update(self, notif: Notification, **kwargs) -> Notification:
        for key, value in kwargs.items():
            setattr(notif, key, value)
        return notif
