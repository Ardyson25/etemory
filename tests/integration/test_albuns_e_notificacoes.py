"""Álbuns (RN13, RC01, RC03) e notificações (RF23, RF24)."""

import pytest
from flask.testing import FlaskClient

from app.domain.enums import Visibilidade
from app.domain.excecoes import AcessoNegado, NaoEncontrado
from app.extensions import db
from app.models import Album, Polaroid
from app.services.album_service import AlbumService
from app.services.interacao_service import InteracaoService
from app.services.notificacao_service import NotificacaoService
from app.services.polaroid_service import PolaroidService
from app.services.vinculo_service import VinculoService


def test_rn13_excluir_album_mantem_polaroids(criar_usuario, criar_polaroid) -> None:  # type: ignore[no-untyped-def]
    ana = criar_usuario("ana")
    polaroid = criar_polaroid(ana)
    servico = AlbumService()
    album = servico.criar(ana, "Férias 2026", "", publico=True)
    servico.adicionar(ana, album.id, polaroid.id)
    servico.adicionar(ana, album.id, polaroid.id)  # repetir não duplica
    assert album.polaroids == [polaroid]

    servico.excluir(ana, album.id)
    assert db.session.get(Album, album.id) is None
    assert db.session.get(Polaroid, polaroid.id) is not None


def test_rc01_album_publico_filtra_o_que_o_leitor_ve(criar_usuario, criar_polaroid) -> None:  # type: ignore[no-untyped-def]
    ana, bia = criar_usuario("ana"), criar_usuario("bia")
    aberta = criar_polaroid(ana, visibilidade=Visibilidade.PUBLICA)
    fechada = criar_polaroid(ana, visibilidade=Visibilidade.SOMENTE_EU)
    servico = AlbumService()
    album = servico.criar(ana, "Misturado", "", publico=True)
    servico.adicionar(ana, album.id, aberta.id)
    servico.adicionar(ana, album.id, fechada.id)

    assert servico.polaroids_visiveis(bia, album) == [aberta]
    assert set(servico.polaroids_visiveis(ana, album)) == {aberta, fechada}
    PolaroidService().arquivar(ana, aberta.id)
    assert servico.polaroids_visiveis(ana, album) == [fechada]


def test_album_privado_e_rc03(client: FlaskClient, criar_usuario, criar_polaroid, entrar) -> None:  # type: ignore[no-untyped-def]
    ana, bia = criar_usuario("ana"), criar_usuario("bia")
    servico = AlbumService()
    album = servico.criar(ana, "Íntimo", "", publico=False)
    with pytest.raises(NaoEncontrado):
        servico.obter_visivel(bia, album.id)
    da_bia = criar_polaroid(bia, visibilidade=Visibilidade.PUBLICA)
    with pytest.raises(AcessoNegado):
        servico.adicionar(ana, album.id, da_bia.id)

    entrar(bia)
    assert client.get(f"/albuns/{album.id}").status_code == 404


def test_album_pelas_rotas(client: FlaskClient, criar_usuario, criar_polaroid, entrar) -> None:  # type: ignore[no-untyped-def]
    ana = criar_usuario("ana")
    polaroid = criar_polaroid(ana)
    entrar(ana)
    resposta = client.post("/albuns/novo", data={"titulo": "Viagens", "descricao": "", "publico": "y"})
    album_id = int(resposta.headers["Location"].rsplit("/", 1)[1])
    client.post("/albuns/adicionar", data={"album_id": album_id, "polaroid_id": polaroid.id})
    assert f"/polaroids/{polaroid.id}".encode() in client.get(f"/albuns/{album_id}").data
    assert "Viagens".encode() in client.get("/@ana?aba=albuns").data
    vazio = client.post("/albuns/novo", data={"titulo": "", "publico": "y"})
    assert vazio.status_code == 200  # formulário volta com erro


def test_notificacoes_contador_abrir_e_marcar(client: FlaskClient, criar_usuario, criar_polaroid, entrar) -> None:  # type: ignore[no-untyped-def]
    ana, bia = criar_usuario("ana"), criar_usuario("bia")
    polaroid = criar_polaroid(ana, visibilidade=Visibilidade.PUBLICA)
    VinculoService().seguir(bia, ana)
    InteracaoService().alternar_curtida(bia, polaroid.id)
    InteracaoService().comentar(bia, polaroid.id, "Que lindo")

    servico = NotificacaoService()
    assert servico.contar_nao_lidas(ana) == 3

    entrar(ana)
    html = client.get("/notificacoes/").data.decode()
    # Polimorfismo: cada subclasse escreve o próprio texto.
    assert "@bia criou um vínculo com você." in html
    assert "@bia curtiu sua memória." in html
    assert "@bia comentou na sua memória." in html
    assert '<span class="contador">3</span>' in html

    primeira = servico.listar(ana, 1).items[0]
    resposta = client.post(f"/notificacoes/{primeira.id}/abrir")
    assert resposta.status_code == 302
    assert primeira.lida and servico.contar_nao_lidas(ana) == 2

    client.post("/notificacoes/marcar-todas")
    assert servico.contar_nao_lidas(ana) == 0


def test_notificacao_de_outra_pessoa_da_404(client: FlaskClient, criar_usuario, entrar) -> None:  # type: ignore[no-untyped-def]
    ana, bia = criar_usuario("ana"), criar_usuario("bia")
    VinculoService().seguir(bia, ana)
    notificacao = NotificacaoService().listar(ana, 1).items[0]
    entrar(bia)
    assert client.post(f"/notificacoes/{notificacao.id}/abrir").status_code == 404
