"""Timelines "Para você", "Vínculos" e grade do Prontuário (RF05, RF17–RF19)."""

from flask import current_app
from flask_sqlalchemy.pagination import Pagination

from app.models import Usuario
from app.repositories import PolaroidRepository, VinculoRepository


class TimelineService:
    def __init__(self) -> None:
        self.polaroids = PolaroidRepository()
        self.vinculos = VinculoRepository()
        self.por_pagina: int = current_app.config["POLAROIDS_POR_PAGINA"]

    def para_voce(self, leitor: Usuario, pagina: int = 1) -> Pagination:
        contexto = self.vinculos.contexto_do_leitor(leitor.id)
        return self.polaroids.visiveis(contexto, pagina, self.por_pagina)

    def de_vinculos(self, leitor: Usuario, pagina: int = 1) -> Pagination:
        contexto = self.vinculos.contexto_do_leitor(leitor.id)
        return self.polaroids.de_vinculos(contexto, pagina, self.por_pagina)

    def do_perfil(self, leitor: Usuario, autor: Usuario, pagina: int = 1) -> Pagination:
        contexto = self.vinculos.contexto_do_leitor(leitor.id)
        return self.polaroids.do_perfil(contexto, autor.id, pagina, self.por_pagina)
