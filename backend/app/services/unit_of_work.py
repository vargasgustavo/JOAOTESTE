"""Unidade de trabalho: commit atomico + efeitos colaterais somente apos o commit."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from flask import g
from sqlalchemy.orm import Session

from app.extensions import db

AfterCommitHook = Callable[[], None]


def after_commit(hook: AfterCommitHook) -> None:
    """Agenda um efeito externo (ex.: enfileirar notificacao) para depois do commit."""
    hooks: list[AfterCommitHook] = getattr(g, "_after_commit_hooks", [])
    hooks.append(hook)
    g._after_commit_hooks = hooks


def _run_after_commit_hooks() -> None:
    hooks: list[AfterCommitHook] = getattr(g, "_after_commit_hooks", [])
    g._after_commit_hooks = []
    for hook in hooks:
        try:
            hook()
        except Exception:  # pragma: no cover - efeito externo nunca quebra a request
            from flask import current_app

            current_app.logger.exception("Falha ao executar hook pos-commit.")


@contextmanager
def transaction() -> Iterator[Session]:
    """Envolve um caso de uso inteiro em uma unica transacao."""
    session = db.s
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        g._after_commit_hooks = []
        raise
    _run_after_commit_hooks()
