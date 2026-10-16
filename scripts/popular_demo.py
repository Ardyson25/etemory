"""Cria dados de demonstração no banco de DESENVOLVIMENTO.

Uso (na raiz do projeto, com o venv ativado):
    python scripts/popular_demo.py

Contas criadas (senha de todas: etermory123): ana, bia, caio (conta privada).
Não rode em produção.
"""

import sys
from datetime import date
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw  # noqa: E402

from app import create_app  # noqa: E402
from app.domain.enums import Emocao, EstadoMemoria, ModoComentarios, Visibilidade  # noqa: E402
from app.repositories import UsuarioRepository  # noqa: E402
from app.services.album_service import AlbumService  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402
from app.services.interacao_service import InteracaoService  # noqa: E402
from app.services.polaroid_service import DadosPolaroid, PolaroidService  # noqa: E402
from app.services.usuario_service import UsuarioService  # noqa: E402
from app.services.vinculo_service import VinculoService  # noqa: E402

SENHA = "etermory123"


def imagem(cor_topo: tuple[int, int, int], cor_base: tuple[int, int, int], texto: str) -> BytesIO:
    """Gradiente simples com um texto, para servir de "foto"."""
    largura, altura = 900, 900
    figura = Image.new("RGB", (largura, altura))
    desenho = ImageDraw.Draw(figura)
    for y in range(altura):
        t = y / altura
        cor = tuple(int(a + (b - a) * t) for a, b in zip(cor_topo, cor_base))
        desenho.line([(0, y), (largura, y)], fill=cor)
    desenho.ellipse((560, 120, 760, 320), fill=(251, 242, 208))
    desenho.text((60, 800), texto, fill=(251, 242, 208))
    buffer = BytesIO()
    figura.save(buffer, "JPEG", quality=90)
    buffer.seek(0)
    return buffer


def main() -> None:
    app = create_app("desenvolvimento")
    with app.app_context():
        if UsuarioRepository().por_username("ana"):
            print("Os dados de demonstração já existem. Nada foi feito.")
            return

        auth = AuthService()
        ana = auth.cadastrar("Ana Clara", "ana", "ana@etermory.dev", SENHA)
        bia = auth.cadastrar("Bia Souza", "bia", "bia@etermory.dev", SENHA)
        caio = auth.cadastrar("Caio Lima", "caio", "caio@etermory.dev", SENHA)

        UsuarioService().atualizar_perfil(
            ana, "Ana Clara", "Colecionando memórias que permanecem.", "https://etermory.dev",
            foto=imagem((140, 26, 17), (60, 10, 8), "Ana"),
            capa=imagem((200, 120, 80), (140, 26, 17), ""),
        )
        UsuarioService().atualizar_perfil(
            bia, "Bia Souza", "Fotografia e saudade.", None,
            foto=imagem((40, 90, 120), (20, 40, 60), "Bia"),
        )
        UsuarioService().configurar(caio, conta_privada=True, modo_comentarios_padrao=ModoComentarios.TODOS)

        vinculos = VinculoService()
        vinculos.seguir(bia, ana)
        vinculos.seguir(ana, bia)
        vinculos.alternar_melhor_amigo(ana, bia.id)
        vinculos.seguir(ana, caio)  # fica pendente (conta privada)

        polaroids = PolaroidService()
        praia = polaroids.publicar(
            ana,
            DadosPolaroid(
                legenda="Primeiro pôr do sol do ano, com @bia. O mar parecia guardar tudo.",
                data_memoria=date(2026, 1, 1),
                emocoes=[Emocao.FELICIDADE, Emocao.PAZ, Emocao.RECOMECO],
                visibilidade=Visibilidade.PUBLICA,
                musica_titulo="Garota de Ipanema",
                musica_artista="Tom Jobim",
                musica_url="https://open.spotify.com/",
                local_nome="Praia de Ipanema",
            ),
            imagem((242, 140, 60), (140, 26, 17), "Ipanema, 01/01/2026"),
        )
        vovo = polaroids.publicar(
            ana,
            DadosPolaroid(
                legenda="A cozinha da vó num domingo qualquer. Só os melhores amigos sabem dessa história.",
                data_memoria=date(2019, 7, 14),
                emocoes=[Emocao.SAUDADE, Emocao.NOSTALGIA],
                estado=EstadoMemoria.SENSIVEL,
                visibilidade=Visibilidade.MELHORES_AMIGOS,
                local_nome="Casa da vó",
            ),
            imagem((120, 80, 50), (40, 25, 15), "Domingo, 2019"),
        )
        formatura = polaroids.publicar(
            bia,
            DadosPolaroid(
                legenda="Formatura! Quatro anos em uma foto.",
                data_memoria=date(2025, 12, 10),
                emocoes=[Emocao.CONQUISTA, Emocao.ORGULHO, Emocao.GRATIDAO],
                estado=EstadoMemoria.REVISITADA,
                visibilidade=Visibilidade.PUBLICA,
                musica_titulo="Tempo Perdido",
                musica_artista="Legião Urbana",
            ),
            imagem((30, 60, 110), (10, 20, 40), "Formatura 2025"),
        )
        polaroids.publicar(
            caio,
            DadosPolaroid(
                legenda="Primeira noite na casa nova.",
                emocoes=[Emocao.MUDANCA, Emocao.ESPERANCA],
                estado=EstadoMemoria.FRAGMENTADA,
            ),
            imagem((60, 60, 70), (15, 15, 20), "Casa nova"),
        )

        interacoes = InteracaoService()
        interacoes.alternar_curtida(bia, praia.id)
        interacoes.alternar_curtida(bia, vovo.id)
        interacoes.comentar(bia, praia.id, "Que dia lindo! Quero voltar lá.")
        interacoes.comentar(ana, formatura.id, "Orgulho de você, @bia!")
        interacoes.alternar_curtida(ana, formatura.id)

        album = AlbumService().criar(ana, "Verão 2026", "Dias de sol e sal.", publico=True)
        AlbumService().adicionar(ana, album.id, praia.id)

        print("Dados de demonstração criados.")
        print("Entre com ana, bia ou caio — senha:", SENHA)


if __name__ == "__main__":
    main()
