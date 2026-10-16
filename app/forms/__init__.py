"""Formulários Flask-WTF.

Todo ``FlaskForm`` inclui o token CSRF automaticamente (RNF02). As
validações daqui melhoram a experiência na tela; as regras de verdade
são conferidas de novo nos modelos e serviços.
"""

from app.forms.album import AlbumForm
from app.forms.auth import CadastroForm, LoginForm
from app.forms.perfil import ConfiguracoesForm, PerfilForm, SenhaForm
from app.forms.polaroid import ComentarioForm, PolaroidForm

__all__ = [
    "AlbumForm",
    "CadastroForm",
    "ComentarioForm",
    "ConfiguracoesForm",
    "LoginForm",
    "PerfilForm",
    "PolaroidForm",
    "SenhaForm",
]
