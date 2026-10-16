"""Testes unitários das regras de acesso (RN01–RN05, RN08), sem banco."""

from dataclasses import dataclass

import pytest

from app.domain.comentarios import (
    FabricaRegraComentario,
    RegraComentarNinguem,
    RegraComentario,
)
from app.domain.contexto import ContextoLeitor
from app.domain.enums import ModoComentarios, StatusPolaroid, Visibilidade
from app.domain.politica_acesso import PoliticaAcesso
from app.domain.visibilidade import (
    FabricaRegraVisibilidade,
    RegraPublica,
    RegraVisibilidade,
    resolver_visibilidade,
)

AUTOR = 1
SEGUIDOR = 2
MELHOR_AMIGO = 3
ESTRANHO = 4


@dataclass
class PolaroidFalsa:
    """Cumpre o contrato PolaroidAcessivel sem SQLAlchemy."""

    visibilidade_efetiva: Visibilidade
    status: StatusPolaroid = StatusPolaroid.ATIVA
    modo_comentarios: ModoComentarios = ModoComentarios.TODOS
    autor_id: int = AUTOR


def leitor(usuario_id: int) -> ContextoLeitor:
    seguindo = {SEGUIDOR: {AUTOR}, MELHOR_AMIGO: {AUTOR}}.get(usuario_id, set())
    melhor_amigo_de = {MELHOR_AMIGO: {AUTOR}}.get(usuario_id, set())
    return ContextoLeitor(usuario_id, frozenset(seguindo), frozenset(melhor_amigo_de))


politica = PoliticaAcesso()


@pytest.mark.parametrize(
    ("visibilidade", "quem_ve"),
    [
        (Visibilidade.PUBLICA, {AUTOR, SEGUIDOR, MELHOR_AMIGO, ESTRANHO}),
        (Visibilidade.SEGUIDORES, {AUTOR, SEGUIDOR, MELHOR_AMIGO}),
        (Visibilidade.MELHORES_AMIGOS, {AUTOR, MELHOR_AMIGO}),
        (Visibilidade.SOMENTE_EU, {AUTOR}),
    ],
)
def test_rn02_quem_ve_cada_visibilidade(visibilidade: Visibilidade, quem_ve: set[int]) -> None:
    polaroid = PolaroidFalsa(visibilidade)
    for usuario in (AUTOR, SEGUIDOR, MELHOR_AMIGO, ESTRANHO):
        assert politica.pode_ver(leitor(usuario), polaroid) == (usuario in quem_ve)


def test_rn03_automatica_resolve_pela_privacidade_da_conta() -> None:
    assert resolver_visibilidade(Visibilidade.AUTOMATICA, False) is Visibilidade.PUBLICA
    assert resolver_visibilidade(Visibilidade.AUTOMATICA, True) is Visibilidade.SEGUIDORES
    assert resolver_visibilidade(Visibilidade.SOMENTE_EU, False) is Visibilidade.SOMENTE_EU


@pytest.mark.parametrize("status", [StatusPolaroid.ARQUIVADA, StatusPolaroid.LIXEIRA])
def test_rn04_arquivada_e_lixeira_so_para_o_autor(status: StatusPolaroid) -> None:
    polaroid = PolaroidFalsa(Visibilidade.PUBLICA, status=status)
    assert politica.pode_ver(leitor(AUTOR), polaroid)
    assert not politica.pode_ver(leitor(SEGUIDOR), polaroid)
    assert not politica.pode_ver(leitor(ESTRANHO), polaroid)


def test_rn05_seguidor_comum_nao_ve_melhores_amigos() -> None:
    polaroid = PolaroidFalsa(Visibilidade.MELHORES_AMIGOS)
    assert not politica.pode_ver(leitor(SEGUIDOR), polaroid)


def test_fabrica_devolve_a_subclasse_certa_e_recusa_automatica() -> None:
    regra = FabricaRegraVisibilidade.obter(Visibilidade.PUBLICA)
    assert isinstance(regra, RegraPublica)
    assert isinstance(regra, RegraVisibilidade)  # polimorfismo: todas são "RegraVisibilidade"
    with pytest.raises(ValueError):
        FabricaRegraVisibilidade.obter(Visibilidade.AUTOMATICA)


def test_classe_abstrata_nao_pode_ser_instanciada() -> None:
    with pytest.raises(TypeError):
        RegraVisibilidade()  # type: ignore[abstract]
    with pytest.raises(TypeError):
        RegraComentario()  # type: ignore[abstract]


@pytest.mark.parametrize(
    ("modo", "quem_comenta"),
    [
        (ModoComentarios.TODOS, {AUTOR, SEGUIDOR, MELHOR_AMIGO, ESTRANHO}),
        (ModoComentarios.SEGUIDORES, {AUTOR, SEGUIDOR, MELHOR_AMIGO}),
        (ModoComentarios.MELHORES_AMIGOS, {AUTOR, MELHOR_AMIGO}),
        (ModoComentarios.NINGUEM, {AUTOR}),
    ],
)
def test_rn08_modo_de_comentarios(modo: ModoComentarios, quem_comenta: set[int]) -> None:
    polaroid = PolaroidFalsa(Visibilidade.PUBLICA, modo_comentarios=modo)
    for usuario in (AUTOR, SEGUIDOR, MELHOR_AMIGO, ESTRANHO):
        assert politica.pode_comentar(leitor(usuario), polaroid) == (usuario in quem_comenta)


def test_rn08_precisa_ver_para_comentar() -> None:
    polaroid = PolaroidFalsa(Visibilidade.SOMENTE_EU, modo_comentarios=ModoComentarios.TODOS)
    assert not politica.pode_comentar(leitor(ESTRANHO), polaroid)


def test_nao_comenta_em_memoria_arquivada() -> None:
    polaroid = PolaroidFalsa(Visibilidade.PUBLICA, status=StatusPolaroid.ARQUIVADA)
    assert not politica.pode_comentar(leitor(AUTOR), polaroid)


def test_fabrica_de_comentarios() -> None:
    assert isinstance(FabricaRegraComentario.obter(ModoComentarios.NINGUEM), RegraComentarNinguem)
