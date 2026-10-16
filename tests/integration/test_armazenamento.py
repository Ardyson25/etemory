"""Armazenamento de imagens em disco e no banco (decisão da Fase 3)."""

from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import func, select

from app.domain.enums import Visibilidade
from app.domain.excecoes import ErroDeNegocio
from app.domain.tempo import agora
from app.extensions import db
from app.models import Arquivo
from app.services.armazenamento import (
    Armazenamento,
    ArmazenamentoBanco,
    ArmazenamentoDisco,
    criar_armazenamento,
)
from app.services.polaroid_service import DadosPolaroid, PolaroidService
from tests.conftest import gerar_imagem


@pytest.fixture()
def no_banco(app: Flask) -> Iterator[Flask]:
    app.config["ARMAZENAMENTO"] = "banco"
    yield app
    app.config["ARMAZENAMENTO"] = "disco"


def total_arquivos() -> int:
    return db.session.scalar(select(func.count()).select_from(Arquivo)) or 0


def test_fabrica_escolhe_pela_configuracao(app: Flask) -> None:
    assert isinstance(criar_armazenamento(), ArmazenamentoDisco)
    app.config["ARMAZENAMENTO"] = "banco"
    assert isinstance(criar_armazenamento(), ArmazenamentoBanco)
    app.config["ARMAZENAMENTO"] = "nuvem"
    with pytest.raises(ValueError):
        criar_armazenamento()
    with pytest.raises(TypeError):
        Armazenamento()  # type: ignore[abstract]


def test_disco_salva_le_e_apaga(tmp_path: Path) -> None:
    disco = ArmazenamentoDisco(tmp_path)
    disco.salvar("a.webp", b"123", "image/webp")
    assert disco.ler("a.webp") == b"123"
    disco.apagar("a.webp")
    assert disco.ler("a.webp") is None
    with pytest.raises(ErroDeNegocio):
        disco.ler("../segredo")


def test_publicar_e_ver_foto_guardada_no_banco(
    no_banco: Flask, client: FlaskClient, criar_usuario, criar_polaroid, entrar  # type: ignore[no-untyped-def]
) -> None:
    ana = criar_usuario("ana")
    polaroid = criar_polaroid(ana, visibilidade=Visibilidade.PUBLICA)
    assert total_arquivos() == 1
    assert not any(Path(no_banco.config["UPLOAD_FOLDER"]).glob("*.webp"))

    entrar(criar_usuario("bia"))
    resposta = client.get(f"/midia/{polaroid.foto.caminho_arquivo}")
    assert resposta.status_code == 200
    assert resposta.mimetype == "image/webp"
    assert resposta.data[:4] == b"RIFF"  # assinatura do formato WebP
    assert "private" in resposta.headers["Cache-Control"]


def test_falha_no_banco_desfaz_o_arquivo(no_banco: Flask, criar_usuario) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ErroDeNegocio):
        PolaroidService().publicar(criar_usuario("ana"), DadosPolaroid(legenda=""), gerar_imagem())
    assert total_arquivos() == 0


def test_limpeza_da_lixeira_apaga_do_banco(no_banco: Flask, criar_usuario, criar_polaroid) -> None:  # type: ignore[no-untyped-def]
    ana = criar_usuario("ana")
    polaroid = criar_polaroid(ana)
    servico = PolaroidService()
    servico.mover_para_lixeira(ana, polaroid.id)
    polaroid.excluida_em = agora() - timedelta(days=30)
    db.session.commit()
    assert servico.limpar_lixeira_expirada() == 1
    assert total_arquivos() == 0
