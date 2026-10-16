"""Regras de negócio das Polaroids (RF07–RF12, RF28–RF30).

Pilar de POO: responsabilidade única — a rota só entrega os dados do
formulário; aqui ficam as regras, e o modelo cuida das próprias transições.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import IO

from flask import current_app

from app.domain.enums import (
    Emocao,
    EstadoMemoria,
    ModoComentarios,
    StatusPolaroid,
    Visibilidade,
)
from app.domain.excecoes import AcessoNegado, NaoEncontrado
from app.domain.notificacoes import GeradorNotificacoes
from app.domain.politica_acesso import PoliticaAcesso
from app.extensions import db
from app.models import Midia, Polaroid, Usuario
from app.repositories import PolaroidRepository, UsuarioRepository, VinculoRepository
from app.services.midia_service import MidiaService
from app.services.notificacao_service import NotificacaoService


@dataclass
class DadosPolaroid:
    """Campos editáveis de uma Polaroid, já convertidos para tipos Python."""

    legenda: str
    data_memoria: date | None = None
    emocoes: list[Emocao] = field(default_factory=list)
    estado: EstadoMemoria = EstadoMemoria.PRESERVADA
    visibilidade: Visibilidade = Visibilidade.AUTOMATICA
    modo_comentarios: ModoComentarios = ModoComentarios.TODOS
    musica_titulo: str | None = None
    musica_artista: str | None = None
    musica_url: str | None = None
    local_nome: str | None = None


class PolaroidService:
    def __init__(self) -> None:
        self.repo = PolaroidRepository()
        self.vinculos = VinculoRepository()
        self.usuarios = UsuarioRepository()
        self.midias = MidiaService()
        self.notificacoes = NotificacaoService()
        self.politica = PoliticaAcesso()

    # ---------- Criação e edição ----------

    def publicar(self, autor: Usuario, dados: DadosPolaroid, foto: IO[bytes]) -> Polaroid:
        """Fluxo do diagrama de sequência 10.7 da V1."""
        imagem = self.midias.processar_upload(foto)
        try:
            polaroid = Polaroid(autor=autor, autor_id=autor.id, legenda=dados.legenda)
            self._aplicar(polaroid, dados)
            polaroid.midias.append(
                Midia(
                    caminho_arquivo=imagem.nome_arquivo,
                    ordem=0,
                    largura=imagem.largura,
                    altura=imagem.altura,
                )
            )
            self.repo.adicionar(polaroid)
            db.session.flush()  # gera o id usado nas notificações
            self.notificacoes.notificar_mencoes(autor, polaroid.legenda, polaroid)
            db.session.commit()
        except Exception:
            db.session.rollback()
            self.midias.apagar(imagem.nome_arquivo)  # nada de foto sem Polaroid
            raise
        return polaroid

    def editar(self, autor: Usuario, polaroid_id: int, dados: DadosPolaroid) -> Polaroid:
        polaroid = self.obter_do_autor(autor, polaroid_id)
        mencionados_antes = GeradorNotificacoes.extrair_mencoes(polaroid.legenda)
        self._aplicar(polaroid, dados)
        polaroid.marcar_como_editada()  # selo "Editado" (RF09)
        self.notificacoes.notificar_mencoes(
            autor, polaroid.legenda, polaroid, ja_mencionados=mencionados_antes
        )
        db.session.commit()
        return polaroid

    @staticmethod
    def _aplicar(polaroid: Polaroid, dados: DadosPolaroid) -> None:
        polaroid.legenda = dados.legenda
        polaroid.data_memoria = dados.data_memoria
        polaroid.definir_emocoes(dados.emocoes)
        polaroid.estado = dados.estado
        polaroid.visibilidade = dados.visibilidade
        polaroid.modo_comentarios = dados.modo_comentarios
        polaroid.musica_titulo = dados.musica_titulo
        polaroid.musica_artista = dados.musica_artista
        polaroid.musica_url = dados.musica_url
        polaroid.local_nome = dados.local_nome

    # ---------- Acesso ----------

    def obter_visivel(self, leitor: Usuario, polaroid_id: int) -> Polaroid:
        """404 se não existir OU se o leitor não puder ver (não revela que existe)."""
        polaroid = self.repo.obter(polaroid_id)
        if polaroid is None:
            raise NaoEncontrado("Memória não encontrada.")
        contexto = self.vinculos.contexto_do_leitor(leitor.id)
        if not self.politica.pode_ver(contexto, polaroid):
            raise NaoEncontrado("Memória não encontrada.")
        return polaroid

    def obter_do_autor(self, autor: Usuario, polaroid_id: int) -> Polaroid:
        polaroid = self.obter_visivel(autor, polaroid_id)
        if polaroid.autor_id != autor.id:
            raise AcessoNegado("Só o autor pode alterar esta memória.")
        return polaroid

    def verificar_acesso_midia(self, leitor: Usuario, nome_arquivo: str) -> None:
        """Foto de Polaroid segue a visibilidade dela; foto de perfil é livre."""
        midia = self.repo.midia_por_arquivo(nome_arquivo)
        if midia is not None:
            self.obter_visivel(leitor, midia.polaroid_id)
        elif not self.usuarios.imagem_de_perfil_existe(nome_arquivo):
            raise NaoEncontrado("Imagem não encontrada.")

    def pode_comentar(self, leitor: Usuario, polaroid: Polaroid) -> bool:
        contexto = self.vinculos.contexto_do_leitor(leitor.id)
        return self.politica.pode_comentar(contexto, polaroid)

    # ---------- Arquivo e Lixeira ----------

    def arquivar(self, autor: Usuario, polaroid_id: int) -> None:
        self.obter_do_autor(autor, polaroid_id).arquivar()
        db.session.commit()

    def desarquivar(self, autor: Usuario, polaroid_id: int) -> None:
        self.obter_do_autor(autor, polaroid_id).desarquivar()
        db.session.commit()

    def mover_para_lixeira(self, autor: Usuario, polaroid_id: int) -> None:
        self.obter_do_autor(autor, polaroid_id).mover_para_lixeira()
        db.session.commit()

    def restaurar(self, autor: Usuario, polaroid_id: int) -> None:
        self.obter_do_autor(autor, polaroid_id).restaurar()
        db.session.commit()

    def arquivadas(self, autor: Usuario) -> list[Polaroid]:
        return self.repo.do_autor_com_status(autor.id, StatusPolaroid.ARQUIVADA)

    def na_lixeira(self, autor: Usuario) -> list[Polaroid]:
        return self.repo.do_autor_com_status(autor.id, StatusPolaroid.LIXEIRA)

    def ativas_do_autor(self, autor: Usuario) -> list[Polaroid]:
        return self.repo.ativas_do_autor(autor.id)

    def limpar_lixeira_expirada(self, referencia: datetime | None = None) -> int:
        """RN14: apaga de vez, com comentários, curtidas e fotos."""
        expiradas = self.repo.expiradas_na_lixeira(referencia)
        arquivos = [m.caminho_arquivo for p in expiradas for m in p.midias]
        for polaroid in expiradas:
            self.repo.remover(polaroid)  # a composição apaga as partes
        db.session.commit()
        for nome in arquivos:  # só apaga o arquivo depois do commit
            self.midias.apagar(nome)
        current_app.logger.info("Lixeira: %d memória(s) apagada(s) de vez.", len(expiradas))
        return len(expiradas)
