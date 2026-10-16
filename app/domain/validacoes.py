"""Validações de dados usadas pelos modelos e serviços.

Ficam no domínio para serem testadas sem banco e sem Flask.
"""

import re
from urllib.parse import urlparse

from app.domain.excecoes import ErroDeNegocio

# Limites das regras de negócio
USERNAME_MIN = 3
USERNAME_MAX = 24
SENHA_MIN = 8
NOME_MAX = 80
BIO_MAX = 300
LEGENDA_MAX = 2000
COMENTARIO_MAX = 500  # RN09
TITULO_ALBUM_MAX = 80  # RN13
DESCRICAO_ALBUM_MAX = 300
MAX_EMOCOES = 3  # RN11
DIAS_NA_LIXEIRA = 30  # RN14

PADRAO_USERNAME = re.compile(r"^[a-z0-9._]{3,24}$")  # RN12
PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_username(username: str) -> str:
    """RN12: 3 a 24 caracteres, só minúsculas, números, ponto e sublinhado."""
    username = (username or "").strip().lstrip("@")
    if not PADRAO_USERNAME.fullmatch(username):
        raise ErroDeNegocio(
            "O @username deve ter de 3 a 24 caracteres e usar só letras "
            "minúsculas, números, ponto e sublinhado."
        )
    return username


def validar_email(email: str) -> str:
    email = (email or "").strip().lower()
    if len(email) > 254 or not PADRAO_EMAIL.fullmatch(email):
        raise ErroDeNegocio("Informe um e-mail válido.")
    return email


def validar_senha(senha: str) -> str:
    if len(senha or "") < SENHA_MIN:
        raise ErroDeNegocio(f"A senha deve ter pelo menos {SENHA_MIN} caracteres.")
    return senha


def validar_texto(
    texto: str | None, campo: str, minimo: int, maximo: int
) -> str:
    """Remove espaços das pontas e confere o tamanho."""
    texto = (texto or "").strip()
    if len(texto) < minimo:
        raise ErroDeNegocio(f"{campo} é obrigatório(a).")
    if len(texto) > maximo:
        raise ErroDeNegocio(f"{campo} pode ter no máximo {maximo} caracteres.")
    return texto


def validar_url_https(url: str | None, campo: str = "O link") -> str | None:
    """RN17: links só com https://. Campo vazio vira ``None``."""
    url = (url or "").strip()
    if not url:
        return None
    partes = urlparse(url)
    if partes.scheme != "https" or not partes.netloc or len(url) > 255:
        raise ErroDeNegocio(f"{campo} deve começar com https://.")
    return url
