CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
INSERT INTO schema_version (version)
SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM schema_version);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attempts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    lesson_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('quiz', 'warmup', 'review')),
    answer TEXT NOT NULL,
    correct BOOLEAN NOT NULL,
    confidence TEXT NOT NULL CHECK (confidence IN ('sure', 'thinkso', 'guessing')),
    try_no INTEGER NOT NULL,
    elapsed_ms INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_attempts_user_lesson ON attempts(user_id, lesson_id);

CREATE TABLE IF NOT EXISTS grades (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    lesson_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    attempt_no INTEGER NOT NULL,
    answer TEXT NOT NULL,
    result_json TEXT NOT NULL,
    flagged BOOLEAN NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_grades_user_lesson ON grades(user_id, lesson_id, question_id);

CREATE TABLE IF NOT EXISTS cards (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    item_key TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    card_json TEXT NOT NULL,
    due TEXT NOT NULL,
    last_rating INTEGER,
    updated_at TEXT NOT NULL,
    UNIQUE (user_id, item_key)
);
CREATE INDEX IF NOT EXISTS idx_cards_user_due ON cards(user_id, due);

CREATE TABLE IF NOT EXISTS review_logs (
    id BIGSERIAL PRIMARY KEY,
    card_id BIGINT NOT NULL REFERENCES cards(id),
    log_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chats (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    lesson_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    ceiling TEXT,
    citations_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chats_user_lesson ON chats(user_id, lesson_id, id);

CREATE TABLE IF NOT EXISTS checks (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    lesson_id TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    output TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_checks_user_lesson ON checks(user_id, lesson_id, id);

CREATE TABLE IF NOT EXISTS mastery (
    user_id BIGINT NOT NULL REFERENCES users(id),
    lesson_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('notstarted', 'learning', 'mastered')),
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    kind TEXT NOT NULL,
    data_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_user_kind ON events(user_id, kind);

-- Phase 2 RAG tables (docs/research/rag-and-content-pipeline.md, "Schema on Neon").
CREATE TABLE IF NOT EXISTS pages (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    path TEXT NOT NULL,
    url TEXT,
    title TEXT,
    version_ref TEXT,
    content_sha256 TEXT,
    UNIQUE (source, path)
);

-- array_to_string is only STABLE, and a generated column needs an IMMUTABLE expression.
CREATE OR REPLACE FUNCTION hk_join_text(text[]) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$ SELECT array_to_string($1, ' ') $$;

CREATE TABLE IF NOT EXISTS chunks (
    chunk_key TEXT PRIMARY KEY,
    page_id BIGINT NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    anchor TEXT,
    heading_path TEXT[],
    ordinal INTEGER,
    text TEXT NOT NULL,
    embed_text TEXT,
    content_sha256 TEXT,
    embedding_model TEXT,
    embedding vector(1536),
    tsv tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(hk_join_text(heading_path), '')), 'A')
        || setweight(to_tsvector('english', coalesce(text, '')), 'B')
    ) STORED
);
CREATE INDEX IF NOT EXISTS idx_chunks_tsv ON chunks USING gin (tsv);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
