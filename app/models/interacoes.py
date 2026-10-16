"""Curtidas e comentários (partes da composição da Polaroid)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.domain.excecoes import AcessoNegado
from app.domain.tempo import agora
from app.domain.validacoes import COMENTARIO_MAX, validar_texto
from app.extensions import db
from app.models.usuario import Usuario

if TYPE_CHECKING:
    from app.models.notificacao import Notificacao
    from app.models.polaroid import Polaroid


class Curtida(db.Model):
    """RN10: a chave composta garante uma curtida por usuário em cada Polaroid."""

    __tablename__ = "curtidas"

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    polaroid_id: Mapped[int] = mapped_column(
        ForeignKey("polaroids.id", ondelete="CASCADE"), primary_key=True
    )
    criado_em: Mapped[datetime] = mapped_column(default=agora)

    usuario: Mapped[Usuario] = relationship()
    polaroid: Mapped[Polaroid] = relationship(back_populates="curtidas")


class Comentario(db.Model):
    __tablename__ = "comentarios"
    __table_args__ = (
        CheckConstraint(
            f"length(texto) BETWEEN 1 AND {COMENTARIO_MAX}", name="texto_tamanho"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    polaroid_id: Mapped[int] = mapped_column(
        ForeignKey("polaroids.id", ondelete="CASCADE"), index=True
    )
    autor_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    texto: Mapped[str] = mapped_column(String(COMENTARIO_MAX))
    criado_em: Mapped[datetime] = mapped_column(default=agora)
    editado_em: Mapped[datetime | None]

    polaroid: Mapped[Polaroid] = relationship(back_populates="comentarios")
    autor: Mapped[Usuario] = relationship()
    notificacoes: Mapped[list[Notificacao]] = relationship(
        back_populates="comentario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("criado_em", agora())
        super().__init__(**kwargs)

    @validates("texto")
    def _validar_texto(self, _chave: str, valor: str) -> str:
        return validar_texto(valor, "O comentário", 1, COMENTARIO_MAX)  # RN09

    @property
    def foi_editado(self) -> bool:
        return self.editado_em is not None

    def editar(self, novo_texto: str, editor: Usuario) -> None:
        """RN09: só o autor do comentário edita."""
        if editor.id != self.autor_id:
            raise AcessoNegado("Só quem escreveu o comentário pode editá-lo.")
        self.texto = novo_texto
        self.editado_em = agora()

    def pode_ser_editado_por(self, usuario: Usuario) -> bool:
        return usuario.id == self.autor_id

    def pode_ser_excluido_por(self, usuario: Usuario) -> bool:
        """RN09: o autor do comentário ou o dono da Polaroid."""
        return usuario.id in (self.autor_id, self.polaroid.autor_id)
