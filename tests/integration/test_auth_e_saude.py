"""Rotas de saúde, cadastro, login e logout (RF01, RF02, RF31, RN01)."""

from flask.testing import FlaskClient

from app.models import Usuario
from app.repositories import UsuarioRepository


def test_saude_responde_sem_login(client: FlaskClient) -> None:
    resposta = client.get("/saude")
    assert resposta.status_code == 200
    assert resposta.get_json() == {"status": "ok", "instancia": "teste"}


def test_rn01_sem_login_vai_para_entrar(client: FlaskClient) -> None:
    resposta = client.get("/")
    assert resposta.status_code == 302
    assert "/entrar" in resposta.headers["Location"]


def test_cadastro_cria_conta_com_hash_e_loga(client: FlaskClient) -> None:
    resposta = client.post(
        "/cadastro",
        data={
            "nome": "Ana Clara",
            "username": "ana.clara",
            "email": "ANA@exemplo.com",
            "senha": "senha-segura-123",
            "confirmar": "senha-segura-123",
        },
    )
    assert resposta.status_code == 302
    usuario = UsuarioRepository().por_username("ana.clara")
    assert usuario is not None
    assert usuario.email == "ana@exemplo.com"
    assert usuario._senha_hash != "senha-segura-123"
    assert client.get("/").status_code == 200  # já está logado


def test_rn12_username_repetido(client: FlaskClient, criar_usuario) -> None:  # type: ignore[no-untyped-def]
    criar_usuario("ana")
    resposta = client.post(
        "/cadastro",
        data={
            "nome": "Outra Ana",
            "username": "ana",
            "email": "outra@exemplo.com",
            "senha": "senha-segura-123",
            "confirmar": "senha-segura-123",
        },
        follow_redirects=True,
    )
    assert "já está em uso".encode() in resposta.data


def test_login_por_username_e_senha_errada(client: FlaskClient, criar_usuario) -> None:  # type: ignore[no-untyped-def]
    usuario: Usuario = criar_usuario("bia")
    errado = client.post("/entrar", data={"login": "bia", "senha": "errada"})
    assert "E-mail ou senha incorretos".encode() in errado.data
    certo = client.post("/entrar", data={"login": "@bia", "senha": "senha-segura-123"})
    assert certo.status_code == 302
    assert usuario.username == "bia"


def test_next_externo_e_ignorado(client: FlaskClient, criar_usuario) -> None:  # type: ignore[no-untyped-def]
    criar_usuario("caio")
    resposta = client.post(
        "/entrar?next=https://site-malicioso.com",
        data={"login": "caio", "senha": "senha-segura-123"},
    )
    assert resposta.headers["Location"] == "/"


def test_sair(client: FlaskClient, criar_usuario, entrar) -> None:  # type: ignore[no-untyped-def]
    entrar(criar_usuario("dani"))
    client.post("/sair")
    assert client.get("/").status_code == 302
