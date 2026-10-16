"""Validações e geração de menções (RN12, RN15, RN16, RN17)."""

import pytest

from app.domain.excecoes import AcessoNegado, ErroDeNegocio, NaoEncontrado
from app.domain.notificacoes import GeradorNotificacoes
from app.domain.validacoes import validar_texto, validar_url_https, validar_username


@pytest.mark.parametrize("valido", ["ana", "ana.maria_2", "a" * 24, "@joao"])
def test_rn12_username_valido(valido: str) -> None:
    assert validar_username(valido) == valido.lstrip("@")


@pytest.mark.parametrize("invalido", ["ab", "a" * 25, "Ana", "ana maria", "ana!", "ãna", ""])
def test_rn12_username_invalido(invalido: str) -> None:
    with pytest.raises(ErroDeNegocio):
        validar_username(invalido)


def test_rn17_links_so_https() -> None:
    assert validar_url_https("https://open.spotify.com/track/1") == "https://open.spotify.com/track/1"
    assert validar_url_https("") is None
    for ruim in ("http://site.com", "javascript:alert(1)", "https://", "ftp://x.com"):
        with pytest.raises(ErroDeNegocio):
            validar_url_https(ruim)


def test_validar_texto_limites() -> None:
    assert validar_texto("  oi  ", "Campo", 1, 10) == "oi"
    with pytest.raises(ErroDeNegocio):
        validar_texto("   ", "Campo", 1, 10)
    with pytest.raises(ErroDeNegocio):
        validar_texto("x" * 11, "Campo", 1, 10)


def test_rn16_extrai_mencoes() -> None:
    texto = "Com @ana e @Joao.Silva no show! Obrigado, @bia_2. E-mail: x@y.com @ab"
    assert GeradorNotificacoes.extrair_mencoes(texto) == {"ana", "joao.silva", "bia_2"}


def test_rn16_texto_sem_mencao() -> None:
    assert GeradorNotificacoes.extrair_mencoes(None) == set()
    assert GeradorNotificacoes.extrair_mencoes("sem menções") == set()


def test_rn15_nao_notifica_a_si_mesmo() -> None:
    assert not GeradorNotificacoes.deve_notificar(1, 1)
    assert GeradorNotificacoes.deve_notificar(1, 2)


def test_heranca_das_excecoes() -> None:
    assert issubclass(AcessoNegado, ErroDeNegocio)
    assert NaoEncontrado.codigo_http == 404
    assert AcessoNegado.codigo_http == 403
