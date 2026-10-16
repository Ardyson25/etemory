"""Regras puras sobre notificações (RN15, RN16).

A criação dos objetos ``Notificacao`` fica no ``NotificacaoService``; aqui
ficam só as decisões, testáveis sem banco.
"""

import re

from app.domain.validacoes import PADRAO_USERNAME

# @ que não vem colado em letra, número ou ponto (evita pegar e-mails).
PADRAO_MENCAO = re.compile(r"(?<![\w.@])@([A-Za-z0-9._]{3,24})")


class GeradorNotificacoes:
    @staticmethod
    def extrair_mencoes(texto: str | None) -> set[str]:
        """RN16: devolve os @usernames citados no texto, sem o @."""
        encontrados: set[str] = set()
        for bruto in PADRAO_MENCAO.findall(texto or ""):
            # Ponto no fim é pontuação da frase: "obrigado, @ana."
            username = bruto.lower().rstrip(".")
            if PADRAO_USERNAME.fullmatch(username):
                encontrados.add(username)
        return encontrados

    @staticmethod
    def deve_notificar(remetente_id: int, destinatario_id: int) -> bool:
        """RN15: ninguém recebe notificação das próprias ações."""
        return remetente_id != destinatario_id
