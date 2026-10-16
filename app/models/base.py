"""Ajudantes comuns aos modelos."""

from enum import Enum

from sqlalchemy import Enum as SAEnum


def coluna_enum(tipo: type[Enum]) -> SAEnum:
    """Grava o NOME do membro do enum num VARCHAR.

    ``native_enum=False`` evita criar tipos ENUM no PostgreSQL, que exigem
    migração especial para receber valores novos.
    """
    return SAEnum(tipo, native_enum=False, length=20, validate_strings=True)
