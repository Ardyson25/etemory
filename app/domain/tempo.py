"""Relógio único da aplicação.

Todas as datas são gravadas em UTC sem fuso (naive). Assim o PostgreSQL e o
SQLite dos testes se comportam igual nas comparações.
"""

from datetime import UTC, datetime


def agora() -> datetime:
    """Data e hora atual em UTC, sem informação de fuso."""
    return datetime.now(UTC).replace(tzinfo=None)
