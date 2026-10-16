"""Edição de perfil e configurações (RF03, RF04, RF06)."""

from typing import IO

from app.domain.enums import ModoComentarios
from app.domain.excecoes import ErroDeNegocio
from app.extensions import db
from app.models import Usuario
from app.services.midia_service import MidiaService
from app.services.vinculo_service import VinculoService


class UsuarioService:
    def __init__(self) -> None:
        self.midias = MidiaService()
        self.vinculos = VinculoService()

    def atualizar_perfil(
        self,
        usuario: Usuario,
        nome: str,
        bio: str | None,
        site: str | None,
        foto: IO[bytes] | None = None,
        capa: IO[bytes] | None = None,
    ) -> Usuario:
        novos: list[str] = []
        antigos: list[str | None] = []
        try:
            usuario.nome = nome
            usuario.bio = bio or ""
            usuario.site = site
            if foto is not None:
                salva = self.midias.processar_upload(foto)
                novos.append(salva.nome_arquivo)
                antigos.append(usuario.foto)
                usuario.foto = salva.nome_arquivo
            if capa is not None:
                salva = self.midias.processar_upload(capa)
                novos.append(salva.nome_arquivo)
                antigos.append(usuario.capa)
                usuario.capa = salva.nome_arquivo
            db.session.commit()
        except Exception:
            db.session.rollback()
            for nome_arquivo in novos:  # não deixa arquivo órfão
                self.midias.apagar(nome_arquivo)
            raise
        for nome_arquivo in antigos:
            self.midias.apagar(nome_arquivo)
        return usuario

    def configurar(
        self,
        usuario: Usuario,
        conta_privada: bool,
        modo_comentarios_padrao: ModoComentarios,
    ) -> None:
        ficou_publica = usuario.conta_privada and not conta_privada
        usuario.conta_privada = conta_privada
        usuario.modo_comentarios_padrao = modo_comentarios_padrao
        if ficou_publica:
            self.vinculos.aceitar_pendentes(usuario)  # RC04
        db.session.commit()

    def alterar_senha(self, usuario: Usuario, senha_atual: str, nova_senha: str) -> None:
        if not usuario.verificar_senha(senha_atual):
            raise ErroDeNegocio("A senha atual está incorreta.")
        usuario.definir_senha(nova_senha)
        db.session.commit()
