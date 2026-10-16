"""Exceções de negócio.

Os serviços lançam estas exceções e o ``create_app`` as transforma em
resposta HTTP (mensagem na tela, 403 ou 404).

Pilar de POO: herança — todas derivam de ``ErroDeNegocio``, então um único
``except ErroDeNegocio`` trata qualquer violação de regra.
"""


class ErroDeNegocio(Exception):
    """Violação de uma regra de negócio. A mensagem é mostrada ao usuário."""

    codigo_http: int = 400


class TransicaoInvalida(ErroDeNegocio):
    """Mudança de estado não permitida (ex.: restaurar Polaroid ativa)."""


class AcessoNegado(ErroDeNegocio):
    """O usuário está logado, mas não pode fazer esta ação."""

    codigo_http = 403


class NaoEncontrado(ErroDeNegocio):
    """O recurso não existe ou o usuário não pode saber que ele existe."""

    codigo_http = 404
