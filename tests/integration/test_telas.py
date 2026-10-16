"""Abre todas as telas para garantir que nenhum template quebra."""

import pytest
from flask.testing import FlaskClient

from app.domain.enums import Visibilidade
from app.services.album_service import AlbumService
from app.services.polaroid_service import PolaroidService


def test_telas_publicas(client: FlaskClient) -> None:
    for url in ("/entrar", "/cadastro"):
        assert client.get(url).status_code == 200


def test_todas_as_telas_logadas(client: FlaskClient, criar_usuario, criar_polaroid, entrar) -> None:  # type: ignore[no-untyped-def]
    ana = criar_usuario("ana")
    polaroid = criar_polaroid(ana, visibilidade=Visibilidade.PUBLICA)
    arquivada = criar_polaroid(ana)
    PolaroidService().arquivar(ana, arquivada.id)
    album = AlbumService().criar(ana, "Álbum", "Descrição", publico=True)
    entrar(ana)

    urls = [
        "/",
        "/?aba=vinculos",
        "/polaroids/nova",
        f"/polaroids/{polaroid.id}",
        f"/polaroids/{polaroid.id}/editar",
        f"/polaroids/{arquivada.id}",
        "/arquivo",
        "/lixeira",
        "/@ana",
        "/@ana?aba=albuns",
        "/@ana/seguidores",
        "/@ana/seguindo",
        "/perfil/editar",
        "/configuracoes",
        "/vinculos/solicitacoes",
        "/vinculos/melhores-amigos",
        "/albuns/novo",
        f"/albuns/{album.id}",
        f"/albuns/{album.id}/editar",
        "/notificacoes/",
    ]
    for url in urls:
        resposta = client.get(url)
        assert resposta.status_code == 200, url
    assert client.get("/albuns/").status_code == 302


@pytest.mark.parametrize("url", ["/nao-existe", "/polaroids/999", "/albuns/999"])
def test_paginas_de_erro(client: FlaskClient, criar_usuario, entrar, url: str) -> None:  # type: ignore[no-untyped-def]
    entrar(criar_usuario("ana"))
    resposta = client.get(url)
    assert resposta.status_code == 404
    assert "Voltar para a timeline".encode() in resposta.data
