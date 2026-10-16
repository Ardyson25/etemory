"""Polaroids, curtidas, comentários, Arquivo e Lixeira."""

from io import BytesIO

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required

from app.domain.excecoes import ErroDeNegocio
from app.extensions import db
from app.forms import ComentarioForm, PolaroidForm
from app.routes._comum import arquivo_enviado, dados_da_polaroid
from app.services.album_service import AlbumService
from app.services.interacao_service import InteracaoService
from app.services.midia_service import TIPO_SAIDA
from app.services.polaroid_service import PolaroidService

bp = Blueprint("polaroids", __name__)


@bp.route("/polaroids/nova", methods=["GET", "POST"])
@login_required
def nova() -> ResponseReturnValue:
    form = PolaroidForm()
    if request.method == "GET":
        form.modo_comentarios.data = current_user.modo_comentarios_padrao.name
    if form.validate_on_submit():
        foto = arquivo_enviado(form.foto.data)
        if foto is None:
            form.foto.errors.append("Escolha a foto da memória.")
        else:
            try:
                polaroid = PolaroidService().publicar(
                    current_user, dados_da_polaroid(form), foto.stream
                )
            except ErroDeNegocio as erro:
                flash(str(erro), "erro")
            else:
                flash("Memória registrada.", "sucesso")
                return redirect(url_for("polaroids.detalhe", polaroid_id=polaroid.id))
    return render_template("polaroids/form.html", form=form, polaroid=None)


@bp.route("/polaroids/<int:polaroid_id>/editar", methods=["GET", "POST"])
@login_required
def editar(polaroid_id: int) -> ResponseReturnValue:
    servico = PolaroidService()
    polaroid = servico.obter_do_autor(current_user, polaroid_id)
    form = PolaroidForm()
    if request.method == "GET":
        form.legenda.data = polaroid.legenda
        form.data_memoria.data = polaroid.data_memoria
        form.emocoes.data = [e.name for e in polaroid.emocoes]
        form.estado.data = polaroid.estado.name
        form.visibilidade.data = polaroid.visibilidade.name
        form.modo_comentarios.data = polaroid.modo_comentarios.name
        form.musica_titulo.data = polaroid.musica_titulo
        form.musica_artista.data = polaroid.musica_artista
        form.musica_url.data = polaroid.musica_url
        form.local_nome.data = polaroid.local_nome
    if form.validate_on_submit():
        try:
            servico.editar(current_user, polaroid_id, dados_da_polaroid(form))
        except ErroDeNegocio as erro:
            db.session.rollback()
            flash(str(erro), "erro")
        else:
            flash("Memória atualizada.", "sucesso")
            return redirect(url_for("polaroids.detalhe", polaroid_id=polaroid_id))
    return render_template("polaroids/form.html", form=form, polaroid=polaroid)


@bp.get("/polaroids/<int:polaroid_id>")
@login_required
def detalhe(polaroid_id: int) -> ResponseReturnValue:
    servico = PolaroidService()
    polaroid = servico.obter_visivel(current_user, polaroid_id)
    albuns = []
    if polaroid.autor_id == current_user.id:
        albuns = AlbumService().do_usuario(current_user, current_user)
    return render_template(
        "polaroids/detalhe.html",
        polaroid=polaroid,
        pode_comentar=servico.pode_comentar(current_user, polaroid),
        form_comentario=ComentarioForm(),
        albuns=albuns,
    )


# ---------- Curtidas e comentários ----------


@bp.post("/polaroids/<int:polaroid_id>/curtir")
@login_required
def curtir(polaroid_id: int) -> ResponseReturnValue:
    curtiu, total = InteracaoService().alternar_curtida(current_user, polaroid_id)
    if request.accept_mimetypes.best == "application/json":
        return jsonify(curtiu=curtiu, total=total)
    return redirect(url_for("polaroids.detalhe", polaroid_id=polaroid_id))


@bp.post("/polaroids/<int:polaroid_id>/comentarios")
@login_required
def comentar(polaroid_id: int) -> ResponseReturnValue:
    form = ComentarioForm()
    if form.validate_on_submit():
        comentario = InteracaoService().comentar(current_user, polaroid_id, form.texto.data)
        return redirect(
            url_for(
                "polaroids.detalhe",
                polaroid_id=polaroid_id,
                _anchor=f"comentario-{comentario.id}",
            )
        )
    for erros in form.errors.values():
        flash(erros[0], "erro")
    return redirect(url_for("polaroids.detalhe", polaroid_id=polaroid_id))


@bp.post("/comentarios/<int:comentario_id>/editar")
@login_required
def editar_comentario(comentario_id: int) -> ResponseReturnValue:
    comentario = InteracaoService().editar_comentario(
        current_user, comentario_id, request.form.get("texto", "")
    )
    return redirect(
        url_for(
            "polaroids.detalhe",
            polaroid_id=comentario.polaroid_id,
            _anchor=f"comentario-{comentario.id}",
        )
    )


@bp.post("/comentarios/<int:comentario_id>/excluir")
@login_required
def excluir_comentario(comentario_id: int) -> ResponseReturnValue:
    polaroid_id = InteracaoService().excluir_comentario(current_user, comentario_id)
    flash("Comentário excluído.", "sucesso")
    return redirect(url_for("polaroids.detalhe", polaroid_id=polaroid_id))


# ---------- Arquivo e Lixeira ----------


@bp.post("/polaroids/<int:polaroid_id>/arquivar")
@login_required
def arquivar(polaroid_id: int) -> ResponseReturnValue:
    PolaroidService().arquivar(current_user, polaroid_id)
    flash("Memória movida para o Arquivo Pessoal.", "sucesso")
    return redirect(url_for("polaroids.arquivo"))


@bp.post("/polaroids/<int:polaroid_id>/desarquivar")
@login_required
def desarquivar(polaroid_id: int) -> ResponseReturnValue:
    PolaroidService().desarquivar(current_user, polaroid_id)
    flash("Memória de volta ao Prontuário.", "sucesso")
    return redirect(url_for("polaroids.detalhe", polaroid_id=polaroid_id))


@bp.post("/polaroids/<int:polaroid_id>/excluir")
@login_required
def excluir(polaroid_id: int) -> ResponseReturnValue:
    PolaroidService().mover_para_lixeira(current_user, polaroid_id)
    flash("Memória movida para a Lixeira. Você tem 30 dias para restaurar.", "sucesso")
    return redirect(url_for("polaroids.lixeira"))


@bp.post("/polaroids/<int:polaroid_id>/restaurar")
@login_required
def restaurar(polaroid_id: int) -> ResponseReturnValue:
    PolaroidService().restaurar(current_user, polaroid_id)
    flash("Memória restaurada.", "sucesso")
    return redirect(url_for("polaroids.detalhe", polaroid_id=polaroid_id))


@bp.get("/arquivo")
@login_required
def arquivo() -> ResponseReturnValue:
    polaroids = PolaroidService().arquivadas(current_user)
    return render_template("polaroids/arquivo.html", polaroids=polaroids)


@bp.get("/lixeira")
@login_required
def lixeira() -> ResponseReturnValue:
    polaroids = PolaroidService().na_lixeira(current_user)
    return render_template("polaroids/lixeira.html", polaroids=polaroids)


# ---------- Arquivos de imagem ----------


@bp.get("/midia/<nome>")
@login_required
def midia(nome: str) -> ResponseReturnValue:
    """Entrega a foto só para quem pode ver (RN01, RN02)."""
    servico = PolaroidService()
    servico.verificar_acesso_midia(current_user, nome)
    dados = servico.midias.ler(nome)
    if dados is None:
        abort(404)
    # "private": o navegador guarda a foto, mas proxies compartilhados não.
    resposta = send_file(BytesIO(dados), mimetype=TIPO_SAIDA, max_age=3600)
    resposta.cache_control.private = True
    resposta.cache_control.public = False
    return resposta
