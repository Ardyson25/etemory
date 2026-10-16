"""Consultas de usuários."""

from collections.abc import Iterable

from sqlalchemy import func, or_, select

from app.extensions import db
from app.models import Usuario
from app.repositories.base import RepositorioBase


class UsuarioRepository(RepositorioBase[Usuario]):
    modelo = Usuario
    mensagem_nao_encontrado = "Usuário não encontrado."

    def por_username(self, username: str) -> Usuario | None:
        username = (username or "").strip().lstrip("@").lower()
        return db.session.scalar(select(Usuario).where(Usuario.username == username))

    def por_email(self, email: str) -> Usuario | None:
        email = (email or "").strip().lower()
        return db.session.scalar(select(Usuario).where(Usuario.email == email))

    def por_login(self, login: str) -> Usuario | None:
        """Aceita e-mail ou @username."""
        login = (login or "").strip()
        if "@" in login.lstrip("@"):
            return self.por_email(login)
        return self.por_username(login)

    def por_usernames(self, usernames: Iterable[str]) -> list[Usuario]:
        nomes = {nome.lower() for nome in usernames}
        if not nomes:
            return []
        return list(db.session.scalars(select(Usuario).where(Usuario.username.in_(nomes))))

    def imagem_de_perfil_existe(self, nome_arquivo: str) -> bool:
        consulta = select(func.count()).where(
            or_(Usuario.foto == nome_arquivo, Usuario.capa == nome_arquivo)
        )
        return bool(db.session.scalar(consulta))

    def username_existe(self, username: str) -> bool:
        return self.por_username(username) is not None

    def email_existe(self, email: str) -> bool:
        consulta = select(func.count()).where(Usuario.email == email.strip().lower())
        return bool(db.session.scalar(consulta))
