"""Helpers dos controllers: parsing validado e respostas JSON consistentes."""

from __future__ import annotations

import uuid
from typing import Any, TypeVar

from flask import Response, jsonify, request
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from app.errors import ValidationError

SchemaT = TypeVar("SchemaT", bound=BaseModel)
MAX_BODY_BYTES = 64 * 1024


def parse_body(schema: type[SchemaT]) -> SchemaT:
    """Le o corpo JSON e valida com pydantic (campos extras = 422)."""
    if request.content_length and request.content_length > MAX_BODY_BYTES:
        raise ValidationError("Corpo da requisicao muito grande.")
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValidationError("O corpo deve ser um objeto JSON.")
    try:
        return schema.model_validate(payload)
    except PydanticValidationError as exc:
        raise ValidationError("Dados invalidos.", details=_format_errors(exc)) from exc


def _format_errors(exc: PydanticValidationError) -> list[dict[str, str]]:
    return [
        {"field": ".".join(str(part) for part in error["loc"]) or "body", "message": error["msg"]}
        for error in exc.errors()
    ]


def parse_uuid(value: str, field: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValidationError(f"Identificador invalido em {field}.") from exc


def json_response(data: Any, status: int = 200) -> tuple[Response, int]:
    return jsonify(data), status


def serialize(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")


def serialize_many(models: list[BaseModel]) -> list[dict[str, Any]]:
    return [model.model_dump(mode="json") for model in models]
