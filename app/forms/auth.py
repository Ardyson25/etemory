"""Formulários de entrada e cadastro."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp

from app.domain.validacoes import NOME_MAX, SENHA_MIN


class LoginForm(FlaskForm):
    login = StringField("E-mail ou @username", validators=[DataRequired()])
    senha = PasswordField("Senha", validators=[DataRequired()])
    lembrar = BooleanField("Manter conectado")
    enviar = SubmitField("Entrar")


class CadastroForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(max=NOME_MAX)])
    username = StringField(
        "@username",
        validators=[
            DataRequired(),
            Regexp(
                r"^@?[a-z0-9._]{3,24}$",
                message="Use de 3 a 24 letras minúsculas, números, ponto ou sublinhado.",
            ),
        ],
    )
    email = EmailField("E-mail", validators=[DataRequired(), Email("E-mail inválido.")])
    senha = PasswordField(
        "Senha",
        validators=[
            DataRequired(),
            Length(min=SENHA_MIN, message=f"Mínimo de {SENHA_MIN} caracteres."),
        ],
    )
    confirmar = PasswordField(
        "Confirmar senha",
        validators=[DataRequired(), EqualTo("senha", "As senhas não conferem.")],
    )
    enviar = SubmitField("Criar conta")
