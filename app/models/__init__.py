"""Modelos SQLAlchemy (tabelas). Importar aqui registra todos no metadata."""

from app.models.album import Album, album_polaroid
from app.models.arquivo import Arquivo
from app.models.interacoes import Comentario, Curtida
from app.models.notificacao import (
    Notificacao,
    NotificacaoComentario,
    NotificacaoCurtida,
    NotificacaoMencao,
    NotificacaoSeguidor,
    NotificacaoSolicitacao,
    NotificacaoSolicitacaoAceita,
)
from app.models.polaroid import Midia, Polaroid, PolaroidEmocao
from app.models.usuario import Usuario
from app.models.vinculo import Vinculo

__all__ = [
    "Album",
    "album_polaroid",
    "Arquivo",
    "Comentario",
    "Curtida",
    "Midia",
    "Notificacao",
    "NotificacaoComentario",
    "NotificacaoCurtida",
    "NotificacaoMencao",
    "NotificacaoSeguidor",
    "NotificacaoSolicitacao",
    "NotificacaoSolicitacaoAceita",
    "Polaroid",
    "PolaroidEmocao",
    "Usuario",
    "Vinculo",
]
