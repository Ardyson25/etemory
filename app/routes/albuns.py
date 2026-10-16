"""Álbuns (RF25–RF27)."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required

from app.domain.excecoes import ErroDeNegocio
from app.forms import AlbumForm
from app.services.album_service import AlbumService

bp = Blueprint("albuns", __name__, url_prefix="/albuns")


@bp.get("/")
@login_required
def lista() -> ResponseReturnValue:
    return redirect(url_for("perfil.prontuario", username=current_user.username, aba="albuns"))


@bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo() -> ResponseReturnValue:
    form = AlbumForm()
    if form.validate_on_submit():
        try:
            album = AlbumService().criar(
                current_user, form.titulo.data, form.descricao.data, form.publico.data
            )
        except ErroDeNegocio as erro:
            flash(str(erro), "erro")
        else:
            return redirect(url_for("albuns.detalhe", album_id=album.id))
    return render_template("albuns/form.html", form=form, album=None)


@bp.route("/<int:album_id>/editar", methods=["GET", "POST"])
@login_required
def editar(album_id: int) -> ResponseReturnValue:
    servico = AlbumService()
    album = servico.obter_do_dono(current_user, album_id)
    form = AlbumForm(obj=album)
    if request.method == "GET":
        form.publico.data = album.eh_publico
    if form.validate_on_submit():
        servico.editar(
            current_user, album_id, form.titulo.data, form.descricao.data, form.publico.data
        )
        return redirect(url_for("albuns.detalhe", album_id=album_id))
    return render_template("albuns/form.html", form=form, album=album)


@bp.get("/<int:album_id>")
@login_required
def detalhe(album_id: int) -> ResponseReturnValue:
    servico = AlbumService()
    album = servico.obter_visivel(current_user, album_id)
    return render_template(
        "albuns/detalhe.html",
        album=album,
        polaroids=servico.polaroids_visiveis(current_user, album),
    )


@bp.post("/<int:album_id>/excluir")
@login_required
def excluir(album_id: int) -> ResponseReturnValue:
    AlbumService().excluir(current_user, album_id)
    flash("Álbum excluído. As memórias continuam no seu Prontuário.", "sucesso")
    return redirect(url_for("albuns.lista"))


@bp.post("/adicionar")
@login_required
def adicionar() -> ResponseReturnValue:
    album_id = request.form.get("album_id", type=int) or 0
    polaroid_id = request.form.get("polaroid_id", type=int) or 0
    AlbumService().adicionar(current_user, album_id, polaroid_id)
    flash("Memória adicionada ao álbum.", "sucesso")
    return redirect(url_for("albuns.detalhe", album_id=album_id))


@bp.post("/<int:album_id>/remover/<int:polaroid_id>")
@login_required
def remover(album_id: int, polaroid_id: int) -> ResponseReturnValue:
    AlbumService().remover(current_user, album_id, polaroid_id)
    return redirect(url_for("albuns.detalhe", album_id=album_id))
