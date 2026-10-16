"""Configuração de produção (Fase 3)."""

import importlib

import pytest

import app.config as config_modulo
from app import create_app


@pytest.fixture()
def recarregar_config(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    """Relê app/config.py depois de mudar as variáveis de ambiente."""

    def _recarregar(**variaveis: str) -> None:
        for nome in ("SECRET_KEY", "DATABASE_URL", "COOKIE_SEGURO", "ATRAS_DE_PROXY"):
            monkeypatch.delenv(nome, raising=False)
        for nome, valor in variaveis.items():
            monkeypatch.setenv(nome, valor)
        importlib.reload(config_modulo)

    yield _recarregar
    monkeypatch.undo()
    importlib.reload(config_modulo)


def test_producao_exige_secret_key(recarregar_config) -> None:  # type: ignore[no-untyped-def]
    recarregar_config()
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app("producao")


def test_producao_segura_por_padrao(recarregar_config, tmp_path) -> None:  # type: ignore[no-untyped-def]
    recarregar_config(SECRET_KEY="x" * 64, DATABASE_URL=f"sqlite:///{tmp_path}/p.db")
    aplicacao = create_app("producao")
    assert aplicacao.config["SESSION_COOKIE_SECURE"] is True
    assert aplicacao.config["SESSION_COOKIE_HTTPONLY"] is True
    assert aplicacao.wsgi_app.__class__.__name__ == "ProxyFix"
    assert aplicacao.config["WTF_CSRF_ENABLED"] is not False


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("postgres://u:s@h/db", "postgresql+psycopg://u:s@h/db"),
        ("postgresql://u:s@h/db?sslmode=require", "postgresql+psycopg://u:s@h/db?sslmode=require"),
        ("postgresql+psycopg://u:s@h/db", "postgresql+psycopg://u:s@h/db"),
    ],
)
def test_url_do_banco_usa_o_driver_psycopg(recarregar_config, entrada: str, esperado: str) -> None:  # type: ignore[no-untyped-def]
    recarregar_config(DATABASE_URL=entrada)
    assert config_modulo.Config.SQLALCHEMY_DATABASE_URI == esperado
