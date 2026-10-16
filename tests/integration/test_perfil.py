"""Prontuário, edição de perfil e configurações (RF03–RF06)."""

from flask.testing import FlaskClient

from app.domain.enums import ModoComentarios
from tests.conftest import gerar_imagem


def test_editar_prontuario_com_foto(client: FlaskClient, criar_usuario, entrar) -> None:  # type: ignore[no-untyped-def]
    ana = criar_usuario("ana")
    entrar(ana)
    resposta = client.post(
        "/perfil/editar",
        data={
            "nome": "Ana Clara",
            "bio": "Guardando memórias",
            "site": "https://ana.dev",
            "foto": (gerar_imagem(), "eu.png"),
        },
        content_type="multipart/form-data",
    )
    assert resposta.status_code == 302
    assert ana.nome == "Ana Clara" and ana.foto
    assert client.get(f"/midia/{ana.foto}").status_code == 200


def test_rn17_site_sem_https(client: FlaskClient, criar_usuario, entrar) -> None:  # type: ignore[no-untyped-def]
    ana = criar_usuario("ana")
    entrar(ana)
    resposta = client.post("/perfil/editar", data={"nome": "Ana", "site": "http://ana.dev"})
    assert resposta.status_code == 200
    assert "https://".encode() in resposta.data
    assert ana.site is None


def test_configuracoes_e_senha(client: FlaskClient, criar_usuario, entrar) -> None:  # type: ignore[no-untyped-def]
    ana = criar_usuario("ana")
    entrar(ana)
    client.post(
        "/configuracoes",
        data={"cfg-conta_privada": "y", "cfg-modo_comentarios_padrao": "SEGUIDORES", "cfg-enviar": "1"},
    )
    assert ana.conta_privada
    assert ana.modo_comentarios_padrao is ModoComentarios.SEGUIDORES

    errada = client.post(
        "/configuracoes",
        data={
            "senha-senha_atual": "errada",
            "senha-nova_senha": "nova-senha-123",
            "senha-confirmar": "nova-senha-123",
            "senha-enviar_senha": "1",
        },
        follow_redirects=True,
    )
    assert "senha atual está incorreta".encode() in errada.data
    client.post(
        "/configuracoes",
        data={
            "senha-senha_atual": "senha-segura-123",
            "senha-nova_senha": "nova-senha-123",
            "senha-confirmar": "nova-senha-123",
            "senha-enviar_senha": "1",
        },
    )
    assert ana.verificar_senha("nova-senha-123")


def test_prontuario_inexistente(client: FlaskClient, criar_usuario, entrar) -> None:  # type: ignore[no-untyped-def]
    entrar(criar_usuario("ana"))
    assert client.get("/@naoexiste").status_code == 404
    assert client.get("/@ana/seguidores").status_code == 200
