"""Encapsulamento dos modelos: objetos criados sem salvar no banco."""

from datetime import timedelta

import pytest

from app.domain.enums import Emocao, StatusPolaroid, StatusVinculo, Visibilidade
from app.domain.excecoes import AcessoNegado, ErroDeNegocio, TransicaoInvalida
from app.domain.tempo import agora
from app.models import Album, Comentario, Polaroid, Usuario, Vinculo


def novo_usuario(id_: int, privada: bool = False) -> Usuario:
    usuario = Usuario(
        nome="Ana", username=f"ana{id_}", email=f"ana{id_}@x.com", senha="12345678",
        conta_privada=privada,
    )
    usuario.id = id_
    return usuario


def nova_polaroid(autor: Usuario) -> Polaroid:
    return Polaroid(autor=autor, autor_id=autor.id, legenda="Praia")


def test_senha_guardada_so_como_hash(app) -> None:  # type: ignore[no-untyped-def]
    usuario = novo_usuario(1)
    assert "12345678" not in usuario._senha_hash
    assert usuario.verificar_senha("12345678")
    assert not usuario.verificar_senha("errada")
    with pytest.raises(ErroDeNegocio):
        usuario.definir_senha("curta")


def test_rn12_username_validado_ao_atribuir(app) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ErroDeNegocio):
        novo_usuario(1).username = "Inválido!"


def test_rn11_legenda_obrigatoria_e_ate_3_emocoes(app) -> None:  # type: ignore[no-untyped-def]
    autor = novo_usuario(1)
    with pytest.raises(ErroDeNegocio):
        Polaroid(autor=autor, autor_id=1, legenda="   ")
    polaroid = nova_polaroid(autor)
    polaroid.definir_emocoes([Emocao.AMOR, Emocao.PAZ, Emocao.AMOR])  # repetida conta uma vez
    assert polaroid.emocoes == [Emocao.AMOR, Emocao.PAZ]
    with pytest.raises(ErroDeNegocio):
        polaroid.definir_emocoes([Emocao.AMOR, Emocao.PAZ, Emocao.SAUDADE, Emocao.ORGULHO])


def test_rn17_musica_so_https(app) -> None:  # type: ignore[no-untyped-def]
    polaroid = nova_polaroid(novo_usuario(1))
    with pytest.raises(ErroDeNegocio):
        polaroid.musica_url = "http://spotify.com"


def test_transicoes_de_status(app) -> None:  # type: ignore[no-untyped-def]
    polaroid = nova_polaroid(novo_usuario(1))
    assert polaroid.status is StatusPolaroid.ATIVA

    polaroid.arquivar()
    assert polaroid.status is StatusPolaroid.ARQUIVADA
    with pytest.raises(TransicaoInvalida):
        polaroid.arquivar()
    polaroid.desarquivar()

    polaroid.mover_para_lixeira()
    assert polaroid.dias_restantes_na_lixeira == 30
    polaroid.restaurar()
    assert polaroid.status is StatusPolaroid.ATIVA
    with pytest.raises(TransicaoInvalida):
        polaroid.restaurar()


def test_rn14_nao_restaura_depois_de_30_dias(app) -> None:  # type: ignore[no-untyped-def]
    polaroid = nova_polaroid(novo_usuario(1))
    polaroid.mover_para_lixeira()
    polaroid.excluida_em = agora() - timedelta(days=30)
    assert polaroid.dias_restantes_na_lixeira == 0
    with pytest.raises(TransicaoInvalida):
        polaroid.restaurar()


def test_status_nao_tem_setter(app) -> None:  # type: ignore[no-untyped-def]
    polaroid = nova_polaroid(novo_usuario(1))
    with pytest.raises(AttributeError):
        polaroid.status = StatusPolaroid.LIXEIRA  # type: ignore[misc]


def test_visibilidade_efetiva_acompanha_a_conta(app) -> None:  # type: ignore[no-untyped-def]
    autor = novo_usuario(1)
    polaroid = nova_polaroid(autor)
    assert polaroid.visibilidade_efetiva is Visibilidade.PUBLICA
    autor.conta_privada = True
    assert polaroid.visibilidade_efetiva is Visibilidade.SEGUIDORES


def test_rn07_vinculo_privado_comeca_pendente(app) -> None:  # type: ignore[no-untyped-def]
    ana, bia = novo_usuario(1), novo_usuario(2, privada=True)
    vinculo = Vinculo.criar(ana, bia)
    assert vinculo.status is StatusVinculo.PENDENTE
    with pytest.raises(ErroDeNegocio):
        vinculo.marcar_melhor_amigo()  # RN06
    vinculo.aceitar()
    vinculo.marcar_melhor_amigo()
    assert vinculo.melhor_amigo
    with pytest.raises(TransicaoInvalida):
        vinculo.cancelar()
    with pytest.raises(ErroDeNegocio):
        Vinculo.criar(ana, ana)  # RN15


def test_rn09_comentario(app) -> None:  # type: ignore[no-untyped-def]
    dono, autor, outro = novo_usuario(1), novo_usuario(2), novo_usuario(3)
    polaroid = nova_polaroid(dono)
    comentario = Comentario(polaroid=polaroid, autor=autor, autor_id=2, texto="Lindo")
    with pytest.raises(ErroDeNegocio):
        comentario.texto = "x" * 501
    with pytest.raises(AcessoNegado):
        comentario.editar("Outro texto", dono)
    comentario.editar("Lindo demais", autor)
    assert comentario.foi_editado
    assert comentario.pode_ser_excluido_por(dono)
    assert comentario.pode_ser_excluido_por(autor)
    assert not comentario.pode_ser_excluido_por(outro)


def test_rn13_album(app) -> None:  # type: ignore[no-untyped-def]
    dono, outro = novo_usuario(1), novo_usuario(2)
    with pytest.raises(ErroDeNegocio):
        Album(dono=dono, dono_id=1, titulo="x" * 81)
    album = Album(dono=dono, dono_id=1, titulo="Férias")
    with pytest.raises(AcessoNegado):
        album.adicionar(nova_polaroid(outro))  # RC03
