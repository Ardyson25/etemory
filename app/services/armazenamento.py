"""Onde os arquivos de imagem ficam guardados.

Pilares de POO:
- Abstração: ``Armazenamento`` define o que todo armazenamento sabe fazer
  (salvar, ler, apagar), sem dizer onde.
- Polimorfismo: o ``MidiaService`` usa qualquer armazenamento do mesmo jeito.
  Trocar de disco para banco é só mudar ``ARMAZENAMENTO`` no ``.env``.
- Padrão Factory: ``criar_armazenamento()`` escolhe a implementação.

Por que dois tipos:
- ``ArmazenamentoDisco`` (Fase 4): pasta de uploads compartilhada por NFS,
  que entra no backup.
- ``ArmazenamentoBanco`` (Fase 3): o plano gratuito do Render apaga o disco
  a cada reinício, então as fotos vão para a tabela ``arquivos`` no
  PostgreSQL do Neon.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from flask import Flask, current_app
from sqlalchemy import delete

from app.domain.excecoes import ErroDeNegocio
from app.extensions import db
from app.models import Arquivo


def validar_nome_arquivo(nome: str) -> str:
    """Só nomes simples, sem pastas (impede ``../.env``)."""
    if not nome or Path(nome).name != nome or nome.startswith("."):
        raise ErroDeNegocio("Nome de arquivo inválido.")
    return nome


class Armazenamento(ABC):
    @abstractmethod
    def salvar(self, nome: str, dados: bytes, tipo: str) -> None:
        """Guarda os bytes com este nome."""

    @abstractmethod
    def ler(self, nome: str) -> bytes | None:
        """Devolve os bytes ou ``None`` se não existir."""

    @abstractmethod
    def apagar(self, nome: str) -> None:
        """Remove o arquivo (não falha se ele já não existir)."""


class ArmazenamentoDisco(Armazenamento):
    def __init__(self, pasta: str | Path) -> None:
        self.pasta = Path(pasta)

    def _caminho(self, nome: str) -> Path:
        return self.pasta / validar_nome_arquivo(nome)

    def salvar(self, nome: str, dados: bytes, tipo: str) -> None:
        self.pasta.mkdir(parents=True, exist_ok=True)
        self._caminho(nome).write_bytes(dados)

    def ler(self, nome: str) -> bytes | None:
        caminho = self._caminho(nome)
        return caminho.read_bytes() if caminho.is_file() else None

    def apagar(self, nome: str) -> None:
        self._caminho(nome).unlink(missing_ok=True)


class ArmazenamentoBanco(Armazenamento):
    """Os bytes entram na mesma transação da Polaroid: se ela falhar, o
    ``rollback`` desfaz o arquivo junto."""

    def salvar(self, nome: str, dados: bytes, tipo: str) -> None:
        db.session.add(
            Arquivo(nome=validar_nome_arquivo(nome), tipo=tipo, dados=dados, tamanho=len(dados))
        )

    def ler(self, nome: str) -> bytes | None:
        arquivo = db.session.get(Arquivo, validar_nome_arquivo(nome))
        return arquivo.dados if arquivo else None

    def apagar(self, nome: str) -> None:
        # Chamado depois do commit da ação principal, por isso confirma aqui.
        db.session.execute(delete(Arquivo).where(Arquivo.nome == validar_nome_arquivo(nome)))
        db.session.commit()


def criar_armazenamento(app: Flask | None = None) -> Armazenamento:
    config = (app or current_app).config
    tipo = config["ARMAZENAMENTO"]
    if tipo == "banco":
        return ArmazenamentoBanco()
    if tipo == "disco":
        return ArmazenamentoDisco(config["UPLOAD_FOLDER"])
    raise ValueError(f"ARMAZENAMENTO inválido: {tipo!r} (use 'disco' ou 'banco').")
