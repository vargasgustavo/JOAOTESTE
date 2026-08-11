"""WaitTimeService isolado: giro real das mesas, fallback e estimativa por posicao."""

from __future__ import annotations

from datetime import timedelta

from app.extensions import db
from app.models import EventType, TableEvent, utcnow
from app.services import WaitTimeService
from tests.conftest import make_table


def _service() -> WaitTimeService:
    return WaitTimeService(db.s, default_wait_minutes=15, sample_hours=24, sample_size=50)


def _event(restaurant_id, table_id, event_type: EventType, when) -> None:
    db.s.add(
        TableEvent(
            restaurant_id=restaurant_id,
            table_id=table_id,
            event_type=event_type,
            timestamp=when,
            event_metadata={},
        )
    )
    db.s.commit()


def test_sem_historico_usa_fallback_de_15_minutos(app, restaurant):
    assert _service().average_turnover_minutes(restaurant.id) == 15


def test_media_usa_intervalo_available_para_occupied(app, restaurant):
    mesa = make_table(restaurant.id, "1", 4)
    agora = utcnow()
    # Dois giros: 20 min e 30 min -> media 25.
    _event(restaurant.id, mesa.id, EventType.TABLE_AVAILABLE, agora - timedelta(minutes=120))
    _event(restaurant.id, mesa.id, EventType.TABLE_OCCUPIED, agora - timedelta(minutes=100))
    _event(restaurant.id, mesa.id, EventType.TABLE_AVAILABLE, agora - timedelta(minutes=60))
    _event(restaurant.id, mesa.id, EventType.TABLE_OCCUPIED, agora - timedelta(minutes=30))

    assert _service().average_turnover_minutes(restaurant.id) == 25


def test_eventos_antigos_ficam_fora_da_amostra(app, restaurant):
    mesa = make_table(restaurant.id, "1", 4)
    antigo = utcnow() - timedelta(hours=48)
    _event(restaurant.id, mesa.id, EventType.TABLE_AVAILABLE, antigo)
    _event(restaurant.id, mesa.id, EventType.TABLE_OCCUPIED, antigo + timedelta(minutes=90))

    assert _service().average_turnover_minutes(restaurant.id) == 15


def test_historico_de_outro_restaurante_nao_contamina(app, restaurant, other_restaurant):
    mesa = make_table(other_restaurant.id, "1", 4)
    agora = utcnow()
    _event(other_restaurant.id, mesa.id, EventType.TABLE_AVAILABLE, agora - timedelta(minutes=50))
    _event(other_restaurant.id, mesa.id, EventType.TABLE_OCCUPIED, agora - timedelta(minutes=10))

    assert _service().average_turnover_minutes(restaurant.id) == 15


def test_estimativa_e_posicao_vezes_giro(app, restaurant):
    mesa = make_table(restaurant.id, "1", 4)
    agora = utcnow()
    _event(restaurant.id, mesa.id, EventType.TABLE_AVAILABLE, agora - timedelta(minutes=40))
    _event(restaurant.id, mesa.id, EventType.TABLE_OCCUPIED, agora - timedelta(minutes=20))

    service = _service()
    assert service.average_turnover_minutes(restaurant.id) == 20
    assert service.estimate_for_position(restaurant.id, 3) == 60
    assert service.estimate_for_position(restaurant.id, None) is None
    assert service.estimate_for_position(restaurant.id, 0) is None
