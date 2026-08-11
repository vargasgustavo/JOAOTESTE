"""DashboardService: metricas do salao em uma unica ida ao banco."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass

from sqlalchemy import Integer, case, func, select
from sqlalchemy.orm import Session

from app.models import QueueEntry, QueueStatus, Table, TableStatus
from app.services.wait_time_service import WaitTimeService


@dataclass(frozen=True, slots=True)
class DashboardMetrics:
    restaurant_id: uuid.UUID
    total_tables: int
    occupied_tables: int
    cleaning_tables: int
    available_tables: int
    reserved_tables: int
    waiting_customers: int
    called_customers: int
    average_wait_minutes: int
    average_turnover_minutes: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _count_status(status: TableStatus):
    return func.coalesce(func.sum(case((Table.status == status, 1), else_=0)), 0).cast(Integer)


def _queue_count(restaurant_id: uuid.UUID, status: QueueStatus):
    return (
        select(func.count(QueueEntry.id))
        .where(QueueEntry.restaurant_id == restaurant_id, QueueEntry.status == status)
        .scalar_subquery()
    )


class DashboardService:
    def __init__(self, session: Session, wait_time: WaitTimeService) -> None:
        self.session = session
        self.wait_time = wait_time

    def metrics(self, restaurant_id: uuid.UUID) -> DashboardMetrics:
        # Agregacao condicional das mesas + subqueries escalares da fila: 1 round-trip.
        stmt = select(
            func.count(Table.id).label("total"),
            _count_status(TableStatus.OCCUPIED).label("occupied"),
            _count_status(TableStatus.CLEANING).label("cleaning"),
            _count_status(TableStatus.AVAILABLE).label("available"),
            _count_status(TableStatus.RESERVED).label("reserved"),
            _queue_count(restaurant_id, QueueStatus.WAITING).label("waiting"),
            _queue_count(restaurant_id, QueueStatus.CALLED).label("called"),
        ).where(Table.restaurant_id == restaurant_id)
        row = self.session.execute(stmt).one()

        turnover = self.wait_time.average_turnover_minutes(restaurant_id)
        waiting = int(row.waiting or 0)
        # Media das estimativas individuais (posicao x giro) dos grupos aguardando.
        average_wait = round(turnover * (waiting + 1) / 2) if waiting else 0

        return DashboardMetrics(
            restaurant_id=restaurant_id,
            total_tables=int(row.total or 0),
            occupied_tables=int(row.occupied or 0),
            cleaning_tables=int(row.cleaning or 0),
            available_tables=int(row.available or 0),
            reserved_tables=int(row.reserved or 0),
            waiting_customers=waiting,
            called_customers=int(row.called or 0),
            average_wait_minutes=average_wait,
            average_turnover_minutes=turnover,
        )
