"""Formulários do Prontuário e das configurações."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, Length, Optional

from app.domain.enums import ModoComentarios
from app.domain.validacoes import BIO_MAX, NOME_MAX, SENHA_MIN
from app.forms.comum import https_opcional, validadores_imagem


class PerfilForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(max=NOME_MAX)])
    bio = TextAreaField("Bio", validators=[Optional(), Length(max=BIO_MAX)])
    site = StringField("Site", validators=[Optional(), https_opcional])
    foto = FileField("Foto de perfil", validators=validadores_imagem())
    capa = FileField("Capa", validators=validadores_imagem())
    enviar = SubmitField("Salvar Prontuário")


class ConfiguracoesForm(FlaskForm):
    conta_privada = BooleanField("Conta privada")
    modo_comentarios_padrao = SelectField(
        "Quem pode comentar nas novas memórias", choices=ModoComentarios.opcoes()
    )
    enviar = SubmitField("Salvar configurações")


class SenhaForm(FlaskForm):
    senha_atual = PasswordField("Senha atual", validators=[DataRequired()])
    nova_senha = PasswordField(
        "Nova senha", validators=[DataRequired(), Length(min=SENHA_MIN)]
    )
    confirmar = PasswordField(
        "Confirmar nova senha",
        validators=[DataRequired(), EqualTo("nova_senha", "As senhas não conferem.")],
    )
    enviar_senha = SubmitField("Alterar senha")
