from __future__ import annotations

from app.services.providers.base import NotificationProvider, SendResult
from app.services.providers.mock import MockProvider

_PROVIDERS: dict[str, NotificationProvider] = {}


def get_provider(name: str = "mock") -> NotificationProvider:
    """Fabrica simples; adicionar um provedor real e registrar uma nova chave aqui."""
    key = (name or "mock").lower()
    if key not in _PROVIDERS:
        if key != "mock":
            raise ValueError(f"Provedor de notificacao desconhecido: {name}")
        _PROVIDERS[key] = MockProvider()
    return _PROVIDERS[key]


def reset_providers() -> None:
    """Usado por testes para limpar o estado do MockProvider."""
    _PROVIDERS.clear()


__all__ = ["MockProvider", "NotificationProvider", "SendResult", "get_provider", "reset_providers"]
