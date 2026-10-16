"""Extensões do Flask, criadas uma vez e ligadas ao app em ``create_app()``."""

import sqlite3
from typing import Any

from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import MetaData, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase

# Nomes previsíveis para índices e restrições (as migrações ficam estáveis).
CONVENCAO_NOMES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCAO_NOMES)


db = SQLAlchemy(model_class=Base)
migrate = Migrate()
csrf = CSRFProtect()

login_manager = LoginManager()
login_manager.login_view = "auth.entrar"
login_manager.login_message = "Entre na sua conta para acessar o Etermory."
login_manager.login_message_category = "aviso"


@event.listens_for(Engine, "connect")
def _ativar_chaves_estrangeiras_sqlite(conexao: Any, _registro: Any) -> None:
    """O SQLite (usado nos testes) só respeita ON DELETE CASCADE com isto."""
    if isinstance(conexao, sqlite3.Connection):
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
