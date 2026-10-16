"""Timeline e consistência entre a regra em Python e a consulta SQL (risco R02)."""

import itertools

from flask.testing import FlaskClient

from app.domain.enums import Visibilidade
from app.domain.politica_acesso import PoliticaAcesso
from app.repositories import PolaroidRepository, VinculoRepository
from app.services.polaroid_service import PolaroidService
from app.services.timeline_service import TimelineService
from app.services.vinculo_service import VinculoService


def test_sql_e_politica_concordam_em_todos_os_casos(criar_usuario, criar_polaroid) -> None:  # type: ignore[no-untyped-def]
    """Para cada combinação de conta, vínculo, visibilidade e status, a
    timeline (SQL) e a PoliticaAcesso (Python) dão a mesma resposta."""
    leitores = {
        "estranho": criar_usuario("estranho"),
        "seguidor": criar_usuario("seguidor"),
        "melhor": criar_usuario("melhor"),
        "pendente": criar_usuario("pendente"),
    }
    vinculos = VinculoService()
    polaroids = []
    for indice, privada in enumerate((False, True)):
        autor = criar_usuario(f"autor{indice}", conta_privada=privada)
        for nome in ("seguidor", "melhor"):
            vinculo = vinculos.seguir(leitores[nome], autor)
            if vinculo.esta_pendente:
                vinculos.responder(autor, vinculo.id, aceitar=True)
        vinculos.alternar_melhor_amigo(autor, leitores["melhor"].id)
        if privada:
            vinculos.seguir(leitores["pendente"], autor)  # fica pendente
        for visibilidade, acao in itertools.product(
            list(Visibilidade), ("ativa", "arquivar", "lixeira")
        ):
            polaroid = criar_polaroid(autor, visibilidade=visibilidade)
            if acao == "arquivar":
                PolaroidService().arquivar(autor, polaroid.id)
            elif acao == "lixeira":
                PolaroidService().mover_para_lixeira(autor, polaroid.id)
            polaroids.append(polaroid)

    politica = PoliticaAcesso()
    for leitor in leitores.values():
        contexto = VinculoRepository().contexto_do_leitor(leitor.id)
        pela_sql = {p.id for p in PolaroidRepository().visiveis(contexto, 1, 1000).items}
        pela_politica = {p.id for p in polaroids if politica.pode_ver(contexto, p)}
        assert pela_sql == pela_politica, leitor.username


def test_abas_e_ordem(criar_usuario, criar_polaroid) -> None:  # type: ignore[no-untyped-def]
    ana, bia, caio = criar_usuario("ana"), criar_usuario("bia"), criar_usuario("caio")
    VinculoService().seguir(ana, bia)
    de_bia = criar_polaroid(bia, legenda="da Bia", visibilidade=Visibilidade.PUBLICA)
    de_caio = criar_polaroid(caio, legenda="do Caio", visibilidade=Visibilidade.PUBLICA)
    minha = criar_polaroid(ana, legenda="minha", visibilidade=Visibilidade.SOMENTE_EU)

    servico = TimelineService()
    assert servico.para_voce(ana).items == [minha, de_caio, de_bia]  # mais recente primeiro
    assert servico.de_vinculos(ana).items == [minha, de_bia]


def test_paginacao(client: FlaskClient, criar_usuario, criar_polaroid, entrar) -> None:  # type: ignore[no-untyped-def]
    ana = criar_usuario("ana")
    for numero in range(7):  # TesteConfig: 5 por página
        criar_polaroid(ana, legenda=f"memoria-{numero}", visibilidade=Visibilidade.PUBLICA)
    pagina = TimelineService().para_voce(ana, 2)
    assert pagina.total == 7 and len(pagina.items) == 2

    entrar(ana)
    html = client.get("/?pagina=2").data.decode()
    assert "memoria-0" in html and "memoria-6" not in html
    assert "Página 2 de 2" in html


def test_prontuario_de_conta_privada(client: FlaskClient, criar_usuario, criar_polaroid, entrar) -> None:  # type: ignore[no-untyped-def]
    bia = criar_usuario("bia", conta_privada=True)
    criar_polaroid(bia, legenda="segredo")  # automática -> seguidores
    publica = criar_polaroid(bia, legenda="aberta", visibilidade=Visibilidade.PUBLICA)
    entrar(criar_usuario("ana"))
    html = client.get("/@bia").data.decode()
    assert f"/polaroids/{publica.id}" in html
    assert html.count('class="grade-item"') == 1
