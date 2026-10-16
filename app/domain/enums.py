"""Enums do domínio do Etermory.

O nome do membro (ex.: ``PUBLICA``) é o que vai para o banco; o valor
(ex.: ``"Pública"``) é o rótulo mostrado na tela.

Pilar de POO: abstração — cada enum dá um nome fixo a um conceito do
negócio e impede valores soltos como a string "publica" espalhada no código.
"""

from enum import Enum


class EnumRotulado(Enum):
    """Base dos enums com rótulo para a interface."""

    @property
    def rotulo(self) -> str:
        return str(self.value)

    @classmethod
    def opcoes(cls) -> list[tuple[str, str]]:
        """Pares (nome, rótulo) usados nos campos de formulário."""
        return [(membro.name, membro.rotulo) for membro in cls]


class Emocao(EnumRotulado):
    FELICIDADE = "Felicidade"
    SAUDADE = "Saudade"
    AMOR = "Amor"
    CORACAO_PARTIDO = "Coração partido"
    SUPERACAO = "Superação"
    RECOMECO = "Recomeço"
    TRISTEZA = "Tristeza"
    ACOLHIMENTO = "Acolhimento"
    GRATIDAO = "Gratidão"
    CONQUISTA = "Conquista"
    MELANCOLIA = "Melancolia"
    NOSTALGIA = "Nostalgia"
    DESPEDIDA = "Despedida"
    LIBERDADE = "Liberdade"
    ESPERANCA = "Esperança"
    PAZ = "Paz"
    ORGULHO = "Orgulho"
    AMIZADE = "Amizade"
    CONFUSAO = "Confusão"
    MUDANCA = "Mudança"


class EstadoMemoria(EnumRotulado):
    PRESERVADA = "Preservada"
    SENSIVEL = "Sensível"
    FRAGMENTADA = "Fragmentada"
    REVISITADA = "Revisitada"


class Visibilidade(EnumRotulado):
    # AUTOMATICA é resolvida na leitura (RN03); as regras nunca a recebem.
    AUTOMATICA = "Automática"
    PUBLICA = "Pública"
    SEGUIDORES = "Seguidores"
    MELHORES_AMIGOS = "Melhores amigos"
    SOMENTE_EU = "Só eu"


class ModoComentarios(EnumRotulado):
    TODOS = "Todos que podem ver"
    SEGUIDORES = "Seguidores"
    MELHORES_AMIGOS = "Melhores amigos"
    NINGUEM = "Ninguém"


class StatusVinculo(EnumRotulado):
    PENDENTE = "Pendente"
    ACEITO = "Aceito"
    RECUSADO = "Recusado"
    CANCELADO = "Cancelado"


class StatusPolaroid(EnumRotulado):
    ATIVA = "Ativa"
    ARQUIVADA = "Arquivada"
    LIXEIRA = "Lixeira"


class TipoNotificacao(EnumRotulado):
    """Valores gravados na coluna ``tipo`` (herança de tabela única)."""

    CURTIDA = "curtida"
    COMENTARIO = "comentario"
    SEGUIDOR = "seguidor"
    SOLICITACAO = "solicitacao"
    SOLICITACAO_ACEITA = "solicitacao_aceita"
    MENCAO = "mencao"
