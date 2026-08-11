"""Logging estruturado com mascaramento obrigatorio de telefone e e-mail."""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE_RE = re.compile(r"(?<!\w)(\+?\d[\d\s().-]{6,}\d)(?!\w)")


def mask_email(value: str | None) -> str:
    if not value or "@" not in value:
        return "***"
    local, _, domain = value.partition("@")
    head = local[0] if local else "*"
    return f"{head}***@{domain}"


def mask_phone(value: str | None) -> str:
    if not value:
        return "***"
    digits = re.sub(r"\D", "", value)
    if len(digits) <= 4:
        return "***"
    return f"***{digits[-4:]}"


def scrub(text: str) -> str:
    """Remove PII de mensagens livres antes de irem para o log."""
    text = EMAIL_RE.sub(lambda m: f"{m.group(1)}***{m.group(2)}", text)
    return PHONE_RE.sub(lambda m: mask_phone(m.group(1)), text)


class PIIFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = scrub(str(record.msg))
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: _scrub_any(v) for k, v in record.args.items()}
                else:
                    record.args = tuple(_scrub_any(a) for a in record.args)
        except Exception:  # pragma: no cover - logging nunca deve derrubar a request
            return True
        return True


def _scrub_any(value: Any) -> Any:
    return scrub(value) if isinstance(value, str) else value


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    handler.addFilter(PIIFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
