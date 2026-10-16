"""Álbuns (RF25–RF27, RN13, RC01, RC03)."""

from app.domain.enums import StatusPolaroid, Visibilidade
from app.domain.excecoes import AcessoNegado, NaoEncontrado
from app.domain.politica_acesso import PoliticaAcesso
from app.extensions import db
from app.models import Album, Polaroid, Usuario
from app.repositories import AlbumRepository, VinculoRepository
from app.services.polaroid_service import PolaroidService


class AlbumService:
    def __init__(self) -> None:
        self.repo = AlbumRepository()
        self.vinculos = VinculoRepository()
        self.polaroids = PolaroidService()
        self.politica = PoliticaAcesso()

    def criar(self, dono: Usuario, titulo: str, descricao: str, publico: bool) -> Album:
        album = Album(
            dono=dono,
            dono_id=dono.id,
            titulo=titulo,
            descricao=descricao,
            visibilidade=Visibilidade.PUBLICA if publico else Visibilidade.SOMENTE_EU,
        )
        self.repo.adicionar(album)
        db.session.commit()
        return album

    def editar(
        self, dono: Usuario, album_id: int, titulo: str, descricao: str, publico: bool
    ) -> Album:
        album = self.obter_do_dono(dono, album_id)
        album.titulo = titulo
        album.descricao = descricao
        album.visibilidade = Visibilidade.PUBLICA if publico else Visibilidade.SOMENTE_EU
        db.session.commit()
        return album

    def obter_visivel(self, leitor: Usuario, album_id: int) -> Album:
        album = self.repo.obter(album_id)
        if album is None or (not album.eh_publico and album.dono_id != leitor.id):
            raise NaoEncontrado("Álbum não encontrado.")
        return album

    def obter_do_dono(self, dono: Usuario, album_id: int) -> Album:
        album = self.obter_visivel(dono, album_id)
        if album.dono_id != dono.id:
            raise AcessoNegado("Só o dono pode alterar este álbum.")
        return album

    def polaroids_visiveis(self, leitor: Usuario, album: Album) -> list[Polaroid]:
        """RC01: o álbum só mostra o que o leitor pode ver."""
        contexto = self.vinculos.contexto_do_leitor(leitor.id)
        return [
            p
            for p in album.polaroids
            # Arquivadas e na Lixeira saem do álbum até para o dono.
            if p.status is StatusPolaroid.ATIVA and self.politica.pode_ver(contexto, p)
        ]

    def do_usuario(self, leitor: Usuario, dono: Usuario) -> list[Album]:
        return self.repo.do_dono(dono.id, incluir_privados=leitor.id == dono.id)

    def adicionar(self, dono: Usuario, album_id: int, polaroid_id: int) -> None:
        album = self.obter_do_dono(dono, album_id)
        polaroid = self.polaroids.obter_do_autor(dono, polaroid_id)
        album.adicionar(polaroid)  # RC03 validado no modelo
        db.session.commit()

    def remover(self, dono: Usuario, album_id: int, polaroid_id: int) -> None:
        album = self.obter_do_dono(dono, album_id)
        polaroid = self.polaroids.obter_do_autor(dono, polaroid_id)
        album.remover(polaroid)
        db.session.commit()

    def excluir(self, dono: Usuario, album_id: int) -> None:
        """RN13: as Polaroids continuam existindo (agregação)."""
        self.repo.remover(self.obter_do_dono(dono, album_id))
        db.session.commit()
