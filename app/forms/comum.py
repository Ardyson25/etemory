"""Validadores reutilizados pelos formulários."""

from flask_wtf.file import FileAllowed, FileSize
from wtforms import Field, Form
from wtforms.validators import ValidationError

from app.domain.excecoes import ErroDeNegocio
from app.domain.validacoes import validar_url_https

EXTENSOES_IMAGEM = ["jpg", "jpeg", "png", "webp"]
LIMITE_IMAGEM = 5 * 1024 * 1024


def validadores_imagem() -> list[object]:
    """RN18 na tela; o ``MidiaService`` confere de novo pelo conteúdo."""
    return [
        FileAllowed(EXTENSOES_IMAGEM, "Envie uma imagem JPEG, PNG ou WebP."),
        FileSize(LIMITE_IMAGEM, message="A imagem pode ter no máximo 5 MB."),
    ]


def https_opcional(_form: Form, campo: Field) -> None:
    """RN17 na tela."""
    try:
        validar_url_https(campo.data, "O link")
    except ErroDeNegocio as erro:
        raise ValidationError(str(erro)) from None
