"""Consultas de vínculos e montagem do ``ContextoLeitor``."""

from sqlalchemy import func, select

from app.domain.contexto import ContextoLeitor
from app.domain.enums import StatusVinculo
from app.extensions import db
from app.models import Usuario, Vinculo
from app.repositories.base import RepositorioBase


class VinculoRepository(RepositorioBase[Vinculo]):
    modelo = Vinculo
    mensagem_nao_encontrado = "Vínculo não encontrado."

    def obter_entre(self, seguidor_id: int, seguido_id: int) -> Vinculo | None:
        return db.session.scalar(
            select(Vinculo).where(
                Vinculo.seguidor_id == seguidor_id, Vinculo.seguido_id == seguido_id
            )
        )

    def contexto_do_leitor(self, usuario_id: int) -> ContextoLeitor:
        """Carrega, numa consulta, quem o leitor segue e onde é melhor amigo."""
        linhas = db.session.execute(
            select(Vinculo.seguido_id, Vinculo.melhor_amigo).where(
                Vinculo.seguidor_id == usuario_id,
                Vinculo.status == StatusVinculo.ACEITO,
            )
        ).all()
        return ContextoLeitor(
            usuario_id=usuario_id,
            seguindo_ids=frozenset(seguido for seguido, _ in linhas),
            melhor_amigo_de_ids=frozenset(seguido for seguido, melhor in linhas if melhor),
        )

    def seguidores_de(self, usuario_id: int) -> list[Usuario]:
        return list(
            db.session.scalars(
                select(Usuario)
                .join(Vinculo, Vinculo.seguidor_id == Usuario.id)
                .where(
                    Vinculo.seguido_id == usuario_id,
                    Vinculo.status == StatusVinculo.ACEITO,
                )
                .order_by(Usuario.nome)
            )
        )

    def seguindo_de(self, usuario_id: int) -> list[Usuario]:
        return list(
            db.session.scalars(
                select(Usuario)
                .join(Vinculo, Vinculo.seguido_id == Usuario.id)
                .where(
                    Vinculo.seguidor_id == usuario_id,
                    Vinculo.status == StatusVinculo.ACEITO,
                )
                .order_by(Usuario.nome)
            )
        )

    def aceitos_para(self, usuario_id: int) -> list[Vinculo]:
        """Vínculos de quem segue o usuário (para gerir melhores amigos)."""
        return list(
            db.session.scalars(
                select(Vinculo)
                .where(
                    Vinculo.seguido_id == usuario_id,
                    Vinculo.status == StatusVinculo.ACEITO,
                )
                .order_by(Vinculo.melhor_amigo.desc(), Vinculo.criado_em.desc())
            )
        )

    def pendentes_para(self, usuario_id: int) -> list[Vinculo]:
        return list(
            db.session.scalars(
                select(Vinculo)
                .where(
                    Vinculo.seguido_id == usuario_id,
                    Vinculo.status == StatusVinculo.PENDENTE,
                )
                .order_by(Vinculo.criado_em.desc())
            )
        )

    def contar_seguidores(self, usuario_id: int) -> int:
        return db.session.scalar(
            select(func.count()).where(
                Vinculo.seguido_id == usuario_id, Vinculo.status == StatusVinculo.ACEITO
            )
        ) or 0

    def contar_seguindo(self, usuario_id: int) -> int:
        return db.session.scalar(
            select(func.count()).where(
                Vinculo.seguidor_id == usuario_id,
                Vinculo.status == StatusVinculo.ACEITO,
            )
        ) or 0
