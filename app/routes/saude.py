"""Rota de saúde usada pelo Nginx e pelo teste de failover (RF31)."""

from flask import Blueprint, current_app, jsonify
from flask.typing import ResponseReturnValue

bp = Blueprint("saude", __name__)


@bp.get("/saude")
def saude() -> ResponseReturnValue:
    """Responde sem login, mostrando qual instância atendeu."""
    return jsonify(status="ok", instancia=current_app.config["INSTANCIA"])
