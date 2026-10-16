"""Tabela ``arquivos``: bytes das imagens quando ``ARMAZENAMENTO=banco``.

Usada na publicação online (Fase 3), em que o disco do servidor é
temporário. Na Fase 4 as imagens ficam em disco e esta tabela fica vazia.
"""

from datetime import datetime

from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.tempo import agora
from app.extensions import db


class Arquivo(db.Model):
    __tablename__ = "arquivos"

    nome: Mapped[str] = mapped_column(String(255), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(50))
    tamanho: Mapped[int]
    dados: Mapped[bytes] = mapped_column(LargeBinary)
    criado_em: Mapped[datetime] = mapped_column(default=agora)
