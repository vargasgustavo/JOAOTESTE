from __future__ import annotations

import re
import uuid
from typing import Annotated

from pydantic import EmailStr, Field, StringConstraints, field_validator

from app.models import Role
from app.schemas.common import NameStr, ResponseSchema, StrictSchema, normalize_phone

PasswordStr = Annotated[str, StringConstraints(min_length=12, max_length=128)]


class RegisterRequest(StrictSchema):
    """Auto-cadastro publico cria SEMPRE um CUSTOMER; roles internas so via admin."""

    email: EmailStr
    password: PasswordStr
    full_name: NameStr
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("email")
    @classmethod
    def _lower(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def _strength(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("A senha deve conter letras e numeros.")
        return value

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value else None


class LoginRequest(StrictSchema):
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]

    @field_validator("email")
    @classmethod
    def _lower(cls, value: str) -> str:
        return value.strip().lower()


class StaffCreateRequest(StrictSchema):
    """Criacao de STAFF/RESTAURANT_ADMIN dentro do proprio restaurante."""

    email: EmailStr
    password: PasswordStr
    full_name: NameStr
    role: Role

    @field_validator("email")
    @classmethod
    def _lower(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("role")
    @classmethod
    def _role(cls, value: Role) -> Role:
        if value == Role.CUSTOMER:
            raise ValueError("Use o cadastro publico para clientes.")
        return value


class UserResponse(ResponseSchema):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: Role
    restaurant_id: uuid.UUID | None = None


class CsrfResponse(ResponseSchema):
    csrf_token: str
