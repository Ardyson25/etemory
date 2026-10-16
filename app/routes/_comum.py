"""Funções pequenas usadas por várias rotas."""

from urllib.parse import urlparse

from flask import request
from werkzeug.datastructures import FileStorage

from app.domain.enums import Emocao, EstadoMemoria, ModoComentarios, Visibilidade
from app.forms import PolaroidForm
from app.services.polaroid_service import DadosPolaroid


def pagina_atual() -> int:
    return max(1, request.args.get("pagina", 1, type=int) or 1)


def arquivo_enviado(campo_data: object) -> FileStorage | None:
    """Devolve o arquivo só se o usuário realmente escolheu um."""
    if isinstance(campo_data, FileStorage) and campo_data.filename:
        return campo_data
    return None


def destino_seguro(destino: str | None) -> str | None:
    """Aceita só caminhos internos no ?next= (evita redirecionar para fora)."""
    if not destino:
        return None
    partes = urlparse(destino)
    if partes.scheme or partes.netloc or not destino.startswith("/"):
        return None
    return destino


def dados_da_polaroid(form: PolaroidForm) -> DadosPolaroid:
    """Converte o formulário (textos) nos tipos do domínio (enums, datas)."""
    return DadosPolaroid(
        legenda=form.legenda.data or "",
        data_memoria=form.data_memoria.data,
        emocoes=[Emocao[nome] for nome in (form.emocoes.data or [])],
        estado=EstadoMemoria[form.estado.data],
        visibilidade=Visibilidade[form.visibilidade.data],
        modo_comentarios=ModoComentarios[form.modo_comentarios.data],
        musica_titulo=form.musica_titulo.data,
        musica_artista=form.musica_artista.data,
        musica_url=form.musica_url.data,
        local_nome=form.local_nome.data,
    )
