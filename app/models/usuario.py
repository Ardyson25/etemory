"""Modelo da tabela ``usuarios``.

Pilar de POO: encapsulamento — a senha só existe como hash no atributo
privado ``_senha_hash``, acessado por ``definir_senha()`` e
``verificar_senha()``. Nenhum código de fora lê ou grava o hash direto.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from flask_login import UserMixin
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from werkzeug.security import check_password_hash, generate_password_hash

from app.domain.enums import ModoComentarios
from app.domain.tempo import agora
from app.domain.validacoes import (
    BIO_MAX,
    NOME_MAX,
    validar_email,
    validar_senha,
    validar_texto,
    validar_url_https,
    validar_username,
)
from app.extensions import db
from app.models.base import coluna_enum

if TYPE_CHECKING:
    from app.models.polaroid import Polaroid


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(NOME_MAX))
    username: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    _senha_hash: Mapped[str] = mapped_column("senha_hash", String(255))
    bio: Mapped[str] = mapped_column(String(BIO_MAX), default="")
    site: Mapped[str | None] = mapped_column(String(255))
    foto: Mapped[str | None] = mapped_column(String(255))
    capa: Mapped[str | None] = mapped_column(String(255))
    conta_privada: Mapped[bool] = mapped_column(default=False)
    modo_comentarios_padrao: Mapped[ModoComentarios] = mapped_column(
        coluna_enum(ModoComentarios), default=ModoComentarios.TODOS
    )
    criado_em: Mapped[datetime] = mapped_column(default=agora)

    polaroids: Mapped[list[Polaroid]] = relationship(back_populates="autor")

    def __init__(self, *, senha: str | None = None, **kwargs: object) -> None:
        kwargs.setdefault("bio", "")
        kwargs.setdefault("conta_privada", False)
        kwargs.setdefault("modo_comentarios_padrao", ModoComentarios.TODOS)
        kwargs.setdefault("criado_em", agora())
        super().__init__(**kwargs)
        if senha is not None:
            self.definir_senha(senha)

    # ---------- Senha (encapsulamento) ----------

    def definir_senha(self, senha: str) -> None:
        """Guarda só o hash da senha (RNF01)."""
        self._senha_hash = generate_password_hash(validar_senha(senha))

    def verificar_senha(self, senha: str) -> bool:
        if not self._senha_hash:
            return False
        return check_password_hash(self._senha_hash, senha)

    # ---------- Validações automáticas ao atribuir ----------

    @validates("username")
    def _validar_username(self, _chave: str, valor: str) -> str:
        return validar_username(valor)  # RN12

    @validates("email")
    def _validar_email(self, _chave: str, valor: str) -> str:
        return validar_email(valor)

    @validates("nome")
    def _validar_nome(self, _chave: str, valor: str) -> str:
        return validar_texto(valor, "O nome", 1, NOME_MAX)

    @validates("bio")
    def _validar_bio(self, _chave: str, valor: str | None) -> str:
        return validar_texto(valor, "A bio", 0, BIO_MAX)

    @validates("site")
    def _validar_site(self, _chave: str, valor: str | None) -> str | None:
        return validar_url_https(valor, "O site")  # RN17

    def __repr__(self) -> str:
        return f"<Usuario @{self.username}>"
