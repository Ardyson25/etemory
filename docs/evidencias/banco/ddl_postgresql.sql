BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0132012b699f

CREATE TABLE usuarios (
    id SERIAL NOT NULL, 
    nome VARCHAR(80) NOT NULL, 
    username VARCHAR(24) NOT NULL, 
    email VARCHAR(254) NOT NULL, 
    senha_hash VARCHAR(255) NOT NULL, 
    bio VARCHAR(300) NOT NULL, 
    site VARCHAR(255), 
    foto VARCHAR(255), 
    capa VARCHAR(255), 
    conta_privada BOOLEAN NOT NULL, 
    modo_comentarios_padrao VARCHAR(20) NOT NULL, 
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_usuarios PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_usuarios_email ON usuarios (email);

CREATE UNIQUE INDEX ix_usuarios_username ON usuarios (username);

CREATE TABLE albuns (
    id SERIAL NOT NULL, 
    dono_id INTEGER NOT NULL, 
    titulo VARCHAR(80) NOT NULL, 
    descricao VARCHAR(300) NOT NULL, 
    visibilidade VARCHAR(20) NOT NULL, 
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_albuns PRIMARY KEY (id), 
    CONSTRAINT ck_albuns_titulo_tamanho CHECK (length(titulo) BETWEEN 1 AND 80), 
    CONSTRAINT fk_albuns_dono_id_usuarios FOREIGN KEY(dono_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

CREATE INDEX ix_albuns_dono_id ON albuns (dono_id);

CREATE TABLE polaroids (
    id SERIAL NOT NULL, 
    autor_id INTEGER NOT NULL, 
    legenda TEXT NOT NULL, 
    data_memoria DATE, 
    estado VARCHAR(20) NOT NULL, 
    visibilidade VARCHAR(20) NOT NULL, 
    modo_comentarios VARCHAR(20) NOT NULL, 
    musica_titulo VARCHAR(120), 
    musica_artista VARCHAR(120), 
    musica_url VARCHAR(255), 
    local_nome VARCHAR(120), 
    status VARCHAR(20) NOT NULL, 
    arquivada_em TIMESTAMP WITHOUT TIME ZONE, 
    excluida_em TIMESTAMP WITHOUT TIME ZONE, 
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    editado_em TIMESTAMP WITHOUT TIME ZONE, 
    CONSTRAINT pk_polaroids PRIMARY KEY (id), 
    CONSTRAINT fk_polaroids_autor_id_usuarios FOREIGN KEY(autor_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

CREATE INDEX ix_polaroids_autor_criado ON polaroids (autor_id, criado_em);

CREATE INDEX ix_polaroids_criado_em ON polaroids (criado_em);

CREATE INDEX ix_polaroids_status ON polaroids (status);

CREATE TABLE vinculos (
    id SERIAL NOT NULL, 
    seguidor_id INTEGER NOT NULL, 
    seguido_id INTEGER NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    melhor_amigo BOOLEAN NOT NULL, 
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    respondido_em TIMESTAMP WITHOUT TIME ZONE, 
    CONSTRAINT pk_vinculos PRIMARY KEY (id), 
    CONSTRAINT ck_vinculos_nao_segue_a_si CHECK (seguidor_id <> seguido_id), 
    CONSTRAINT fk_vinculos_seguido_id_usuarios FOREIGN KEY(seguido_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
    CONSTRAINT fk_vinculos_seguidor_id_usuarios FOREIGN KEY(seguidor_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
    CONSTRAINT uq_vinculos_par UNIQUE (seguidor_id, seguido_id)
);

CREATE INDEX ix_vinculos_seguido_status ON vinculos (seguido_id, status);

CREATE INDEX ix_vinculos_seguidor_id ON vinculos (seguidor_id);

CREATE TABLE album_polaroid (
    album_id INTEGER NOT NULL, 
    polaroid_id INTEGER NOT NULL, 
    adicionada_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_album_polaroid PRIMARY KEY (album_id, polaroid_id), 
    CONSTRAINT fk_album_polaroid_album_id_albuns FOREIGN KEY(album_id) REFERENCES albuns (id) ON DELETE CASCADE, 
    CONSTRAINT fk_album_polaroid_polaroid_id_polaroids FOREIGN KEY(polaroid_id) REFERENCES polaroids (id) ON DELETE CASCADE
);

CREATE TABLE comentarios (
    id SERIAL NOT NULL, 
    polaroid_id INTEGER NOT NULL, 
    autor_id INTEGER NOT NULL, 
    texto VARCHAR(500) NOT NULL, 
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    editado_em TIMESTAMP WITHOUT TIME ZONE, 
    CONSTRAINT pk_comentarios PRIMARY KEY (id), 
    CONSTRAINT ck_comentarios_texto_tamanho CHECK (length(texto) BETWEEN 1 AND 500), 
    CONSTRAINT fk_comentarios_autor_id_usuarios FOREIGN KEY(autor_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
    CONSTRAINT fk_comentarios_polaroid_id_polaroids FOREIGN KEY(polaroid_id) REFERENCES polaroids (id) ON DELETE CASCADE
);

CREATE INDEX ix_comentarios_polaroid_id ON comentarios (polaroid_id);

CREATE TABLE curtidas (
    usuario_id INTEGER NOT NULL, 
    polaroid_id INTEGER NOT NULL, 
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_curtidas PRIMARY KEY (usuario_id, polaroid_id), 
    CONSTRAINT fk_curtidas_polaroid_id_polaroids FOREIGN KEY(polaroid_id) REFERENCES polaroids (id) ON DELETE CASCADE, 
    CONSTRAINT fk_curtidas_usuario_id_usuarios FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

CREATE TABLE midias (
    id SERIAL NOT NULL, 
    polaroid_id INTEGER NOT NULL, 
    caminho_arquivo VARCHAR(255) NOT NULL, 
    ordem INTEGER NOT NULL, 
    largura INTEGER NOT NULL, 
    altura INTEGER NOT NULL, 
    CONSTRAINT pk_midias PRIMARY KEY (id), 
    CONSTRAINT fk_midias_polaroid_id_polaroids FOREIGN KEY(polaroid_id) REFERENCES polaroids (id) ON DELETE CASCADE
);

CREATE INDEX ix_midias_polaroid_id ON midias (polaroid_id);

CREATE TABLE polaroid_emocoes (
    polaroid_id INTEGER NOT NULL, 
    emocao VARCHAR(20) NOT NULL, 
    CONSTRAINT pk_polaroid_emocoes PRIMARY KEY (polaroid_id, emocao), 
    CONSTRAINT fk_polaroid_emocoes_polaroid_id_polaroids FOREIGN KEY(polaroid_id) REFERENCES polaroids (id) ON DELETE CASCADE
);

CREATE TABLE notificacoes (
    id SERIAL NOT NULL, 
    tipo VARCHAR(30) NOT NULL, 
    destinatario_id INTEGER NOT NULL, 
    remetente_id INTEGER NOT NULL, 
    polaroid_id INTEGER, 
    comentario_id INTEGER, 
    lida BOOLEAN NOT NULL, 
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_notificacoes PRIMARY KEY (id), 
    CONSTRAINT fk_notificacoes_comentario_id_comentarios FOREIGN KEY(comentario_id) REFERENCES comentarios (id) ON DELETE CASCADE, 
    CONSTRAINT fk_notificacoes_destinatario_id_usuarios FOREIGN KEY(destinatario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
    CONSTRAINT fk_notificacoes_polaroid_id_polaroids FOREIGN KEY(polaroid_id) REFERENCES polaroids (id) ON DELETE CASCADE, 
    CONSTRAINT fk_notificacoes_remetente_id_usuarios FOREIGN KEY(remetente_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

CREATE INDEX ix_notificacoes_criado_em ON notificacoes (criado_em);

CREATE INDEX ix_notificacoes_destinatario_lida ON notificacoes (destinatario_id, lida);

INSERT INTO alembic_version (version_num) VALUES ('0132012b699f') RETURNING alembic_version.version_num;

-- Running upgrade 0132012b699f -> 5dcb4bb1f818

CREATE TABLE arquivos (
    nome VARCHAR(255) NOT NULL, 
    tipo VARCHAR(50) NOT NULL, 
    tamanho INTEGER NOT NULL, 
    dados BYTEA NOT NULL, 
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_arquivos PRIMARY KEY (nome)
);

UPDATE alembic_version SET version_num='5dcb4bb1f818' WHERE alembic_version.version_num = '0132012b699f';

COMMIT;

