"""Modelo da tabela ``vinculos`` (quem segue quem).

Pilar de POO: encapsulamento — o status só muda pelos métodos ``aceitar()``,
``recusar()``, ``cancelar()`` e ``reabrir()``, que validam a transição.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import StatusVinculo
from app.domain.excecoes import ErroDeNegocio, TransicaoInvalida
from app.domain.tempo import agora
from app.extensions import db
from app.models.base import coluna_enum
from app.models.usuario import Usuario


class Vinculo(db.Model):
    __tablename__ = "vinculos"
    __table_args__ = (
        UniqueConstraint("seguidor_id", "seguido_id", name="uq_vinculos_par"),
        CheckConstraint("seguidor_id <> seguido_id", name="nao_segue_a_si"),
        Index("ix_vinculos_seguido_status", "seguido_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    seguidor_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    seguido_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    _status: Mapped[StatusVinculo] = mapped_column(
        "status", coluna_enum(StatusVinculo)
    )
    melhor_amigo: Mapped[bool] = mapped_column(default=False)
    criado_em: Mapped[datetime] = mapped_column(default=agora)
    respondido_em: Mapped[datetime | None]

    seguidor: Mapped[Usuario] = relationship(foreign_keys=[seguidor_id])
    seguido: Mapped[Usuario] = relationship(foreign_keys=[seguido_id])

    @classmethod
    def criar(cls, seguidor: Usuario, seguido: Usuario) -> Vinculo:
        """RN07: conta privada gera solicitação; conta pública, vínculo aceito."""
        if seguidor.id == seguido.id:
            raise ErroDeNegocio("Você não pode seguir a si mesmo.")  # RN15
        vinculo = cls(
            seguidor=seguidor,
            seguido=seguido,
            seguidor_id=seguidor.id,
            seguido_id=seguido.id,
            melhor_amigo=False,
            criado_em=agora(),
        )
        vinculo._entrar_em(seguido.conta_privada)
        return vinculo

    @hybrid_property
    def status(self) -> StatusVinculo:
        return self._status

    @property
    def esta_ativo(self) -> bool:
        return self._status is StatusVinculo.ACEITO

    @property
    def esta_pendente(self) -> bool:
        return self._status is StatusVinculo.PENDENTE

    # ---------- Transições ----------

    def _entrar_em(self, conta_privada: bool) -> None:
        if conta_privada:
            self._status = StatusVinculo.PENDENTE
            self.respondido_em = None
        else:
            self._status = StatusVinculo.ACEITO
            self.respondido_em = agora()

    def _exigir_pendente(self) -> None:
        if self._status is not StatusVinculo.PENDENTE:
            raise TransicaoInvalida("Esta solicitação não está mais pendente.")

    def aceitar(self) -> None:
        self._exigir_pendente()
        self._status = StatusVinculo.ACEITO
        self.respondido_em = agora()

    def recusar(self) -> None:
        self._exigir_pendente()
        self._status = StatusVinculo.RECUSADO
        self.respondido_em = agora()

    def cancelar(self) -> None:
        """RN07: só quem pediu cancela, e só enquanto pendente."""
        self._exigir_pendente()
        self._status = StatusVinculo.CANCELADO
        self.respondido_em = agora()

    def reabrir(self, conta_privada: bool) -> None:
        """RC06: depois de recusado ou cancelado, pode pedir de novo."""
        if self._status not in (StatusVinculo.RECUSADO, StatusVinculo.CANCELADO):
            raise TransicaoInvalida("Este vínculo já está ativo ou pendente.")
        self.melhor_amigo = False
        self.criado_em = agora()
        self._entrar_em(conta_privada)

    def marcar_melhor_amigo(self) -> None:
        """RN06: melhor amigo precisa ser seguidor aceito."""
        if not self.esta_ativo:
            raise ErroDeNegocio("Só seguidores podem ser melhores amigos.")
        self.melhor_amigo = True

    def desmarcar_melhor_amigo(self) -> None:
        self.melhor_amigo = False
