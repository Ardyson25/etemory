"""Notificações com herança de tabela única (single table inheritance).

Pilares de POO:
- Herança: cada tipo de notificação é uma subclasse de ``Notificacao`` e
  herda as colunas comuns.
- Polimorfismo: a tela chama ``notificacao.texto()`` e ``notificacao.link()``
  sem saber o tipo; cada subclasse responde do seu jeito.
- No banco: uma tabela só, e a coluna ``tipo`` (``polymorphic_on``) diz ao
  SQLAlchemy qual subclasse criar ao ler cada linha.

``Notificacao`` é abstrata por convenção: o SQLAlchemy não aceita ``ABC``
junto com o modelo, então ``texto()`` e ``link()`` lançam
``NotImplementedError`` na classe base.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from flask import url_for
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import TipoNotificacao
from app.domain.tempo import agora
from app.extensions import db
from app.models.usuario import Usuario

if TYPE_CHECKING:
    from app.models.interacoes import Comentario
    from app.models.polaroid import Polaroid


class Notificacao(db.Model):
    __tablename__ = "notificacoes"
    __table_args__ = (
        Index("ix_notificacoes_destinatario_lida", "destinatario_id", "lida"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(30))
    destinatario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    remetente_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    polaroid_id: Mapped[int | None] = mapped_column(
        ForeignKey("polaroids.id", ondelete="CASCADE")
    )
    comentario_id: Mapped[int | None] = mapped_column(
        ForeignKey("comentarios.id", ondelete="CASCADE")
    )
    lida: Mapped[bool] = mapped_column(default=False)
    criado_em: Mapped[datetime] = mapped_column(default=agora, index=True)

    destinatario: Mapped[Usuario] = relationship(foreign_keys=[destinatario_id])
    remetente: Mapped[Usuario] = relationship(foreign_keys=[remetente_id])
    polaroid: Mapped[Polaroid | None] = relationship(back_populates="notificacoes")
    comentario: Mapped[Comentario | None] = relationship(
        back_populates="notificacoes"
    )

    __mapper_args__ = {"polymorphic_on": "tipo", "polymorphic_identity": "base"}

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("lida", False)
        kwargs.setdefault("criado_em", agora())
        super().__init__(**kwargs)

    def texto(self) -> str:
        raise NotImplementedError

    def link(self) -> str:
        raise NotImplementedError

    def marcar_como_lida(self) -> None:
        self.lida = True

    @property
    def _quem(self) -> str:
        return f"@{self.remetente.username}"


class NotificacaoCurtida(Notificacao):
    __mapper_args__ = {"polymorphic_identity": TipoNotificacao.CURTIDA.value}

    def texto(self) -> str:
        return f"{self._quem} curtiu sua memória."

    def link(self) -> str:
        return url_for("polaroids.detalhe", polaroid_id=self.polaroid_id)


class NotificacaoComentario(Notificacao):
    __mapper_args__ = {"polymorphic_identity": TipoNotificacao.COMENTARIO.value}

    def texto(self) -> str:
        return f"{self._quem} comentou na sua memória."

    def link(self) -> str:
        return url_for(
            "polaroids.detalhe",
            polaroid_id=self.polaroid_id,
            _anchor=f"comentario-{self.comentario_id}",
        )


class NotificacaoSeguidor(Notificacao):
    __mapper_args__ = {"polymorphic_identity": TipoNotificacao.SEGUIDOR.value}

    def texto(self) -> str:
        return f"{self._quem} criou um vínculo com você."

    def link(self) -> str:
        return url_for("perfil.prontuario", username=self.remetente.username)


class NotificacaoSolicitacao(Notificacao):
    __mapper_args__ = {"polymorphic_identity": TipoNotificacao.SOLICITACAO.value}

    def texto(self) -> str:
        return f"{self._quem} pediu para criar um vínculo com você."

    def link(self) -> str:
        return url_for("perfil.solicitacoes")


class NotificacaoSolicitacaoAceita(Notificacao):
    __mapper_args__ = {
        "polymorphic_identity": TipoNotificacao.SOLICITACAO_ACEITA.value
    }

    def texto(self) -> str:
        return f"{self._quem} aceitou sua solicitação de vínculo."

    def link(self) -> str:
        return url_for("perfil.prontuario", username=self.remetente.username)


class NotificacaoMencao(Notificacao):
    __mapper_args__ = {"polymorphic_identity": TipoNotificacao.MENCAO.value}

    def texto(self) -> str:
        onde = "num comentário" if self.comentario_id else "numa memória"
        return f"{self._quem} mencionou você {onde}."

    def link(self) -> str:
        anchor = f"comentario-{self.comentario_id}" if self.comentario_id else None
        return url_for("polaroids.detalhe", polaroid_id=self.polaroid_id, _anchor=anchor)
