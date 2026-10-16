"""Dados que as regras de acesso precisam, sem depender do banco.

``ContextoLeitor`` é montado pelo ``VinculoRepository`` antes de chamar as
regras. ``PolaroidAcessivel`` descreve o mínimo que uma Polaroid precisa ter
para ser avaliada: o modelo SQLAlchemy cumpre esse contrato e os testes
unitários usam uma classe simples no lugar dele.
"""

from dataclasses import dataclass, field
from typing import Protocol

from app.domain.enums import ModoComentarios, StatusPolaroid, Visibilidade


@dataclass(frozen=True)
class ContextoLeitor:
    """Quem está lendo e quais vínculos aceitos ele tem.

    Pilar de POO: encapsulamento — os conjuntos são imutáveis (frozenset) e
    as perguntas são feitas por métodos, não olhando os conjuntos direto.
    """

    usuario_id: int
    # Autores que o leitor segue com vínculo ACEITO.
    seguindo_ids: frozenset[int] = field(default_factory=frozenset)
    # Autores que marcaram o leitor como melhor amigo.
    melhor_amigo_de_ids: frozenset[int] = field(default_factory=frozenset)

    def eh_autor(self, autor_id: int) -> bool:
        return self.usuario_id == autor_id

    def segue(self, autor_id: int) -> bool:
        return autor_id in self.seguindo_ids

    def eh_melhor_amigo_de(self, autor_id: int) -> bool:
        return autor_id in self.melhor_amigo_de_ids


class PolaroidAcessivel(Protocol):
    """Contrato mínimo de uma Polaroid para as regras de acesso."""

    autor_id: int

    @property
    def status(self) -> StatusPolaroid: ...

    @property
    def visibilidade_efetiva(self) -> Visibilidade: ...

    @property
    def modo_comentarios(self) -> ModoComentarios: ...
