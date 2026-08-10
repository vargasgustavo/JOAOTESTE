from sqlalchemy import select
from sqlalchemy.orm import Session

from ..extensions import db
from ..models import Table, TableStatus


def _supports_for_update() -> bool:
    """Return True when the active dialect supports SELECT FOR UPDATE SKIP LOCKED."""
    return db.engine.dialect.name != "sqlite"


class TableRepository:
    def __init__(self, session: Session | None = None):
        self._session = session or db.session

    def get_by_id(self, table_id: str) -> Table | None:
        return self._session.get(Table, table_id)

    def list_by_restaurant(self, restaurant_id: str) -> list[Table]:
        return list(
            self._session.execute(
                select(Table).where(Table.restaurant_id == restaurant_id)
            ).scalars().all()
        )

    def get_available_for_restaurant(self, restaurant_id: str) -> list[Table]:
        stmt = select(Table).where(
            Table.restaurant_id == restaurant_id,
            Table.status == TableStatus.AVAILABLE,
        )
        if _supports_for_update():
            stmt = stmt.with_for_update(skip_locked=True)
        return list(self._session.execute(stmt).scalars().all())

    def create(self, **kwargs) -> Table:
        table = Table(**kwargs)
        self._session.add(table)
        return table

    def update(self, table: Table, **kwargs) -> Table:
        for key, value in kwargs.items():
            setattr(table, key, value)
        return table
