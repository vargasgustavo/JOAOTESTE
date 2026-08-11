"""Concorrencia: duas liberacoes simultaneas nunca chamam o mesmo cliente.

O teste com threads exige PostgreSQL (FOR UPDATE SKIP LOCKED); em SQLite ele e
pulado, mas os testes logicos de dupla liberacao rodam em qualquer banco.
"""

from __future__ import annotations

import os
import threading

import pytest

from app.extensions import db
from app.models import QueueStatus, TableStatus
from tests.conftest import STAFF_PASSWORD, make_queue_entry, make_table

requires_postgres = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL", "").startswith("postgresql"),
    reason="SELECT FOR UPDATE SKIP LOCKED exige PostgreSQL (defina TEST_DATABASE_URL).",
)


def test_duas_liberacoes_chamam_clientes_diferentes(api, restaurant, staff):
    mesa_a = make_table(restaurant.id, "1", 4, TableStatus.CLEANING)
    mesa_b = make_table(restaurant.id, "2", 4, TableStatus.CLEANING)
    make_queue_entry(restaurant.id, "Joao", "+5511900002001", 4, 1)
    make_queue_entry(restaurant.id, "Maria", "+5511900002002", 2, 2)

    api.login(staff.email, STAFF_PASSWORD)
    primeiro = api.post(f"/tables/{mesa_a.id}/release").get_json()
    segundo = api.post(f"/tables/{mesa_b.id}/release").get_json()

    chamados = {primeiro["allocation"]["customer_name"], segundo["allocation"]["customer_name"]}
    assert chamados == {"Joao", "Maria"}


def test_liberar_a_mesma_mesa_duas_vezes_nao_chama_dois_clientes(api, restaurant, staff):
    mesa = make_table(restaurant.id, "1", 4, TableStatus.CLEANING)
    make_queue_entry(restaurant.id, "Joao", "+5511900002011", 4, 1)
    make_queue_entry(restaurant.id, "Maria", "+5511900002012", 2, 2)

    api.login(staff.email, STAFF_PASSWORD)
    assert api.post(f"/tables/{mesa.id}/release").status_code == 200
    # A mesa ficou RESERVED: uma segunda liberacao e transicao invalida.
    repetida = api.post(f"/tables/{mesa.id}/release")
    assert repetida.status_code == 409

    from app.models import QueueEntry

    chamados = db.s.query(QueueEntry).filter_by(status=QueueStatus.CALLED).count()
    assert chamados == 1


def test_uma_mesa_para_dois_grupos_chama_apenas_o_primeiro(api, restaurant, staff):
    make_table(restaurant.id, "1", 4, TableStatus.AVAILABLE)
    api.login(staff.email, STAFF_PASSWORD)

    primeiro = api.post(
        f"/restaurants/{restaurant.id}/queue",
        json={"customer_name": "Joao", "customer_phone": "+5511900002021", "party_size": 4},
    ).get_json()
    segundo = api.post(
        f"/restaurants/{restaurant.id}/queue",
        json={"customer_name": "Maria", "customer_phone": "+5511900002022", "party_size": 2},
    ).get_json()

    assert primeiro["status"] == QueueStatus.CALLED.value
    assert segundo["status"] == QueueStatus.WAITING.value


@requires_postgres
def test_liberacoes_simultaneas_em_threads_nao_duplicam_chamada(app, restaurant, staff):
    """Duas mesas liberadas ao mesmo tempo, dois clientes na fila: um cada."""
    mesa_a = make_table(restaurant.id, "1", 4, TableStatus.CLEANING)
    mesa_b = make_table(restaurant.id, "2", 4, TableStatus.CLEANING)
    make_queue_entry(restaurant.id, "Joao", "+5511900002031", 4, 1)
    make_queue_entry(restaurant.id, "Maria", "+5511900002032", 2, 2)
    staff_id, restaurant_id = staff.id, restaurant.id
    db.s.commit()

    largada = threading.Barrier(2)
    resultados: list[str | None] = []
    erros: list[BaseException] = []

    def liberar(table_id) -> None:
        from app.services import TableService, transaction
        from app.services.wait_time_service import WaitTimeService

        try:
            with app.app_context():
                largada.wait(timeout=10)
                with transaction() as session:
                    service = TableService(session, WaitTimeService(session))
                    _, allocation = service.release_table(table_id, restaurant_id, staff_id)
                resultados.append(allocation.customer_name if allocation else None)
                db.session.remove()
        except BaseException as exc:  # pragma: no cover - so aparece em falha real
            erros.append(exc)

    threads = [threading.Thread(target=liberar, args=(tid,)) for tid in (mesa_a.id, mesa_b.id)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert not erros, erros
    assert sorted(filter(None, resultados)) == ["Joao", "Maria"]

    from app.models import QueueEntry

    db.s.expire_all()
    chamados = db.s.query(QueueEntry).filter_by(status=QueueStatus.CALLED).all()
    assert len(chamados) == 2
    # Cada cliente foi para uma mesa distinta.
    assert len({entry.assigned_table_id for entry in chamados}) == 2


@requires_postgres
def test_entradas_simultaneas_disputando_uma_unica_mesa(app, restaurant):
    """Dois clientes entram ao mesmo tempo com uma unica mesa livre: so um e chamado."""
    make_table(restaurant.id, "1", 4, TableStatus.AVAILABLE)
    restaurant_id = restaurant.id
    db.s.commit()

    largada = threading.Barrier(2)
    status: list[str] = []
    erros: list[BaseException] = []

    def entrar(nome: str, telefone: str) -> None:
        from app.schemas.queue import QueueJoinRequest
        from app.services import QueueService, transaction
        from app.services.wait_time_service import WaitTimeService

        try:
            with app.app_context():
                largada.wait(timeout=10)
                with transaction() as session:
                    service = QueueService(session, WaitTimeService(session))
                    entry, _ = service.join(
                        restaurant_id,
                        QueueJoinRequest(
                            customer_name=nome, customer_phone=telefone, party_size=2
                        ),
                    )
                    resultado = entry.status.value
                status.append(resultado)
                db.session.remove()
        except BaseException as exc:  # pragma: no cover
            erros.append(exc)

    threads = [
        threading.Thread(target=entrar, args=("Joao", "+5511900002041")),
        threading.Thread(target=entrar, args=("Maria", "+5511900002042")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert not erros, erros
    assert sorted(status) == [QueueStatus.CALLED.value, QueueStatus.WAITING.value]
