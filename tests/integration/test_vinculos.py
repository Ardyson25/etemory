"""Vínculos, solicitações e melhores amigos (RN05–RN07, RN15, RC04, RC06)."""

import pytest
from flask.testing import FlaskClient
from sqlalchemy import select

from app.domain.enums import StatusVinculo, Visibilidade
from app.domain.excecoes import AcessoNegado, ErroDeNegocio, NaoEncontrado
from app.extensions import db
from app.models import (
    Notificacao,
    NotificacaoSeguidor,
    NotificacaoSolicitacao,
    NotificacaoSolicitacaoAceita,
)
from app.services.polaroid_service import PolaroidService
from app.services.usuario_service import UsuarioService
from app.services.vinculo_service import EstadoRelacao, VinculoService
from app.domain.enums import ModoComentarios


def notificacoes_de(usuario_id: int) -> list[Notificacao]:
    return list(db.session.scalars(select(Notificacao).where(Notificacao.destinatario_id == usuario_id)))


def test_rn07_conta_publica_e_seguida_na_hora(criar_usuario) -> None:  # type: ignore[no-untyped-def]
    ana, bia = criar_usuario("ana"), criar_usuario("bia")
    vinculo = VinculoService().seguir(ana, bia)
    assert vinculo.status is StatusVinculo.ACEITO
    assert [type(n) for n in notificacoes_de(bia.id)] == [NotificacaoSeguidor]


def test_rn07_conta_privada_gera_solicitacao(criar_usuario) -> None:  # type: ignore[no-untyped-def]
    ana, bia = criar_usuario("ana"), criar_usuario("bia", conta_privada=True)
    servico = VinculoService()
    vinculo = servico.seguir(ana, bia)
    assert vinculo.status is StatusVinculo.PENDENTE
    assert servico.estado_relacao(ana, bia) is EstadoRelacao.PENDENTE
    assert isinstance(notificacoes_de(bia.id)[0], NotificacaoSolicitacao)

    with pytest.raises(AcessoNegado):
        servico.responder(ana, vinculo.id, aceitar=True)  # só a dona responde
    servico.responder(bia, vinculo.id, aceitar=True)
    assert vinculo.status is StatusVinculo.ACEITO
    assert isinstance(notificacoes_de(ana.id)[0], NotificacaoSolicitacaoAceita)


def test_rn07_cancelar_e_rc06_pedir_de_novo(criar_usuario) -> None:  # type: ignore[no-untyped-def]
    ana, bia = criar_usuario("ana"), criar_usuario("bia", conta_privada=True)
    servico = VinculoService()
    servico.seguir(ana, bia)
    servico.cancelar_solicitacao(ana, bia)
    assert servico.estado_relacao(ana, bia) is EstadoRelacao.NENHUM

    vinculo = servico.seguir(ana, bia)  # RC06
    servico.responder(bia, vinculo.id, aceitar=False)
    assert vinculo.status is StatusVinculo.RECUSADO
    assert servico.seguir(ana, bia).status is StatusVinculo.PENDENTE


def test_rn15_nao_segue_a_si_mesmo(criar_usuario) -> None:  # type: ignore[no-untyped-def]
    ana = criar_usuario("ana")
    with pytest.raises(ErroDeNegocio):
        VinculoService().seguir(ana, ana)


def test_seguir_duas_vezes_nao_duplica(criar_usuario) -> None:  # type: ignore[no-untyped-def]
    ana, bia = criar_usuario("ana"), criar_usuario("bia")
    servico = VinculoService()
    assert servico.seguir(ana, bia).id == servico.seguir(ana, bia).id
    assert servico.contadores(bia)["seguidores"] == 1


def test_rn05_rn06_deixar_de_seguir_tira_acesso_e_melhor_amigo(criar_usuario, criar_polaroid) -> None:  # type: ignore[no-untyped-def]
    ana, bia = criar_usuario("ana"), criar_usuario("bia")
    servico = VinculoService()
    servico.seguir(bia, ana)
    assert servico.alternar_melhor_amigo(ana, bia.id) is True
    intima = criar_polaroid(ana, visibilidade=Visibilidade.MELHORES_AMIGOS)
    assert PolaroidService().obter_visivel(bia, intima.id) == intima

    servico.deixar_de_seguir(bia, ana)
    with pytest.raises(NaoEncontrado):
        PolaroidService().obter_visivel(bia, intima.id)

    servico.seguir(bia, ana)  # volta a seguir, mas não é mais melhor amiga
    with pytest.raises(NaoEncontrado):
        PolaroidService().obter_visivel(bia, intima.id)


def test_rn06_melhor_amigo_precisa_ser_seguidor(criar_usuario) -> None:  # type: ignore[no-untyped-def]
    ana, bia = criar_usuario("ana"), criar_usuario("bia")
    with pytest.raises(ErroDeNegocio):
        VinculoService().alternar_melhor_amigo(ana, bia.id)


def test_rc04_virar_publica_aceita_pendentes(criar_usuario) -> None:  # type: ignore[no-untyped-def]
    ana, bia = criar_usuario("ana"), criar_usuario("bia", conta_privada=True)
    vinculo = VinculoService().seguir(ana, bia)
    UsuarioService().configurar(bia, conta_privada=False, modo_comentarios_padrao=ModoComentarios.TODOS)
    assert vinculo.status is StatusVinculo.ACEITO


def test_fluxo_pelas_rotas(client: FlaskClient, criar_usuario, entrar) -> None:  # type: ignore[no-untyped-def]
    ana, bia = criar_usuario("ana"), criar_usuario("bia", conta_privada=True)
    entrar(ana)
    client.post("/@bia/seguir")
    assert "Solicitado".encode() in client.get("/@bia").data
    client.post("/sair")

    entrar(bia)
    pagina = client.get("/vinculos/solicitacoes")
    assert "@ana".encode() in pagina.data
    vinculo_id = VinculoService().solicitacoes_pendentes(bia)[0].id
    client.post(f"/vinculos/{vinculo_id}/aceitar")
    assert "1</strong> seguidores".encode() in client.get("/@bia").data
    assert client.post(f"/vinculos/{vinculo_id}/apagar").status_code == 404
