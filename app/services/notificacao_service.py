"""Criação e leitura de notificações (RF23, RF24, RN15, RN16).

Este serviço não faz ``commit``: quem chama (outro serviço) confirma a
notificação junto com a ação que a gerou, numa transação só.
"""

from collections.abc import Iterable

from flask_sqlalchemy.pagination import Pagination

from app.domain.excecoes import NaoEncontrado
from app.domain.notificacoes import GeradorNotificacoes
from app.domain.politica_acesso import PoliticaAcesso
from app.extensions import db
from app.models import (
    Comentario,
    Notificacao,
    NotificacaoMencao,
    Polaroid,
    Usuario,
)
from app.repositories import (
    NotificacaoRepository,
    UsuarioRepository,
    VinculoRepository,
)


class NotificacaoService:
    def __init__(self) -> None:
        self.repo = NotificacaoRepository()
        self.usuarios = UsuarioRepository()
        self.vinculos = VinculoRepository()
        self.politica = PoliticaAcesso()

    def notificar(
        self,
        classe: type[Notificacao],
        remetente: Usuario,
        destinatario_id: int,
        polaroid: Polaroid | None = None,
        comentario: Comentario | None = None,
    ) -> Notificacao | None:
        """Cria a notificação do tipo ``classe`` (polimorfismo pela classe)."""
        if not GeradorNotificacoes.deve_notificar(remetente.id, destinatario_id):
            return None  # RN15
        notificacao = classe(
            remetente=remetente,
            destinatario_id=destinatario_id,
            polaroid=polaroid,
            comentario=comentario,
        )
        return self.repo.adicionar(notificacao)

    def notificar_mencoes(
        self,
        remetente: Usuario,
        texto: str,
        polaroid: Polaroid,
        comentario: Comentario | None = None,
        ja_mencionados: Iterable[str] = (),
    ) -> int:
        """RN16 + RC02: notifica quem existe e pode ver a Polaroid."""
        nomes = GeradorNotificacoes.extrair_mencoes(texto) - set(ja_mencionados)
        criadas = 0
        for usuario in self.usuarios.por_usernames(nomes):
            contexto = self.vinculos.contexto_do_leitor(usuario.id)
            if not self.politica.pode_ver(contexto, polaroid):
                continue
            if self.notificar(NotificacaoMencao, remetente, usuario.id, polaroid, comentario):
                criadas += 1
        return criadas

    # ---------- Leitura ----------

    def listar(self, usuario: Usuario, pagina: int, por_pagina: int = 30) -> Pagination:
        return self.repo.do_usuario(usuario.id, pagina, por_pagina)

    def contar_nao_lidas(self, usuario: Usuario) -> int:
        return self.repo.contar_nao_lidas(usuario.id)

    def abrir(self, usuario: Usuario, notificacao_id: int) -> str:
        """Marca como lida e devolve o link de destino."""
        notificacao = self.repo.obter(notificacao_id)
        if notificacao is None or notificacao.destinatario_id != usuario.id:
            raise NaoEncontrado("Notificação não encontrada.")
        notificacao.marcar_como_lida()
        link = notificacao.link()
        db.session.commit()
        return link

    def marcar_todas_como_lidas(self, usuario: Usuario) -> None:
        self.repo.marcar_todas_como_lidas(usuario.id)
        db.session.commit()
