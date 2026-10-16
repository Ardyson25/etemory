"""Cadastro e autenticação (RF01, RF02)."""

from app.domain.excecoes import ErroDeNegocio
from app.domain.validacoes import validar_email, validar_username
from app.extensions import db
from app.models import Usuario
from app.repositories import UsuarioRepository


class AuthService:
    def __init__(self) -> None:
        self.usuarios = UsuarioRepository()

    def cadastrar(self, nome: str, username: str, email: str, senha: str) -> Usuario:
        username = validar_username(username)
        email = validar_email(email)
        if self.usuarios.username_existe(username):
            raise ErroDeNegocio("Este @username já está em uso.")  # RN12
        if self.usuarios.email_existe(email):
            raise ErroDeNegocio("Já existe uma conta com este e-mail.")
        usuario = Usuario(nome=nome, username=username, email=email, senha=senha)
        self.usuarios.adicionar(usuario)
        db.session.commit()
        return usuario

    def autenticar(self, login: str, senha: str) -> Usuario | None:
        """Devolve o usuário ou ``None``, sem dizer qual dado estava errado."""
        usuario = self.usuarios.por_login(login)
        if usuario is None or not usuario.verificar_senha(senha):
            return None
        return usuario
