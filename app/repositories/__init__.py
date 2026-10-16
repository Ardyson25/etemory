"""Repositórios: toda consulta ao banco passa por aqui."""

from app.repositories.album_repository import AlbumRepository
from app.repositories.notificacao_repository import NotificacaoRepository
from app.repositories.polaroid_repository import PolaroidRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.repositories.vinculo_repository import VinculoRepository

__all__ = [
    "AlbumRepository",
    "NotificacaoRepository",
    "PolaroidRepository",
    "UsuarioRepository",
    "VinculoRepository",
]
