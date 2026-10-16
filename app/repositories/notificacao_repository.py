"""Consultas de notificações."""

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Notificacao
from app.repositories.base import RepositorioBase


class NotificacaoRepository(RepositorioBase[Notificacao]):
    modelo = Notificacao
    mensagem_nao_encontrado = "Notificação não encontrada."

    def do_usuario(self, usuario_id: int, pagina: int, por_pagina: int) -> Pagination:
        consulta = (
            select(Notificacao)
            .where(Notificacao.destinatario_id == usuario_id)
            .options(selectinload(Notificacao.remetente))
            .order_by(Notificacao.criado_em.desc(), Notificacao.id.desc())
        )
        return db.paginate(consulta, page=pagina, per_page=por_pagina, error_out=False)

    def contar_nao_lidas(self, usuario_id: int) -> int:
        return db.session.scalar(
            select(func.count()).where(
                Notificacao.destinatario_id == usuario_id,
                Notificacao.lida.is_(False),
            )
        ) or 0

    def marcar_todas_como_lidas(self, usuario_id: int) -> None:
        db.session.execute(
            update(Notificacao)
            .where(Notificacao.destinatario_id == usuario_id, Notificacao.lida.is_(False))
            .values(lida=True)
        )
