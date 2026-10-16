"""Cadastro, entrada e saída (RF01, RF02)."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required, login_user, logout_user

from app.domain.excecoes import ErroDeNegocio
from app.forms import CadastroForm, LoginForm
from app.routes._comum import destino_seguro
from app.services.auth_service import AuthService

bp = Blueprint("auth", __name__)


@bp.route("/entrar", methods=["GET", "POST"])
def entrar() -> ResponseReturnValue:
    if current_user.is_authenticated:
        return redirect(url_for("timeline.index"))
    form = LoginForm()
    if form.validate_on_submit():
        usuario = AuthService().autenticar(form.login.data, form.senha.data)
        if usuario is None:
            flash("E-mail ou senha incorretos.", "erro")
        else:
            login_user(usuario, remember=form.lembrar.data)
            destino = destino_seguro(request.args.get("next"))
            return redirect(destino or url_for("timeline.index"))
    return render_template("auth/entrar.html", form=form)


@bp.route("/cadastro", methods=["GET", "POST"])
def cadastro() -> ResponseReturnValue:
    if current_user.is_authenticated:
        return redirect(url_for("timeline.index"))
    form = CadastroForm()
    if form.validate_on_submit():
        try:
            usuario = AuthService().cadastrar(
                form.nome.data, form.username.data, form.email.data, form.senha.data
            )
        except ErroDeNegocio as erro:
            flash(str(erro), "erro")
        else:
            login_user(usuario)
            flash("Bem-vindo(a) ao Etermory!", "sucesso")
            return redirect(url_for("timeline.index"))
    return render_template("auth/cadastro.html", form=form)


@bp.post("/sair")
@login_required
def sair() -> ResponseReturnValue:
    logout_user()
    return redirect(url_for("auth.entrar"))
