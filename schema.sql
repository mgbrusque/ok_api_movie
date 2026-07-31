BEGIN;

CREATE TABLE IF NOT EXISTS server (
    id BIGSERIAL PRIMARY KEY,
    server TEXT NOT NULL UNIQUE,
    active SMALLINT NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    type TEXT NOT NULL DEFAULT 'UPLOAD'
);

CREATE TABLE IF NOT EXISTS filmes (
    id BIGINT PRIMARY KEY,
    nome TEXT NOT NULL,
    tempo TEXT,
    imagem TEXT,
    idserver BIGINT REFERENCES server(id) ON DELETE SET NULL,
    ordernum INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_filmes_idserver ON filmes (idserver);
CREATE INDEX IF NOT EXISTS idx_filmes_created_at ON filmes (created_at DESC);

CREATE TABLE IF NOT EXISTS infofilmes (
    id BIGINT PRIMARY KEY,
    id_imdb TEXT,
    titulo TEXT,
    sinopse TEXT,
    imagem TEXT,
    generos TEXT,
    nota TEXT,
    language VARCHAR(16)
);

COMMIT;
