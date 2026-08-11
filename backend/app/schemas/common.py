"""Base dos schemas: entrada estrita (rejeita campos extras) e saida serializavel."""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

PHONE_RE = re.compile(r"^\+?\d{10,15}$")

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
TableNumberStr = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=16)
]


class StrictSchema(BaseModel):
    """Toda entrada da API herda daqui: campos desconhecidos viram erro 422."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        frozen=True,
    )


class ResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def normalize_phone(value: str) -> str:
    """Mantem apenas digitos (e um + inicial) para armazenamento consistente."""
    cleaned = re.sub(r"[\s()\-.]", "", value or "")
    if not PHONE_RE.match(cleaned):
        raise ValueError("Telefone invalido. Use DDI/DDD e apenas digitos, ex.: +5511999998888")
    return cleaned
