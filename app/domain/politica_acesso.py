"""Ponto único de decisão sobre ver e comentar Polaroids.

Ordem das verificações em ``pode_ver``:
1. O autor sempre vê as próprias Polaroids (RN01).
2. Arquivada ou na Lixeira só aparece para o autor (RN04).
3. Resolve a visibilidade Automática (RN03).
4. Delega para a regra concreta (RN02, RN05) — aqui está o polimorfismo:
   a política não sabe qual regra recebeu.

Pilar de POO: responsabilidade única — esta classe só decide acesso.
"""

from app.domain.comentarios import FabricaRegraComentario
from app.domain.contexto import ContextoLeitor, PolaroidAcessivel
from app.domain.enums import StatusPolaroid
from app.domain.visibilidade import FabricaRegraVisibilidade


class PoliticaAcesso:
    def pode_ver(self, leitor: ContextoLeitor, polaroid: PolaroidAcessivel) -> bool:
        if leitor.eh_autor(polaroid.autor_id):
            return True
        if polaroid.status is not StatusPolaroid.ATIVA:
            return False
        regra = FabricaRegraVisibilidade.obter(polaroid.visibilidade_efetiva)
        return regra.pode_ver(leitor, polaroid)

    def pode_comentar(
        self, leitor: ContextoLeitor, polaroid: PolaroidAcessivel
    ) -> bool:
        """RN08: precisa poder ver e respeitar o modo de comentários."""
        if polaroid.status is not StatusPolaroid.ATIVA:
            return False
        if not self.pode_ver(leitor, polaroid):
            return False
        regra = FabricaRegraComentario.obter(polaroid.modo_comentarios)
        return regra.pode_comentar(leitor, polaroid)
