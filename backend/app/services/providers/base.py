"""Contrato de provedor de notificacao. Trocar de provedor nao altera o restante do app."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SendResult:
    success: bool
    provider_message_id: str | None = None
    error: str | None = None


class NotificationProvider(ABC):
    """Interface unica; implementacoes reais (Twilio, Zenvia...) entram sem tocar services."""

    name = "base"

    @abstractmethod
    def send_whatsapp(self, to: str, message: str) -> SendResult: ...

    @abstractmethod
    def send_sms(self, to: str, message: str) -> SendResult: ...

    @abstractmethod
    def send_web_notification(self, to: str, message: str) -> SendResult: ...
