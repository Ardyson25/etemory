"""Formulários da Polaroid e do comentário."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (
    DateField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from wtforms.widgets import CheckboxInput, ListWidget

from app.domain.enums import Emocao, EstadoMemoria, ModoComentarios, Visibilidade
from app.domain.validacoes import COMENTARIO_MAX, LEGENDA_MAX, MAX_EMOCOES
from app.forms.comum import https_opcional, validadores_imagem


class CaixasDeSelecao(SelectMultipleField):
    """Lista de checkboxes (usada nas emoções)."""

    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class PolaroidForm(FlaskForm):
    foto = FileField("Foto", validators=validadores_imagem())
    legenda = TextAreaField(
        "Legenda", validators=[DataRequired("A legenda é obrigatória."), Length(max=LEGENDA_MAX)]
    )
    data_memoria = DateField("Data da memória", validators=[Optional()])
    emocoes = CaixasDeSelecao("Emoções (até 3)", choices=Emocao.opcoes())
    estado = SelectField(
        "Estado da memória",
        choices=EstadoMemoria.opcoes(),
        default=EstadoMemoria.PRESERVADA.name,
    )
    visibilidade = SelectField(
        "Quem pode ver", choices=Visibilidade.opcoes(), default=Visibilidade.AUTOMATICA.name
    )
    modo_comentarios = SelectField("Quem pode comentar", choices=ModoComentarios.opcoes())
    musica_titulo = StringField("Música", validators=[Optional(), Length(max=120)])
    musica_artista = StringField("Artista", validators=[Optional(), Length(max=120)])
    musica_url = StringField("Link do Spotify", validators=[Optional(), https_opcional])
    local_nome = StringField("Local", validators=[Optional(), Length(max=120)])
    enviar = SubmitField("Registrar memória")

    def validate_emocoes(self, campo: CaixasDeSelecao) -> None:
        if len(campo.data or []) > MAX_EMOCOES:
            raise ValidationError(f"Escolha no máximo {MAX_EMOCOES} emoções.")


class ComentarioForm(FlaskForm):
    texto = TextAreaField(
        "Comentário",
        validators=[DataRequired("Escreva algo."), Length(max=COMENTARIO_MAX)],
    )
    enviar = SubmitField("Comentar")
