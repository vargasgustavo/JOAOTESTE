"""Notificacoes: mensagem, provider plugavel e resiliencia quando o broker cai."""

from __future__ import annotations

from app.extensions import db
from app.models import Notification, NotificationStatus, TableStatus
from app.services.notification_service import build_table_ready_message
from app.services.providers import get_provider
from tests.conftest import STAFF_PASSWORD, make_queue_entry, make_table


def test_mensagem_segue_o_texto_do_produto():
    mensagem = build_table_ready_message("Joao Almeida", "Restaurante X")
    assert mensagem == "Ola, Joao! Sua mesa esta pronta no Restaurante X. Dirija-se a recepcao."


def test_liberar_mesa_gera_notificacao_enviada_pelo_provider(api, restaurant, staff):
    mesa = make_table(restaurant.id, "1", 4, TableStatus.CLEANING)
    entry = make_queue_entry(restaurant.id, "Joao Almeida", "+5511900004001", 4, 1)

    api.login(staff.email, STAFF_PASSWORD)
    assert api.post(f"/tables/{mesa.id}/release").status_code == 200

    notification = db.s.query(Notification).filter_by(queue_entry_id=entry.id).one()
    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at is not None
    assert "Sua mesa esta pronta" in notification.message

    enviados = get_provider("mock").sent
    assert len(enviados) == 1
    canal, destinatario, _ = enviados[0]
    assert canal == "WHATSAPP"
    assert destinatario == "+5511900004001"


def test_broker_indisponivel_nao_quebra_a_liberacao(api, restaurant, staff, monkeypatch):
    """Se o Celery falhar, a mesa continua liberada e a notificacao fica PENDING."""
    from app.tasks import notifications as tasks

    def explode(*args, **kwargs):  # noqa: ANN002, ANN003
        raise ConnectionError("broker fora do ar")

    monkeypatch.setattr(tasks.send_notification_task, "apply_async", explode)

    mesa = make_table(restaurant.id, "1", 4, TableStatus.CLEANING)
    entry = make_queue_entry(restaurant.id, "Joao", "+5511900004011", 4, 1)

    api.login(staff.email, STAFF_PASSWORD)
    response = api.post(f"/tables/{mesa.id}/release")

    assert response.status_code == 200
    assert response.get_json()["allocation"]["customer_name"] == "Joao"

    notification = db.s.query(Notification).filter_by(queue_entry_id=entry.id).one()
    assert notification.status == NotificationStatus.PENDING


def test_telefone_e_mascarado_nos_logs():
    from app.logging_utils import mask_email, mask_phone, scrub

    assert mask_phone("+5511999998888") == "***8888"
    assert mask_email("cliente@exemplo.com") == "c***@exemplo.com"
    # Mensagens livres tambem sao limpas antes de chegar ao log.
    limpo = scrub("cliente joao@exemplo.com pelo telefone +5511999998888")
    assert "joao@exemplo.com" not in limpo
    assert "999998888" not in limpo
