"""Curtidas e comentários (RF20–RF22, RN08–RN10)."""

from app.domain.excecoes import AcessoNegado, NaoEncontrado
from app.domain.notificacoes import GeradorNotificacoes
from app.extensions import db
from app.models import Comentario, Curtida, NotificacaoComentario, NotificacaoCurtida, Usuario
from app.services.notificacao_service import NotificacaoService
from app.services.polaroid_service import PolaroidService


class InteracaoService:
    def __init__(self) -> None:
        self.polaroids = PolaroidService()
        self.notificacoes = NotificacaoService()

    def alternar_curtida(self, usuario: Usuario, polaroid_id: int) -> tuple[bool, int]:
        """Curte ou descurte. Devolve (curtiu_agora, total_de_curtidas)."""
        polaroid = self.polaroids.obter_visivel(usuario, polaroid_id)
        curtida = db.session.get(Curtida, (usuario.id, polaroid.id))
        if curtida is not None:
            polaroid.curtidas.remove(curtida)
            curtiu = False
        else:
            polaroid.curtidas.append(Curtida(usuario=usuario, usuario_id=usuario.id))
            self.notificacoes.notificar(
                NotificacaoCurtida, usuario, polaroid.autor_id, polaroid
            )
            curtiu = True
        db.session.commit()
        return curtiu, len(polaroid.curtidas)

    def comentar(self, autor: Usuario, polaroid_id: int, texto: str) -> Comentario:
        polaroid = self.polaroids.obter_visivel(autor, polaroid_id)
        if not self.polaroids.pode_comentar(autor, polaroid):
            raise AcessoNegado("Você não pode comentar nesta memória.")  # RN08
        comentario = Comentario(autor=autor, autor_id=autor.id, texto=texto)
        polaroid.comentarios.append(comentario)
        db.session.flush()
        self.notificacoes.notificar(
            NotificacaoComentario, autor, polaroid.autor_id, polaroid, comentario
        )
        self.notificacoes.notificar_mencoes(autor, texto, polaroid, comentario)
        db.session.commit()
        return comentario

    def _obter_comentario(self, comentario_id: int) -> Comentario:
        comentario = db.session.get(Comentario, comentario_id)
        if comentario is None:
            raise NaoEncontrado("Comentário não encontrado.")
        return comentario

    def editar_comentario(self, editor: Usuario, comentario_id: int, texto: str) -> Comentario:
        comentario = self._obter_comentario(comentario_id)
        self.polaroids.obter_visivel(editor, comentario.polaroid_id)
        mencionados_antes = GeradorNotificacoes.extrair_mencoes(comentario.texto)
        comentario.editar(texto, editor)  # RN09: valida autor e tamanho
        self.notificacoes.notificar_mencoes(
            editor,
            comentario.texto,
            comentario.polaroid,
            comentario,
            ja_mencionados=mencionados_antes,
        )
        db.session.commit()
        return comentario

    def excluir_comentario(self, usuario: Usuario, comentario_id: int) -> int:
        """RN09: autor do comentário ou dono da Polaroid. Devolve a polaroid_id."""
        comentario = self._obter_comentario(comentario_id)
        if not comentario.pode_ser_excluido_por(usuario):
            raise AcessoNegado("Você não pode excluir este comentário.")
        polaroid_id = comentario.polaroid_id
        db.session.delete(comentario)
        db.session.commit()
        return polaroid_id
