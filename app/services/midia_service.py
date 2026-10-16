"""Validação, redimensionamento e gravação de imagens com Pillow (RN18).

A validação é feita pelo CONTEÚDO do arquivo (Pillow abre e confere o
formato), não pela extensão, que o usuário pode trocar à vontade.

Onde o arquivo fica guardado é decidido pelo ``Armazenamento`` (disco ou
banco): este serviço não sabe e não precisa saber (polimorfismo).
"""

from dataclasses import dataclass
from io import BytesIO
from typing import IO
from uuid import uuid4

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

from app.domain.excecoes import ErroDeNegocio
from app.services.armazenamento import Armazenamento, criar_armazenamento, validar_nome_arquivo

FORMATOS_ACEITOS = {"JPEG", "PNG", "WEBP"}
TIPO_SAIDA = "image/webp"


@dataclass(frozen=True)
class ImagemSalva:
    nome_arquivo: str
    largura: int
    altura: int


class MidiaService:
    def __init__(
        self,
        armazenamento: Armazenamento | None = None,
        tamanho_max: int | None = None,
        lado_max: int | None = None,
    ) -> None:
        config = current_app.config
        self.armazenamento = armazenamento or criar_armazenamento()
        self.tamanho_max = tamanho_max or config["TAMANHO_MAX_IMAGEM"]
        self.lado_max = lado_max or config["LADO_MAX_IMAGEM"]

    def processar_upload(self, arquivo: IO[bytes]) -> ImagemSalva:
        """Valida, corrige a rotação, reduz e salva como WebP."""
        dados = arquivo.read(self.tamanho_max + 1)
        if not dados:
            raise ErroDeNegocio("Escolha uma imagem.")
        if len(dados) > self.tamanho_max:
            limite_mb = self.tamanho_max // (1024 * 1024)
            raise ErroDeNegocio(f"A imagem pode ter no máximo {limite_mb} MB.")

        try:
            with Image.open(BytesIO(dados)) as conferencia:
                formato = conferencia.format
                conferencia.verify()  # detecta arquivo corrompido
            imagem = Image.open(BytesIO(dados))
            imagem.load()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise ErroDeNegocio("O arquivo enviado não é uma imagem válida.") from None

        if formato not in FORMATOS_ACEITOS:
            raise ErroDeNegocio("Envie uma imagem JPEG, PNG ou WebP.")

        imagem = ImageOps.exif_transpose(imagem)  # respeita a rotação do celular
        imagem.thumbnail((self.lado_max, self.lado_max))
        tem_transparencia = imagem.mode in ("RGBA", "LA") or (
            imagem.mode == "P" and "transparency" in imagem.info
        )
        imagem = imagem.convert("RGBA" if tem_transparencia else "RGB")

        saida = BytesIO()
        imagem.save(saida, "WEBP", quality=85, method=4)
        nome = f"{uuid4().hex}.webp"
        self.armazenamento.salvar(nome, saida.getvalue(), TIPO_SAIDA)
        return ImagemSalva(nome, imagem.width, imagem.height)

    def ler(self, nome_arquivo: str) -> bytes | None:
        return self.armazenamento.ler(nome_arquivo)

    def caminho(self, nome_arquivo: str) -> str:
        """Confere se o nome é seguro (sem pastas). Mantido para os testes."""
        return validar_nome_arquivo(nome_arquivo)

    def apagar(self, nome_arquivo: str | None) -> None:
        if nome_arquivo:
            self.armazenamento.apagar(nome_arquivo)
