"""Curtidas, comentários e menções (RN08–RN10, RN15, RN16, RC02)."""

import pytest
from flask.testing import FlaskClient
from sqlalchemy import select

from app.domain.enums import ModoComentarios, Visibilidade
from app.domain.excecoes import AcessoNegado
from app.extensions import db
from app.models import (
    Notificacao,
    NotificacaoComentario,
    NotificacaoCurtida,
    NotificacaoMencao,
)
from app.services.interacao_service import InteracaoService
from app.services.polaroid_service import DadosPolaroid, PolaroidService
from app.services.vinculo_service import VinculoService


def tipos_para(usuario_id: int) -> list[type]:
    consulta = select(Notificacao).where(Notificacao.destinatario_id == usuario_id)
    return [type(n) for n in db.session.scalars(consulta)]


def test_rn10_curtir_e_descurtir(criar_usuario, criar_polaroid) -> None:  # type: ignore[no-untyped-def]
    ana, bia = criar_usuario("ana"), criar_usuario("bia")
    polaroid = criar_polaroid(ana, visibilidade=Visibilidade.PUBLICA)
    servico = InteracaoService()
    assert servico.alternar_curtida(bia, polaroid.id) == (True, 1)
    assert servico.alternar_curtida(bia, polaroid.id) == (False, 0)
    assert tipos_para(ana.id) == [NotificacaoCurtida]


def test_rn15_curtir_a_propria_nao_notifica(criar_usuario, criar_polaroid) -> None:  # type: ignore[no-untyped-def]
    ana = criar_usuario("ana")
    polaroid = criar_polaroid(ana)
    InteracaoService().alternar_curtida(ana, polaroid.id)
    assert tipos_para(ana.id) == []


def test_curtir_por_fetch_devolve_json(client: FlaskClient, criar_usuario, criar_polaroid, entrar) -> None:  # type: ignore[no-untyped-def]
    polaroid = criar_polaroid(criar_usuario("ana"), visibilidade=Visibilidade.PUBLICA)
    entrar(criar_usuario("bia"))
    resposta = client.post(
        f"/polaroids/{polaroid.id}/curtir", headers={"Accept": "application/json"}
    )
    assert resposta.get_json() == {"curtiu": True, "total": 1}


def test_rn08_e_rn16_comentario_com_mencao(criar_usuario, criar_polaroid) -> None:  # type: ignore[no-untyped-def]
    ana, bia, caio = criar_usuario("ana"), criar_usuario("bia"), criar_usuario("caio")
    polaroid = criar_polaroid(ana, visibilidade=Visibilidade.PUBLICA)
    InteracaoService().comentar(bia, polaroid.id, "Olha isso @caio e @ninguem_existe")
    assert tipos_para(ana.id) == [NotificacaoComentario]
    assert tipos_para(caio.id) == [NotificacaoMencao]


def test_rc02_mencao_so_para_quem_pode_ver(criar_usuario, criar_polaroid) -> None:  # type: ignore[no-untyped-def]
    ana, bia = criar_usuario("ana"), criar_usuario("bia")
    criar_polaroid(ana, legenda="Só minha, @bia", visibilidade=Visibilidade.SOMENTE_EU)
    assert tipos_para(bia.id) == []


def test_mencao_na_edicao_so_notifica_quem_e_novo(criar_usuario, criar_polaroid) -> None:  # type: ignore[no-untyped-def]
    ana, bia, caio = criar_usuario("ana"), criar_usuario("bia"), criar_usuario("caio")
    polaroid = criar_polaroid(ana, legenda="Com @bia", visibilidade=Visibilidade.PUBLICA)
    PolaroidService().editar(
        ana, polaroid.id,
        DadosPolaroid(legenda="Com @bia e @caio", visibilidade=Visibilidade.PUBLICA),
    )
    assert tipos_para(bia.id) == [NotificacaoMencao]
    assert tipos_para(caio.id) == [NotificacaoMencao]


@pytest.mark.parametrize(
    ("modo", "seguidor_pode", "estranho_pode"),
    [
        (ModoComentarios.TODOS, True, True),
        (ModoComentarios.SEGUIDORES, True, False),
        (ModoComentarios.NINGUEM, False, False),
    ],
)
def test_rn08_modos(criar_usuario, criar_polaroid, modo, seguidor_pode, estranho_pode) -> None:  # type: ignore[no-untyped-def]
    ana, seguidor, estranho = criar_usuario("ana"), criar_usuario("seg"), criar_usuario("est")
    VinculoService().seguir(seguidor, ana)
    polaroid = criar_polaroid(ana, visibilidade=Visibilidade.PUBLICA, modo_comentarios=modo)
    servico = InteracaoService()
    for usuario, pode in ((seguidor, seguidor_pode), (estranho, estranho_pode)):
        if pode:
            servico.comentar(usuario, polaroid.id, "oi")
        else:
            with pytest.raises(AcessoNegado):
                servico.comentar(usuario, polaroid.id, "oi")
    servico.comentar(ana, polaroid.id, "a autora sempre pode")


def test_rn09_editar_e_excluir_pelas_rotas(client: FlaskClient, criar_usuario, criar_polaroid, entrar) -> None:  # type: ignore[no-untyped-def]
    ana, bia, caio = criar_usuario("ana"), criar_usuario("bia"), criar_usuario("caio")
    polaroid = criar_polaroid(ana, visibilidade=Visibilidade.PUBLICA)
    comentario = InteracaoService().comentar(bia, polaroid.id, "Lindo")

    entrar(caio)
    assert client.post(f"/comentarios/{comentario.id}/editar", data={"texto": "x"}).status_code == 403
    assert client.post(f"/comentarios/{comentario.id}/excluir").status_code == 403
    client.post("/sair")

    entrar(ana)  # dona da Polaroid: não edita, mas exclui
    assert client.post(f"/comentarios/{comentario.id}/editar", data={"texto": "x"}).status_code == 403
    assert client.post(f"/comentarios/{comentario.id}/excluir").status_code == 302
    assert polaroid.comentarios == []


def test_rn09_comentario_vazio_ou_longo_pela_rota(client: FlaskClient, criar_usuario, criar_polaroid, entrar) -> None:  # type: ignore[no-untyped-def]
    ana = criar_usuario("ana")
    polaroid = criar_polaroid(ana)
    entrar(ana)
    for texto in ("", "x" * 501):
        resposta = client.post(
            f"/polaroids/{polaroid.id}/comentarios", data={"texto": texto}, follow_redirects=True
        )
        assert resposta.status_code == 200
    assert polaroid.comentarios == []
