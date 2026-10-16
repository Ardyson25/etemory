"""Regras de visibilidade das Polaroids (RN02, RN03, RN05).

Pilares de POO:
- Abstração: ``RegraVisibilidade`` diz O QUE toda regra responde
  (``pode_ver``), sem dizer COMO.
- Polimorfismo: cada subclasse responde do seu jeito, e quem usa a regra não
  precisa saber qual delas recebeu.
- Padrão Factory: ``FabricaRegraVisibilidade`` escolhe a regra pelo enum.
"""

from abc import ABC, abstractmethod

from app.domain.contexto import ContextoLeitor, PolaroidAcessivel
from app.domain.enums import Visibilidade


def resolver_visibilidade(
    escolhida: Visibilidade, conta_privada: bool
) -> Visibilidade:
    """RN03: Automática vira Pública (conta pública) ou Seguidores (privada)."""
    if escolhida is Visibilidade.AUTOMATICA:
        return Visibilidade.SEGUIDORES if conta_privada else Visibilidade.PUBLICA
    return escolhida


class RegraVisibilidade(ABC):
    """Contrato de toda regra de visibilidade."""

    @abstractmethod
    def pode_ver(
        self, leitor: ContextoLeitor, polaroid: PolaroidAcessivel
    ) -> bool:
        """Diz se o leitor pode ver a Polaroid por esta regra."""


class RegraPublica(RegraVisibilidade):
    """Qualquer usuário logado vê, mesmo com conta privada (RN02)."""

    def pode_ver(self, leitor: ContextoLeitor, polaroid: PolaroidAcessivel) -> bool:
        return True


class RegraSeguidores(RegraVisibilidade):
    """Autor + seguidores com vínculo aceito (RN02, RN05)."""

    def pode_ver(self, leitor: ContextoLeitor, polaroid: PolaroidAcessivel) -> bool:
        return leitor.eh_autor(polaroid.autor_id) or leitor.segue(polaroid.autor_id)


class RegraMelhoresAmigos(RegraVisibilidade):
    """Autor + quem ele marcou como melhor amigo (RN02, RN05)."""

    def pode_ver(self, leitor: ContextoLeitor, polaroid: PolaroidAcessivel) -> bool:
        return leitor.eh_autor(polaroid.autor_id) or leitor.eh_melhor_amigo_de(
            polaroid.autor_id
        )


class RegraSomenteEu(RegraVisibilidade):
    """Só o autor (RN02)."""

    def pode_ver(self, leitor: ContextoLeitor, polaroid: PolaroidAcessivel) -> bool:
        return leitor.eh_autor(polaroid.autor_id)


class FabricaRegraVisibilidade:
    """Escolhe a regra certa para cada valor do enum ``Visibilidade``."""

    _REGRAS: dict[Visibilidade, RegraVisibilidade] = {
        Visibilidade.PUBLICA: RegraPublica(),
        Visibilidade.SEGUIDORES: RegraSeguidores(),
        Visibilidade.MELHORES_AMIGOS: RegraMelhoresAmigos(),
        Visibilidade.SOMENTE_EU: RegraSomenteEu(),
    }

    @classmethod
    def obter(cls, visibilidade: Visibilidade) -> RegraVisibilidade:
        if visibilidade is Visibilidade.AUTOMATICA:
            raise ValueError(
                "Resolva a visibilidade AUTOMATICA antes (resolver_visibilidade)."
            )
        return cls._REGRAS[visibilidade]
