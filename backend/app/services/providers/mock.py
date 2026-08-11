"""MockProvider do V0: apenas registra o envio, sempre mascarando o destinatario."""

from __future__ import annotations

import logging
import uuid

from app.logging_utils import mask_phone
from app.services.providers.base import NotificationProvider, SendResult

logger = logging.getLogger(__name__)


class MockProvider(NotificationProvider):
    name = "mock"

    def __init__(self) -> None:
        #: Somente para inspecao em testes/dev; nao e persistencia.
        self.sent: list[tuple[str, str, str]] = []

    def _record(self, channel: str, to: str, message: str) -> SendResult:
        self.sent.append((channel, to, message))
        logger.info("Notificacao %s enviada para %s: %s", channel, mask_phone(to), message)
        return SendResult(success=True, provider_message_id=f"mock-{uuid.uuid4().hex[:12]}")

    def send_whatsapp(self, to: str, message: str) -> SendResult:
        return self._record("WHATSAPP", to, message)

    def send_sms(self, to: str, message: str) -> SendResult:
        return self._record("SMS", to, message)

    def send_web_notification(self, to: str, message: str) -> SendResult:
        return self._record("WEB", to, message)
