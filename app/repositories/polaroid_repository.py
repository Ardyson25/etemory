"""Consultas de Polaroids.

``filtro_visivel`` traduz para SQL as mesmas regras de ``PoliticaAcesso``
(RN01–RN05). Assim a timeline filtra no banco, sem carregar tudo para o
Python. O teste ``tests/integration/test_timeline.py`` compara os dois
caminhos para garantir que nunca divergem (risco R02 da V1).
"""

from datetime import datetime, timedelta

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import ColumnElement, and_, false, or_, select
from sqlalchemy.orm import selectinload

from app.domain.contexto import ContextoLeitor
from app.domain.enums import StatusPolaroid, Visibilidade
from app.domain.tempo import agora
from app.domain.validacoes import DIAS_NA_LIXEIRA
from app.extensions import db
from app.models import Midia, Polaroid, Usuario
from app.repositories.base import RepositorioBase


class PolaroidRepository(RepositorioBase[Polaroid]):
    modelo = Polaroid
    mensagem_nao_encontrado = "Memória não encontrada."

    @staticmethod
    def filtro_visivel(contexto: ContextoLeitor) -> ColumnElement[bool]:
        """Polaroids ATIVAS que o leitor pode ver (exige join com Usuario)."""
        conta_privada = Usuario.conta_privada
        automatica = Polaroid.visibilidade == Visibilidade.AUTOMATICA

        publica = or_(
            Polaroid.visibilidade == Visibilidade.PUBLICA,
            and_(automatica, conta_privada.is_(False)),
        )
        para_seguidores = and_(
            or_(
                Polaroid.visibilidade == Visibilidade.SEGUIDORES,
                and_(automatica, conta_privada.is_(True)),
            ),
            Polaroid.autor_id.in_(contexto.seguindo_ids)
            if contexto.seguindo_ids
            else false(),
        )
        para_melhores_amigos = and_(
            Polaroid.visibilidade == Visibilidade.MELHORES_AMIGOS,
            Polaroid.autor_id.in_(contexto.melhor_amigo_de_ids)
            if contexto.melhor_amigo_de_ids
            else false(),
        )
        return and_(
            Polaroid.status == StatusPolaroid.ATIVA,
            or_(
                Polaroid.autor_id == contexto.usuario_id,
                publica,
                para_seguidores,
                para_melhores_amigos,
            ),
        )

    @staticmethod
    def _consulta_base():  # type: ignore[no-untyped-def]
        return (
            select(Polaroid)
            .join(Polaroid.autor)
            .options(
                selectinload(Polaroid.autor),
                selectinload(Polaroid.midias),
                selectinload(Polaroid._emocoes),
                selectinload(Polaroid.curtidas),
                selectinload(Polaroid.comentarios),
            )
            .order_by(Polaroid.criado_em.desc(), Polaroid.id.desc())
        )

    def _paginar(self, consulta, pagina: int, por_pagina: int) -> Pagination:  # type: ignore[no-untyped-def]
        return db.paginate(
            consulta, page=pagina, per_page=por_pagina, error_out=False, count=True
        )

    def visiveis(
        self, contexto: ContextoLeitor, pagina: int, por_pagina: int
    ) -> Pagination:
        """Aba "Para você" (RF17)."""
        consulta = self._consulta_base().where(self.filtro_visivel(contexto))
        return self._paginar(consulta, pagina, por_pagina)

    def de_vinculos(
        self, contexto: ContextoLeitor, pagina: int, por_pagina: int
    ) -> Pagination:
        """Aba "Vínculos" (RF18): de quem o leitor segue, e as dele."""
        autores = set(contexto.seguindo_ids) | {contexto.usuario_id}
        consulta = self._consulta_base().where(
            self.filtro_visivel(contexto), Polaroid.autor_id.in_(autores)
        )
        return self._paginar(consulta, pagina, por_pagina)

    def do_perfil(
        self, contexto: ContextoLeitor, autor_id: int, pagina: int, por_pagina: int
    ) -> Pagination:
        consulta = self._consulta_base().where(
            self.filtro_visivel(contexto), Polaroid.autor_id == autor_id
        )
        return self._paginar(consulta, pagina, por_pagina)

    def do_autor_com_status(
        self, autor_id: int, status: StatusPolaroid
    ) -> list[Polaroid]:
        """Arquivo Pessoal e Lixeira (só o autor chega aqui)."""
        ordem = (
            Polaroid.excluida_em.desc()
            if status is StatusPolaroid.LIXEIRA
            else Polaroid.arquivada_em.desc()
        )
        consulta = (
            select(Polaroid)
            .where(Polaroid.autor_id == autor_id, Polaroid.status == status)
            .options(selectinload(Polaroid.midias))
            .order_by(ordem)
        )
        return list(db.session.scalars(consulta))

    def ativas_do_autor(self, autor_id: int) -> list[Polaroid]:
        consulta = (
            select(Polaroid)
            .where(
                Polaroid.autor_id == autor_id,
                Polaroid.status == StatusPolaroid.ATIVA,
            )
            .order_by(Polaroid.criado_em.desc())
        )
        return list(db.session.scalars(consulta))

    def midia_por_arquivo(self, nome_arquivo: str) -> Midia | None:
        return db.session.scalar(select(Midia).where(Midia.caminho_arquivo == nome_arquivo))

    def expiradas_na_lixeira(self, referencia: datetime | None = None) -> list[Polaroid]:
        """RN14: na Lixeira há 30 dias ou mais."""
        limite = (referencia or agora()) - timedelta(days=DIAS_NA_LIXEIRA)
        consulta = select(Polaroid).where(
            Polaroid.status == StatusPolaroid.LIXEIRA, Polaroid.excluida_em <= limite
        )
        return list(db.session.scalars(consulta))
