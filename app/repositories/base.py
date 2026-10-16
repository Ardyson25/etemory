"""Repositório genérico.

Pilar de POO: herança — cada repositório concreto herda ``obter``,
``adicionar`` e ``remover`` e só escreve as consultas próprias.
"""

from typing import Any, Generic, TypeVar

from app.domain.excecoes import NaoEncontrado
from app.extensions import db

T = TypeVar("T")


class RepositorioBase(Generic[T]):
    modelo: type[T]
    mensagem_nao_encontrado: str = "Registro não encontrado."

    def obter(self, id_: Any) -> T | None:
        return db.session.get(self.modelo, id_)

    def obter_ou_erro(self, id_: Any) -> T:
        objeto = self.obter(id_)
        if objeto is None:
            raise NaoEncontrado(self.mensagem_nao_encontrado)
        return objeto

    def adicionar(self, objeto: T) -> T:
        db.session.add(objeto)
        return objeto

    def remover(self, objeto: T) -> None:
        db.session.delete(objeto)
