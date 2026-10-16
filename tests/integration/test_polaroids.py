"""Publicação, edição, upload, Arquivo e Lixeira (RF07–RF12, RF28–RF30)."""

from datetime import timedelta
from io import BytesIO
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import func, select

from app.domain.enums import Emocao, StatusPolaroid, Visibilidade
from app.domain.excecoes import AcessoNegado, ErroDeNegocio, NaoEncontrado
from app.domain.tempo import agora
from app.extensions import db
from app.models import Comentario, Curtida, Midia, Notificacao, Polaroid
from app.services.interacao_service import InteracaoService
from app.services.midia_service import MidiaService
from app.services.polaroid_service import DadosPolaroid, PolaroidService
from tests.conftest import gerar_imagem


def contar(modelo: type) -> int:
    return db.session.scalar(select(func.count()).select_from(modelo)) or 0


def test_publicar_pela_rota(client: FlaskClient, criar_usuario, entrar, app: Flask) -> None:  # type: ignore[no-untyped-def]
    entrar(criar_usuario("ana"))
    resposta = client.post(
        "/polaroids/nova",
        data={
            "foto": (gerar_imagem("JPEG", (3000, 2000)), "praia.jpg"),
            "legenda": "Primeiro dia na praia",
            "emocoes": ["FELICIDADE", "PAZ"],
            "estado": "PRESERVADA",
            "visibilidade": "AUTOMATICA",
            "modo_comentarios": "TODOS",
            "musica_titulo": "Garota de Ipanema",
            "musica_url": "https://open.spotify.com/track/abc",
        },
        content_type="multipart/form-data",
    )
    assert resposta.status_code == 302
    polaroid = db.session.scalar(select(Polaroid))
    assert polaroid.emocoes == [Emocao.FELICIDADE, Emocao.PAZ]
    foto = polaroid.foto
    assert foto is not None and max(foto.largura, foto.altura) == 1600  # RN18: redimensionada
    assert (Path(app.config["UPLOAD_FOLDER"]) / foto.caminho_arquivo).exists()

    pagina = client.get(f"/polaroids/{polaroid.id}")
    assert "Primeiro dia na praia".encode() in pagina.data


def test_rn11_mais_de_3_emocoes_pela_rota(client: FlaskClient, criar_usuario, entrar) -> None:  # type: ignore[no-untyped-def]
    entrar(criar_usuario("ana"))
    resposta = client.post(
        "/polaroids/nova",
        data={
            "foto": (gerar_imagem(), "a.png"),
            "legenda": "Teste",
            "emocoes": ["AMOR", "PAZ", "SAUDADE", "ORGULHO"],
            "estado": "PRESERVADA",
            "visibilidade": "PUBLICA",
            "modo_comentarios": "TODOS",
        },
        content_type="multipart/form-data",
    )
    assert resposta.status_code == 200
    assert "no máximo 3 emoções".encode() in resposta.data
    assert contar(Polaroid) == 0


def test_rn18_rejeita_arquivo_que_nao_e_imagem(app: Flask) -> None:
    falso = BytesIO(b"<?php echo 'oi'; ?>")
    with pytest.raises(ErroDeNegocio, match="não é uma imagem"):
        MidiaService().processar_upload(falso)


def test_rn18_rejeita_imagem_maior_que_5mb(app: Flask) -> None:
    grande = BytesIO(b"\x89PNG" + b"0" * (5 * 1024 * 1024 + 10))
    with pytest.raises(ErroDeNegocio, match="5 MB"):
        MidiaService().processar_upload(grande)


def test_rn18_rejeita_gif(app: Flask) -> None:
    with pytest.raises(ErroDeNegocio, match="JPEG, PNG ou WebP"):
        MidiaService().processar_upload(gerar_imagem("GIF"))


def test_midia_nao_aceita_caminho_com_pastas(app: Flask) -> None:
    with pytest.raises(ErroDeNegocio):
        MidiaService().caminho("../.env")


def test_falha_ao_publicar_nao_deixa_arquivo_orfao(app: Flask, criar_usuario) -> None:  # type: ignore[no-untyped-def]
    autor = criar_usuario("ana")
    with pytest.raises(ErroDeNegocio):
        PolaroidService().publicar(autor, DadosPolaroid(legenda="   "), gerar_imagem())
    assert list(Path(app.config["UPLOAD_FOLDER"]).iterdir()) == []


def test_editar_marca_editado_e_so_autor_edita(criar_usuario, criar_polaroid) -> None:  # type: ignore[no-untyped-def]
    ana, bia = criar_usuario("ana"), criar_usuario("bia")
    polaroid = criar_polaroid(ana, visibilidade=Visibilidade.PUBLICA)
    assert not polaroid.foi_editada
    PolaroidService().editar(ana, polaroid.id, DadosPolaroid(legenda="Nova legenda"))
    assert polaroid.foi_editada and polaroid.legenda == "Nova legenda"
    with pytest.raises(AcessoNegado):
        PolaroidService().editar(bia, polaroid.id, DadosPolaroid(legenda="Invasão"))


def test_editar_pela_rota_de_outro_usuario_da_403(client: FlaskClient, criar_usuario, criar_polaroid, entrar) -> None:  # type: ignore[no-untyped-def]
    polaroid = criar_polaroid(criar_usuario("ana"), visibilidade=Visibilidade.PUBLICA)
    entrar(criar_usuario("bia"))
    assert client.get(f"/polaroids/{polaroid.id}/editar").status_code == 403


def test_polaroid_invisivel_da_404(client: FlaskClient, criar_usuario, criar_polaroid, entrar) -> None:  # type: ignore[no-untyped-def]
    polaroid = criar_polaroid(criar_usuario("ana"), visibilidade=Visibilidade.SOMENTE_EU)
    entrar(criar_usuario("bia"))
    assert client.get(f"/polaroids/{polaroid.id}").status_code == 404
    nome = polaroid.foto.caminho_arquivo
    assert client.get(f"/midia/{nome}").status_code == 404  # a foto também é protegida


def test_rn04_arquivo_e_lixeira(client: FlaskClient, criar_usuario, criar_polaroid, entrar) -> None:  # type: ignore[no-untyped-def]
    ana, bia = criar_usuario("ana"), criar_usuario("bia")
    polaroid = criar_polaroid(ana, visibilidade=Visibilidade.PUBLICA)
    servico = PolaroidService()

    servico.arquivar(ana, polaroid.id)
    assert servico.arquivadas(ana) == [polaroid]
    with pytest.raises(NaoEncontrado):
        servico.obter_visivel(bia, polaroid.id)

    servico.desarquivar(ana, polaroid.id)
    servico.mover_para_lixeira(ana, polaroid.id)
    assert servico.na_lixeira(ana) == [polaroid]
    servico.restaurar(ana, polaroid.id)
    assert polaroid.status is StatusPolaroid.ATIVA

    entrar(ana)
    assert client.post(f"/polaroids/{polaroid.id}/excluir").status_code == 302
    assert "dia(s) restantes".encode() in client.get("/lixeira").data


def test_rn14_limpeza_apaga_tudo_junto(app: Flask, criar_usuario, criar_polaroid) -> None:  # type: ignore[no-untyped-def]
    ana, bia = criar_usuario("ana"), criar_usuario("bia")
    velha = criar_polaroid(ana, visibilidade=Visibilidade.PUBLICA)
    recente = criar_polaroid(ana, visibilidade=Visibilidade.PUBLICA)
    InteracaoService().alternar_curtida(bia, velha.id)
    InteracaoService().comentar(bia, velha.id, "Que saudade")
    arquivo = Path(app.config["UPLOAD_FOLDER"]) / velha.foto.caminho_arquivo

    servico = PolaroidService()
    servico.mover_para_lixeira(ana, velha.id)
    servico.mover_para_lixeira(ana, recente.id)
    velha.excluida_em = agora() - timedelta(days=31)
    db.session.commit()

    assert servico.limpar_lixeira_expirada() == 1
    assert db.session.get(Polaroid, recente.id) is not None  # ainda dentro dos 30 dias
    assert contar(Polaroid) == 1
    assert contar(Midia) == 1
    assert contar(Comentario) == 0
    assert contar(Curtida) == 0
    assert contar(Notificacao) == 0
    assert not arquivo.exists()


def test_comando_limpar_lixeira(app: Flask) -> None:
    resultado = app.test_cli_runner().invoke(args=["limpar-lixeira"])
    assert "0 memória(s) apagada(s)" in resultado.output
