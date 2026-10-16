"""Consultas de álbuns."""

from sqlalchemy import select

from app.domain.enums import Visibilidade
from app.extensions import db
from app.models import Album
from app.repositories.base import RepositorioBase


class AlbumRepository(RepositorioBase[Album]):
    modelo = Album
    mensagem_nao_encontrado = "Álbum não encontrado."

    def do_dono(self, dono_id: int, incluir_privados: bool) -> list[Album]:
        consulta = select(Album).where(Album.dono_id == dono_id)
        if not incluir_privados:
            consulta = consulta.where(Album.visibilidade == Visibilidade.PUBLICA)
        return list(db.session.scalars(consulta.order_by(Album.criado_em.desc())))
