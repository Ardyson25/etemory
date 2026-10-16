"""Fixtures compartilhadas pelos testes.

Os testes de integração usam SQLite em memória: cada teste começa com um
banco vazio e não precisa de PostgreSQL instalado.
"""

from collections.abc import Callable, Iterator
from io import BytesIO
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient
from PIL import Image

from app import create_app
from app.domain.enums import Visibilidade
from app.extensions import db
from app.models import Polaroid, Usuario
from app.services.polaroid_service import DadosPolaroid, PolaroidService


@pytest.fixture()
def app(tmp_path: Path) -> Iterator[Flask]:
    aplicacao = create_app("teste")
    aplicacao.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
    with aplicacao.app_context():
        db.create_all()
        yield aplicacao
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    return app.test_client()


def gerar_imagem(formato: str = "PNG", tamanho: tuple[int, int] = (40, 30)) -> BytesIO:
    """Imagem pequena criada na memória para os testes de upload."""
    buffer = BytesIO()
    Image.new("RGB", tamanho, (140, 26, 17)).save(buffer, formato)
    buffer.seek(0)
    return buffer


@pytest.fixture()
def criar_usuario(app: Flask) -> Callable[..., Usuario]:
    contador = {"n": 0}

    def _criar(username: str | None = None, conta_privada: bool = False) -> Usuario:
        contador["n"] += 1
        nome = username or f"usuario{contador['n']}"
        usuario = Usuario(
            nome=nome.title(),
            username=nome,
            email=f"{nome}@exemplo.com",
            senha="senha-segura-123",
            conta_privada=conta_privada,
        )
        db.session.add(usuario)
        db.session.commit()
        return usuario

    return _criar


@pytest.fixture()
def criar_polaroid(app: Flask) -> Callable[..., Polaroid]:
    def _criar(
        autor: Usuario,
        legenda: str = "Uma memória",
        visibilidade: Visibilidade = Visibilidade.AUTOMATICA,
        **extras: object,
    ) -> Polaroid:
        dados = DadosPolaroid(legenda=legenda, visibilidade=visibilidade, **extras)  # type: ignore[arg-type]
        return PolaroidService().publicar(autor, dados, gerar_imagem())

    return _criar


@pytest.fixture()
def entrar(client: FlaskClient) -> Callable[[Usuario], None]:
    """Faz login de verdade pela rota /entrar."""

    def _entrar(usuario: Usuario) -> None:
        resposta = client.post(
            "/entrar", data={"login": usuario.email, "senha": "senha-segura-123"}
        )
        assert resposta.status_code == 302

    return _entrar
