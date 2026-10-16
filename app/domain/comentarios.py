"""Regras de quem pode comentar numa Polaroid (RN08).

Mesmo padrão das regras de visibilidade: classe abstrata + subclasses
polimórficas + fábrica. Estas regras só são consultadas depois de confirmar
que o leitor pode ver a Polaroid (ver ``PoliticaAcesso``).

Pilares de POO: abstração, polimorfismo e padrão Factory.
"""

from abc import ABC, abstractmethod

from app.domain.contexto import ContextoLeitor, PolaroidAcessivel
from app.domain.enums import ModoComentarios


class RegraComentario(ABC):
    """Contrato de toda regra de comentário."""

    @abstractmethod
    def pode_comentar(
        self, leitor: ContextoLeitor, polaroid: PolaroidAcessivel
    ) -> bool:
        """Diz se o leitor pode comentar por esta regra."""


class RegraComentarTodos(RegraComentario):
    """Todos que podem ver a Polaroid podem comentar."""

    def pode_comentar(self, leitor: ContextoLeitor, polaroid: PolaroidAcessivel) -> bool:
        return True


class RegraComentarSeguidores(RegraComentario):
    def pode_comentar(self, leitor: ContextoLeitor, polaroid: PolaroidAcessivel) -> bool:
        return leitor.eh_autor(polaroid.autor_id) or leitor.segue(polaroid.autor_id)


class RegraComentarMelhoresAmigos(RegraComentario):
    def pode_comentar(self, leitor: ContextoLeitor, polaroid: PolaroidAcessivel) -> bool:
        return leitor.eh_autor(polaroid.autor_id) or leitor.eh_melhor_amigo_de(
            polaroid.autor_id
        )


class RegraComentarNinguem(RegraComentario):
    """Ninguém comenta, exceto o autor (RN08: o autor sempre pode)."""

    def pode_comentar(self, leitor: ContextoLeitor, polaroid: PolaroidAcessivel) -> bool:
        return leitor.eh_autor(polaroid.autor_id)


class FabricaRegraComentario:
    _REGRAS: dict[ModoComentarios, RegraComentario] = {
        ModoComentarios.TODOS: RegraComentarTodos(),
        ModoComentarios.SEGUIDORES: RegraComentarSeguidores(),
        ModoComentarios.MELHORES_AMIGOS: RegraComentarMelhoresAmigos(),
        ModoComentarios.NINGUEM: RegraComentarNinguem(),
    }

    @classmethod
    def obter(cls, modo: ModoComentarios) -> RegraComentario:
        return cls._REGRAS[modo]
