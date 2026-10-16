"""Formulário de álbum."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from app.domain.validacoes import DESCRICAO_ALBUM_MAX, TITULO_ALBUM_MAX


class AlbumForm(FlaskForm):
    titulo = StringField(
        "Título", validators=[DataRequired(), Length(max=TITULO_ALBUM_MAX)]
    )
    descricao = TextAreaField(
        "Descrição", validators=[Optional(), Length(max=DESCRICAO_ALBUM_MAX)]
    )
    publico = BooleanField("Álbum público", default=True)
    enviar = SubmitField("Salvar álbum")
