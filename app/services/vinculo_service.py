"""Seguir, solicitações e melhores amigos (RF13–RF16, RN05–RN07, RN15)."""

from enum import Enum

from app.domain.contexto import ContextoLeitor
from app.domain.enums import StatusVinculo
from app.domain.excecoes import AcessoNegado, ErroDeNegocio
from app.extensions import db
from app.models import (
    NotificacaoSeguidor,
    NotificacaoSolicitacao,
    NotificacaoSolicitacaoAceita,
    Usuario,
    Vinculo,
)
from app.repositories import VinculoRepository
from app.services.notificacao_service import NotificacaoService


class EstadoRelacao(Enum):
    """Como o leitor se relaciona com um perfil (define o botão na tela)."""

    PROPRIO = "proprio"
    SEGUINDO = "seguindo"
    PENDENTE = "pendente"
    NENHUM = "nenhum"


class VinculoService:
    def __init__(self) -> None:
        self.repo = VinculoRepository()
        self.notificacoes = NotificacaoService()

    def contexto(self, usuario: Usuario) -> ContextoLeitor:
        return self.repo.contexto_do_leitor(usuario.id)

    def estado_relacao(self, leitor: Usuario, alvo: Usuario) -> EstadoRelacao:
        if leitor.id == alvo.id:
            return EstadoRelacao.PROPRIO
        vinculo = self.repo.obter_entre(leitor.id, alvo.id)
        if vinculo is None:
            return EstadoRelacao.NENHUM
        if vinculo.esta_ativo:
            return EstadoRelacao.SEGUINDO
        if vinculo.esta_pendente:
            return EstadoRelacao.PENDENTE
        return EstadoRelacao.NENHUM

    def seguir(self, seguidor: Usuario, seguido: Usuario) -> Vinculo:
        """RN07: conta pública é seguida na hora; privada gera solicitação."""
        if seguidor.id == seguido.id:
            raise ErroDeNegocio("Você não pode seguir a si mesmo.")  # RN15
        vinculo = self.repo.obter_entre(seguidor.id, seguido.id)
        if vinculo is not None and (vinculo.esta_ativo or vinculo.esta_pendente):
            return vinculo  # clicar duas vezes não cria nada novo
        if vinculo is None:
            vinculo = self.repo.adicionar(Vinculo.criar(seguidor, seguido))
        else:
            vinculo.reabrir(seguido.conta_privada)  # RC06

        classe = NotificacaoSeguidor if vinculo.esta_ativo else NotificacaoSolicitacao
        self.notificacoes.notificar(classe, seguidor, seguido.id)
        db.session.commit()
        return vinculo

    def deixar_de_seguir(self, seguidor: Usuario, seguido: Usuario) -> None:
        """RN05/RN06: apagar o vínculo tira o acesso e o "melhor amigo" na hora."""
        vinculo = self.repo.obter_entre(seguidor.id, seguido.id)
        if vinculo is None:
            return
        if vinculo.esta_pendente:
            vinculo.cancelar()
        else:
            self.repo.remover(vinculo)
        db.session.commit()

    def cancelar_solicitacao(self, seguidor: Usuario, seguido: Usuario) -> None:
        vinculo = self.repo.obter_entre(seguidor.id, seguido.id)
        if vinculo is None or not vinculo.esta_pendente:
            raise ErroDeNegocio("Não há solicitação pendente para cancelar.")
        vinculo.cancelar()
        db.session.commit()

    def responder(self, dono: Usuario, vinculo_id: int, aceitar: bool) -> Vinculo:
        """Só o dono da conta privada aceita ou recusa (RN07)."""
        vinculo = self.repo.obter_ou_erro(vinculo_id)
        if vinculo.seguido_id != dono.id:
            raise AcessoNegado("Esta solicitação não é para você.")
        if aceitar:
            vinculo.aceitar()
            self.notificacoes.notificar(
                NotificacaoSolicitacaoAceita, dono, vinculo.seguidor_id
            )
        else:
            vinculo.recusar()
        db.session.commit()
        return vinculo

    def aceitar_pendentes(self, dono: Usuario) -> int:
        """RC04: ao virar conta pública, as solicitações pendentes são aceitas."""
        pendentes = self.repo.pendentes_para(dono.id)
        for vinculo in pendentes:
            vinculo.aceitar()
            self.notificacoes.notificar(
                NotificacaoSolicitacaoAceita, dono, vinculo.seguidor_id
            )
        return len(pendentes)

    def alternar_melhor_amigo(self, dono: Usuario, seguidor_id: int) -> bool:
        """RN06: só seguidor aceito vira melhor amigo. Devolve o novo estado."""
        vinculo = self.repo.obter_entre(seguidor_id, dono.id)
        if vinculo is None or vinculo.status is not StatusVinculo.ACEITO:
            raise ErroDeNegocio("Só seguidores podem ser melhores amigos.")
        if vinculo.melhor_amigo:
            vinculo.desmarcar_melhor_amigo()
        else:
            vinculo.marcar_melhor_amigo()
        db.session.commit()
        return vinculo.melhor_amigo

    # ---------- Listas ----------

    def seguidores(self, usuario: Usuario) -> list[Usuario]:
        return self.repo.seguidores_de(usuario.id)

    def seguindo(self, usuario: Usuario) -> list[Usuario]:
        return self.repo.seguindo_de(usuario.id)

    def solicitacoes_pendentes(self, dono: Usuario) -> list[Vinculo]:
        return self.repo.pendentes_para(dono.id)

    def vinculos_de_seguidores(self, dono: Usuario) -> list[Vinculo]:
        return self.repo.aceitos_para(dono.id)

    def contadores(self, usuario: Usuario) -> dict[str, int]:
        return {
            "seguidores": self.repo.contar_seguidores(usuario.id),
            "seguindo": self.repo.contar_seguindo(usuario.id),
        }
