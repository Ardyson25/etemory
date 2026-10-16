"""Timeline com as abas "Para você" e "Vínculos" (RF17–RF19)."""

from flask import Blueprint, render_template, request
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required

from app.routes._comum import pagina_atual
from app.services.timeline_service import TimelineService

bp = Blueprint("timeline", __name__)


@bp.get("/")
@login_required
def index() -> ResponseReturnValue:
    aba = request.args.get("aba", "para-voce")
    servico = TimelineService()
    if aba == "vinculos":
        pagina = servico.de_vinculos(current_user, pagina_atual())
    else:
        aba = "para-voce"
        pagina = servico.para_voce(current_user, pagina_atual())
    return render_template("timeline/index.html", aba=aba, pagina=pagina)
