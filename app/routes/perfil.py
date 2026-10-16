"""Prontuário, vínculos e configurações (RF03–RF06, RF13–RF16)."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required

from app.domain.enums import ModoComentarios
from app.domain.excecoes import ErroDeNegocio, NaoEncontrado
from app.extensions import db
from app.forms import ConfiguracoesForm, PerfilForm, SenhaForm
from app.models import Usuario
from app.repositories import UsuarioRepository
from app.routes._comum import arquivo_enviado, pagina_atual
from app.services.album_service import AlbumService
from app.services.timeline_service import TimelineService
from app.services.usuario_service import UsuarioService
from app.services.vinculo_service import EstadoRelacao, VinculoService

bp = Blueprint("perfil", __name__)


def _usuario_ou_404(username: str) -> Usuario:
    usuario = UsuarioRepository().por_username(username)
    if usuario is None:
        raise NaoEncontrado("Prontuário não encontrado.")
    return usuario


@bp.get("/@<username>")
@login_required
def prontuario(username: str) -> ResponseReturnValue:
    dono = _usuario_ou_404(username)
    vinculos = VinculoService()
    aba = request.args.get("aba", "memorias")
    pagina = None
    albuns = []
    if aba == "albuns":
        albuns = AlbumService().do_usuario(current_user, dono)
    else:
        aba = "memorias"
        pagina = TimelineService().do_perfil(current_user, dono, pagina_atual())
    return render_template(
        "perfil/prontuario.html",
        dono=dono,
        aba=aba,
        pagina=pagina,
        albuns=albuns,
        relacao=vinculos.estado_relacao(current_user, dono),
        EstadoRelacao=EstadoRelacao,
        contadores=vinculos.contadores(dono),
    )


@bp.get("/@<username>/seguidores")
@login_required
def seguidores(username: str) -> ResponseReturnValue:
    dono = _usuario_ou_404(username)
    usuarios = VinculoService().seguidores(dono)
    return render_template(
        "perfil/lista_usuarios.html", dono=dono, usuarios=usuarios, titulo="Seguidores"
    )


@bp.get("/@<username>/seguindo")
@login_required
def seguindo(username: str) -> ResponseReturnValue:
    dono = _usuario_ou_404(username)
    usuarios = VinculoService().seguindo(dono)
    return render_template(
        "perfil/lista_usuarios.html", dono=dono, usuarios=usuarios, titulo="Seguindo"
    )


# ---------- Vínculos ----------


@bp.post("/@<username>/seguir")
@login_required
def seguir(username: str) -> ResponseReturnValue:
    vinculo = VinculoService().seguir(current_user, _usuario_ou_404(username))
    if vinculo.esta_pendente:
        flash("Solicitação de vínculo enviada.", "sucesso")
    return redirect(url_for("perfil.prontuario", username=username))


@bp.post("/@<username>/deixar-de-seguir")
@login_required
def deixar_de_seguir(username: str) -> ResponseReturnValue:
    VinculoService().deixar_de_seguir(current_user, _usuario_ou_404(username))
    return redirect(url_for("perfil.prontuario", username=username))


@bp.post("/@<username>/cancelar-solicitacao")
@login_required
def cancelar_solicitacao(username: str) -> ResponseReturnValue:
    VinculoService().cancelar_solicitacao(current_user, _usuario_ou_404(username))
    return redirect(url_for("perfil.prontuario", username=username))


@bp.get("/vinculos/solicitacoes")
@login_required
def solicitacoes() -> ResponseReturnValue:
    pendentes = VinculoService().solicitacoes_pendentes(current_user)
    return render_template("perfil/solicitacoes.html", pendentes=pendentes)


@bp.post("/vinculos/<int:vinculo_id>/<acao>")
@login_required
def responder(vinculo_id: int, acao: str) -> ResponseReturnValue:
    if acao not in ("aceitar", "recusar"):
        raise NaoEncontrado("Ação inválida.")
    VinculoService().responder(current_user, vinculo_id, aceitar=acao == "aceitar")
    return redirect(url_for("perfil.solicitacoes"))


@bp.get("/vinculos/melhores-amigos")
@login_required
def melhores_amigos() -> ResponseReturnValue:
    vinculos = VinculoService().vinculos_de_seguidores(current_user)
    return render_template("perfil/melhores_amigos.html", vinculos=vinculos)


@bp.post("/vinculos/melhores-amigos/<int:seguidor_id>")
@login_required
def alternar_melhor_amigo(seguidor_id: int) -> ResponseReturnValue:
    VinculoService().alternar_melhor_amigo(current_user, seguidor_id)
    return redirect(url_for("perfil.melhores_amigos"))


# ---------- Edição e configurações ----------


@bp.route("/perfil/editar", methods=["GET", "POST"])
@login_required
def editar() -> ResponseReturnValue:
    form = PerfilForm(obj=current_user)
    if form.validate_on_submit():
        try:
            UsuarioService().atualizar_perfil(
                current_user,
                nome=form.nome.data,
                bio=form.bio.data,
                site=form.site.data,
                foto=_stream(form.foto.data),
                capa=_stream(form.capa.data),
            )
        except ErroDeNegocio as erro:
            flash(str(erro), "erro")
        else:
            flash("Prontuário atualizado.", "sucesso")
            return redirect(url_for("perfil.prontuario", username=current_user.username))
    return render_template("perfil/editar.html", form=form)


def _stream(dado: object):  # type: ignore[no-untyped-def]
    arquivo = arquivo_enviado(dado)
    return arquivo.stream if arquivo else None


@bp.route("/configuracoes", methods=["GET", "POST"])
@login_required
def configuracoes() -> ResponseReturnValue:
    form = ConfiguracoesForm(prefix="cfg")
    form_senha = SenhaForm(prefix="senha")
    servico = UsuarioService()

    if request.method == "GET":
        form.conta_privada.data = current_user.conta_privada
        form.modo_comentarios_padrao.data = current_user.modo_comentarios_padrao.name

    if form.enviar.data and form.validate_on_submit():
        servico.configurar(
            current_user,
            conta_privada=form.conta_privada.data,
            modo_comentarios_padrao=ModoComentarios[form.modo_comentarios_padrao.data],
        )
        flash("Configurações salvas.", "sucesso")
        return redirect(url_for("perfil.configuracoes"))

    if form_senha.enviar_senha.data and form_senha.validate_on_submit():
        try:
            servico.alterar_senha(
                current_user, form_senha.senha_atual.data, form_senha.nova_senha.data
            )
        except ErroDeNegocio as erro:
            db.session.rollback()
            flash(str(erro), "erro")
        else:
            flash("Senha alterada.", "sucesso")
            return redirect(url_for("perfil.configuracoes"))

    return render_template("perfil/configuracoes.html", form=form, form_senha=form_senha)
