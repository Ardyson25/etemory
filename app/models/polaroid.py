"""Modelos da Polaroid e das partes que a compõem.

Pilares de POO:
- Encapsulamento: o status só muda por ``arquivar()``, ``desarquivar()``,
  ``mover_para_lixeira()`` e ``restaurar()``, que validam a transição.
  Valores calculados usam ``@property`` (ex.: ``dias_restantes_na_lixeira``).
- Composição: ``Midia``, ``Comentario``, ``Curtida`` e as emoções só existem
  dentro da Polaroid (``cascade="all, delete-orphan"`` + ``ON DELETE
  CASCADE``). Apagar a Polaroid apaga tudo isso junto (RN14).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.domain.enums import (
    Emocao,
    EstadoMemoria,
    ModoComentarios,
    StatusPolaroid,
    Visibilidade,
)
from app.domain.excecoes import ErroDeNegocio, TransicaoInvalida
from app.domain.tempo import agora
from app.domain.validacoes import (
    DIAS_NA_LIXEIRA,
    LEGENDA_MAX,
    MAX_EMOCOES,
    validar_texto,
    validar_url_https,
)
from app.domain.visibilidade import resolver_visibilidade
from app.extensions import db
from app.models.base import coluna_enum

if TYPE_CHECKING:
    from app.models.album import Album
    from app.models.interacoes import Comentario, Curtida
    from app.models.notificacao import Notificacao
    from app.models.usuario import Usuario


class Midia(db.Model):
    """Foto da Polaroid (parte da composição)."""

    __tablename__ = "midias"

    id: Mapped[int] = mapped_column(primary_key=True)
    polaroid_id: Mapped[int] = mapped_column(
        ForeignKey("polaroids.id", ondelete="CASCADE"), index=True
    )
    caminho_arquivo: Mapped[str] = mapped_column(String(255))
    ordem: Mapped[int] = mapped_column(default=0)
    largura: Mapped[int]
    altura: Mapped[int]

    polaroid: Mapped[Polaroid] = relationship(back_populates="midias")


class PolaroidEmocao(db.Model):
    """Uma emoção marcada numa Polaroid (até 3 por Polaroid, RN11)."""

    __tablename__ = "polaroid_emocoes"

    polaroid_id: Mapped[int] = mapped_column(
        ForeignKey("polaroids.id", ondelete="CASCADE"), primary_key=True
    )
    emocao: Mapped[Emocao] = mapped_column(coluna_enum(Emocao), primary_key=True)


class Polaroid(db.Model):
    __tablename__ = "polaroids"
    __table_args__ = (Index("ix_polaroids_autor_criado", "autor_id", "criado_em"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    autor_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    legenda: Mapped[str] = mapped_column(Text)
    data_memoria: Mapped[date | None]
    estado: Mapped[EstadoMemoria] = mapped_column(coluna_enum(EstadoMemoria))
    visibilidade: Mapped[Visibilidade] = mapped_column(coluna_enum(Visibilidade))
    modo_comentarios: Mapped[ModoComentarios] = mapped_column(
        coluna_enum(ModoComentarios)
    )
    musica_titulo: Mapped[str | None] = mapped_column(String(120))
    musica_artista: Mapped[str | None] = mapped_column(String(120))
    musica_url: Mapped[str | None] = mapped_column(String(255))
    local_nome: Mapped[str | None] = mapped_column(String(120))
    _status: Mapped[StatusPolaroid] = mapped_column(
        "status", coluna_enum(StatusPolaroid), index=True
    )
    arquivada_em: Mapped[datetime | None]
    excluida_em: Mapped[datetime | None]
    criado_em: Mapped[datetime] = mapped_column(index=True)
    editado_em: Mapped[datetime | None]

    autor: Mapped[Usuario] = relationship(back_populates="polaroids")
    midias: Mapped[list[Midia]] = relationship(
        back_populates="polaroid",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Midia.ordem",
    )
    _emocoes: Mapped[list[PolaroidEmocao]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    comentarios: Mapped[list[Comentario]] = relationship(
        back_populates="polaroid",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Comentario.criado_em",
    )
    curtidas: Mapped[list[Curtida]] = relationship(
        back_populates="polaroid", cascade="all, delete-orphan", passive_deletes=True
    )
    notificacoes: Mapped[list[Notificacao]] = relationship(
        back_populates="polaroid", cascade="all, delete-orphan", passive_deletes=True
    )
    # Agregação: o álbum só aponta para a Polaroid (ver models/album.py).
    albuns: Mapped[list[Album]] = relationship(
        secondary="album_polaroid", back_populates="polaroids"
    )

    def __init__(self, *, emocoes: Iterable[Emocao] = (), **kwargs: object) -> None:
        kwargs.setdefault("estado", EstadoMemoria.PRESERVADA)
        kwargs.setdefault("visibilidade", Visibilidade.AUTOMATICA)
        kwargs.setdefault("modo_comentarios", ModoComentarios.TODOS)
        kwargs.setdefault("criado_em", agora())
        super().__init__(**kwargs)
        self._status = StatusPolaroid.ATIVA
        self.definir_emocoes(emocoes)

    # ---------- Leitura ----------

    @hybrid_property
    def status(self) -> StatusPolaroid:
        """Só leitura: para mudar, use os métodos de transição."""
        return self._status

    @property
    def visibilidade_efetiva(self) -> Visibilidade:
        """RN03 resolvida na hora da leitura (RC05)."""
        return resolver_visibilidade(self.visibilidade, self.autor.conta_privada)

    @property
    def emocoes(self) -> list[Emocao]:
        return [item.emocao for item in self._emocoes]

    @property
    def foi_editada(self) -> bool:
        return self.editado_em is not None

    @property
    def foto(self) -> Midia | None:
        return self.midias[0] if self.midias else None

    @property
    def dias_restantes_na_lixeira(self) -> int:
        if self._status is not StatusPolaroid.LIXEIRA or self.excluida_em is None:
            return 0
        passados = (agora() - self.excluida_em).days
        return max(0, DIAS_NA_LIXEIRA - passados)

    # ---------- Alteração de conteúdo ----------

    def definir_emocoes(self, emocoes: Iterable[Emocao]) -> None:
        """RN11: no máximo 3 emoções, sem repetição."""
        novas = list(dict.fromkeys(emocoes))
        if len(novas) > MAX_EMOCOES:
            raise ErroDeNegocio(f"Escolha no máximo {MAX_EMOCOES} emoções.")
        # Mantém as que continuam e troca só o que mudou.
        self._emocoes = [e for e in self._emocoes if e.emocao in novas]
        atuais = {e.emocao for e in self._emocoes}
        for emocao in novas:
            if emocao not in atuais:
                self._emocoes.append(PolaroidEmocao(emocao=emocao))

    def marcar_como_editada(self) -> None:
        self.editado_em = agora()

    @validates("legenda")
    def _validar_legenda(self, _chave: str, valor: str) -> str:
        return validar_texto(valor, "A legenda", 1, LEGENDA_MAX)  # RN11

    @validates("musica_url")
    def _validar_musica_url(self, _chave: str, valor: str | None) -> str | None:
        return validar_url_https(valor, "O link da música")  # RN17

    @validates("musica_titulo", "musica_artista", "local_nome")
    def _validar_textos_opcionais(self, chave: str, valor: str | None) -> str | None:
        valor = (valor or "").strip()
        if len(valor) > 120:
            raise ErroDeNegocio("Música e local podem ter no máximo 120 caracteres.")
        return valor or None

    # ---------- Transições de status ----------

    def arquivar(self) -> None:
        if self._status is not StatusPolaroid.ATIVA:
            raise TransicaoInvalida("Só memórias ativas podem ser arquivadas.")
        self._status = StatusPolaroid.ARQUIVADA
        self.arquivada_em = agora()

    def desarquivar(self) -> None:
        if self._status is not StatusPolaroid.ARQUIVADA:
            raise TransicaoInvalida("Esta memória não está arquivada.")
        self._status = StatusPolaroid.ATIVA
        self.arquivada_em = None

    def mover_para_lixeira(self) -> None:
        if self._status is StatusPolaroid.LIXEIRA:
            raise TransicaoInvalida("Esta memória já está na Lixeira.")
        self._status = StatusPolaroid.LIXEIRA
        self.excluida_em = agora()

    def restaurar(self) -> None:
        """RN14: volta como ativa se estiver na Lixeira há até 30 dias."""
        if self._status is not StatusPolaroid.LIXEIRA:
            raise TransicaoInvalida("Esta memória não está na Lixeira.")
        if self.expirou_na_lixeira():
            raise TransicaoInvalida("O prazo de 30 dias para restaurar já acabou.")
        self._status = StatusPolaroid.ATIVA
        self.excluida_em = None
        self.arquivada_em = None

    def expirou_na_lixeira(self, referencia: datetime | None = None) -> bool:
        if self._status is not StatusPolaroid.LIXEIRA or self.excluida_em is None:
            return False
        return ((referencia or agora()) - self.excluida_em).days >= DIAS_NA_LIXEIRA

    def __repr__(self) -> str:
        return f"<Polaroid {self.id} de {self.autor_id}>"
