"""Álbuns de Polaroids.

Pilar de POO: agregação — o álbum só referencia as Polaroids pela tabela
``album_polaroid``. Excluir o álbum apaga as linhas dessa tabela, mas as
Polaroids continuam existindo (RN13).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.domain.enums import Visibilidade
from app.domain.excecoes import AcessoNegado, ErroDeNegocio
from app.domain.tempo import agora
from app.domain.validacoes import DESCRICAO_ALBUM_MAX, TITULO_ALBUM_MAX, validar_texto
from app.extensions import db
from app.models.base import coluna_enum
from app.models.usuario import Usuario

if TYPE_CHECKING:
    from app.models.polaroid import Polaroid

album_polaroid = Table(
    "album_polaroid",
    db.metadata,
    Column(
        "album_id",
        ForeignKey("albuns.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "polaroid_id",
        ForeignKey("polaroids.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("adicionada_em", db.DateTime, default=agora, nullable=False),
)


class Album(db.Model):
    __tablename__ = "albuns"
    __table_args__ = (
        CheckConstraint(
            f"length(titulo) BETWEEN 1 AND {TITULO_ALBUM_MAX}", name="titulo_tamanho"
        ),
    )

    VISIBILIDADES_PERMITIDAS = (Visibilidade.PUBLICA, Visibilidade.SOMENTE_EU)

    id: Mapped[int] = mapped_column(primary_key=True)
    dono_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    titulo: Mapped[str] = mapped_column(String(TITULO_ALBUM_MAX))
    descricao: Mapped[str] = mapped_column(String(DESCRICAO_ALBUM_MAX), default="")
    visibilidade: Mapped[Visibilidade] = mapped_column(coluna_enum(Visibilidade))
    criado_em: Mapped[datetime] = mapped_column(default=agora)

    dono: Mapped[Usuario] = relationship()
    polaroids: Mapped[list[Polaroid]] = relationship(
        secondary=album_polaroid,
        back_populates="albuns",
        order_by=album_polaroid.c.adicionada_em.desc(),
    )

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("descricao", "")
        kwargs.setdefault("visibilidade", Visibilidade.PUBLICA)
        kwargs.setdefault("criado_em", agora())
        super().__init__(**kwargs)

    @property
    def eh_publico(self) -> bool:
        return self.visibilidade is Visibilidade.PUBLICA

    @validates("titulo")
    def _validar_titulo(self, _chave: str, valor: str) -> str:
        return validar_texto(valor, "O título do álbum", 1, TITULO_ALBUM_MAX)  # RN13

    @validates("descricao")
    def _validar_descricao(self, _chave: str, valor: str | None) -> str:
        return validar_texto(valor, "A descrição", 0, DESCRICAO_ALBUM_MAX)

    @validates("visibilidade")
    def _validar_visibilidade(self, _chave: str, valor: Visibilidade) -> Visibilidade:
        if valor not in self.VISIBILIDADES_PERMITIDAS:
            raise ErroDeNegocio("O álbum deve ser público ou privado.")
        return valor

    def adicionar(self, polaroid: Polaroid) -> None:
        """RC03: só as próprias Polaroids entram no álbum."""
        if polaroid.autor_id != self.dono_id:
            raise AcessoNegado("Você só pode adicionar as suas memórias.")
        if polaroid not in self.polaroids:
            self.polaroids.append(polaroid)

    def remover(self, polaroid: Polaroid) -> None:
        if polaroid in self.polaroids:
            self.polaroids.remove(polaroid)
