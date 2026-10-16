"""Fábrica da aplicação (padrão app factory).

``create_app()`` monta uma aplicação nova a cada chamada. Isso permite
criar uma configuração para testes, outra para produção, e rodar duas
instâncias (app1 e app2) com o mesmo código.
"""

import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # lê o .env antes de importar a configuração

import click  # noqa: E402
from flask import (  # noqa: E402
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user  # noqa: E402
from flask_wtf.csrf import CSRFError  # noqa: E402
from werkzeug.exceptions import HTTPException  # noqa: E402
from werkzeug.middleware.proxy_fix import ProxyFix  # noqa: E402

from app.config import obter_config  # noqa: E402
from app.domain.enums import Emocao, EstadoMemoria  # noqa: E402
from app.domain.excecoes import AcessoNegado, ErroDeNegocio, NaoEncontrado  # noqa: E402
from app.extensions import csrf, db, login_manager, migrate  # noqa: E402

CHAVE_INSEGURA = "dev-inseguro-troque-no-env"


def create_app(nome_config: str | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(obter_config(nome_config))

    if not app.debug and not app.testing and app.config["SECRET_KEY"] == CHAVE_INSEGURA:
        raise RuntimeError("Defina SECRET_KEY no .env antes de rodar em produção.")

    if app.config["ATRAS_DE_PROXY"]:
        # O Nginx informa o IP real e o protocolo (http/https) do visitante.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # type: ignore[method-assign]

    if app.config["ARMAZENAMENTO"] == "disco":
        Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    _iniciar_extensoes(app)
    _registrar_blueprints(app)
    _registrar_erros(app)
    _registrar_contexto_templates(app)
    _registrar_comandos(app)
    _configurar_log(app)
    return app


def _iniciar_extensoes(app: Flask) -> None:
    from app import models  # noqa: F401  (registra as tabelas)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def carregar_usuario(usuario_id: str) -> "models.Usuario | None":
        return db.session.get(models.Usuario, int(usuario_id))


def _registrar_blueprints(app: Flask) -> None:
    from app.routes import albuns, auth, notificacoes, perfil, polaroids, saude, timeline

    for modulo in (saude, auth, timeline, polaroids, perfil, albuns, notificacoes):
        app.register_blueprint(modulo.bp)


def _pagina_de_erro(codigo: int, mensagem: str):  # type: ignore[no-untyped-def]
    if request.is_json or request.accept_mimetypes.best == "application/json":
        return jsonify(erro=mensagem), codigo
    return render_template("erros/erro.html", codigo=codigo, mensagem=mensagem), codigo


def _voltar():  # type: ignore[no-untyped-def]
    """Volta para a página anterior, só se ela for deste mesmo site."""
    anterior = request.referrer or ""
    if anterior.startswith(request.host_url):
        return redirect(anterior)
    return redirect(url_for("timeline.index"))


def _registrar_erros(app: Flask) -> None:
    @app.errorhandler(ErroDeNegocio)
    def erro_de_negocio(erro: ErroDeNegocio):  # type: ignore[no-untyped-def]
        db.session.rollback()  # desfaz alterações pela metade
        if isinstance(erro, (NaoEncontrado, AcessoNegado)):
            return _pagina_de_erro(erro.codigo_http, str(erro))
        if request.is_json or request.accept_mimetypes.best == "application/json":
            return jsonify(erro=str(erro)), erro.codigo_http
        flash(str(erro), "erro")
        return _voltar()

    @app.errorhandler(CSRFError)
    def erro_csrf(_erro: CSRFError):  # type: ignore[no-untyped-def]
        return _pagina_de_erro(400, "O formulário expirou. Recarregue a página e tente de novo.")

    @app.errorhandler(HTTPException)
    def erro_http(erro: HTTPException):  # type: ignore[no-untyped-def]
        mensagens = {
            403: "Você não tem permissão para ver este registro.",
            404: "Este registro não está disponível.",
            413: "O arquivo enviado é grande demais.",
        }
        codigo = erro.code or 500
        return _pagina_de_erro(codigo, mensagens.get(codigo, erro.description or "Erro."))

    if app.testing:
        return  # nos testes o erro real deve aparecer no pytest

    @app.errorhandler(Exception)
    def erro_inesperado(erro: Exception):  # type: ignore[no-untyped-def]
        db.session.rollback()
        app.logger.exception("Erro inesperado: %s", erro)
        return _pagina_de_erro(500, "Algo deu errado do nosso lado. Tente novamente.")


def _registrar_contexto_templates(app: Flask) -> None:
    from app.services.notificacao_service import NotificacaoService

    @app.context_processor
    def variaveis_globais() -> dict[str, object]:
        nao_lidas = 0
        if current_user.is_authenticated:
            nao_lidas = NotificacaoService().contar_nao_lidas(current_user)
        return {
            "notificacoes_nao_lidas": nao_lidas,
            "Emocao": Emocao,
            "EstadoMemoria": EstadoMemoria,
        }


def _registrar_comandos(app: Flask) -> None:
    @app.cli.command("limpar-lixeira")
    def limpar_lixeira() -> None:
        """Apaga de vez as memórias com 30 dias ou mais na Lixeira (RN14)."""
        from app.services.polaroid_service import PolaroidService

        total = PolaroidService().limpar_lixeira_expirada()
        click.echo(f"{total} memória(s) apagada(s) de vez.")


def _configurar_log(app: Flask) -> None:
    formato = logging.Formatter(
        f"%(asctime)s [%(levelname)s] [{app.config['INSTANCIA']}] %(name)s: %(message)s"
    )
    if app.config.get("LOG_FILE"):
        # A rotação do arquivo fica com o logrotate (Fase 4).
        arquivo = logging.FileHandler(app.config["LOG_FILE"], encoding="utf-8")
        arquivo.setFormatter(formato)
        arquivo.setLevel(logging.INFO)
        app.logger.addHandler(arquivo)
    app.logger.setLevel(logging.INFO)
