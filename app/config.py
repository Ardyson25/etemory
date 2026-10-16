"""Configurações por ambiente (RNF20).

Tudo que é segredo ou muda entre máquinas vem de variáveis de ambiente,
lidas do arquivo ``.env`` (que nunca vai para o Git).
"""

import os
from pathlib import Path

PASTA_RAIZ = Path(__file__).resolve().parent.parent


def _bool(nome: str, padrao: bool) -> bool:
    valor = os.environ.get(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in ("1", "true", "sim", "yes", "on")


def _url_banco(padrao: str) -> str:
    url = os.environ.get("DATABASE_URL", padrao)
    # Serviços como Render e Neon entregam "postgres://"; o SQLAlchemy 2
    # precisa do nome do driver.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-inseguro-troque-no-env")
    SQLALCHEMY_DATABASE_URI = _url_banco(
        f"sqlite:///{PASTA_RAIZ / 'instance' / 'etermory.db'}"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Nome desta instância, mostrado em /saude (app1, app2...).
    INSTANCIA = os.environ.get("INSTANCIA", "local")

    # Uploads (RN18). ARMAZENAMENTO: "disco" (pasta/NFS) ou "banco" (tabela arquivos)
    ARMAZENAMENTO = os.environ.get("ARMAZENAMENTO", "disco")
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(PASTA_RAIZ / "instance" / "uploads"))
    TAMANHO_MAX_IMAGEM = 5 * 1024 * 1024
    LADO_MAX_IMAGEM = 1600
    MAX_CONTENT_LENGTH = 12 * 1024 * 1024  # foto + capa + campos

    POLAROIDS_POR_PAGINA = 20

    # Sessão segura (RNF05)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("COOKIE_SEGURO", False)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE

    WTF_CSRF_TIME_LIMIT = None  # o token vale enquanto a sessão existir

    LOG_FILE = os.environ.get("LOG_FILE")  # ex.: /var/log/etermory/app.log
    ATRAS_DE_PROXY = _bool("ATRAS_DE_PROXY", False)


class DesenvolvimentoConfig(Config):
    DEBUG = True


class TesteConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "chave-de-teste"
    INSTANCIA = "teste"
    POLAROIDS_POR_PAGINA = 5


class ProducaoConfig(Config):
    SESSION_COOKIE_SECURE = _bool("COOKIE_SEGURO", True)
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    ATRAS_DE_PROXY = _bool("ATRAS_DE_PROXY", True)


CONFIGURACOES: dict[str, type[Config]] = {
    "desenvolvimento": DesenvolvimentoConfig,
    "teste": TesteConfig,
    "producao": ProducaoConfig,
}


def obter_config(nome: str | None) -> type[Config]:
    nome = nome or os.environ.get("ETERMORY_AMBIENTE", "desenvolvimento")
    return CONFIGURACOES[nome]
