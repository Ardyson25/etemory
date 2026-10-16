"""Notificações (RF24). Sem tempo real: atualizam ao carregar a página."""

from flask import Blueprint, redirect, render_template, url_for
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required

from app.routes._comum import pagina_atual
from app.services.notificacao_service import NotificacaoService

bp = Blueprint("notificacoes", __name__, url_prefix="/notificacoes")


@bp.get("/")
@login_required
def lista() -> ResponseReturnValue:
    pagina = NotificacaoService().listar(current_user, pagina_atual())
    return render_template("notificacoes/lista.html", pagina=pagina)


@bp.post("/<int:notificacao_id>/abrir")
@login_required
def abrir(notificacao_id: int) -> ResponseReturnValue:
    return redirect(NotificacaoService().abrir(current_user, notificacao_id))


@bp.post("/marcar-todas")
@login_required
def marcar_todas() -> ResponseReturnValue:
    NotificacaoService().marcar_todas_como_lidas(current_user)
    return redirect(url_for("notificacoes.lista"))
