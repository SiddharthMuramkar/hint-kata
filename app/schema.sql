CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    lesson_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('quiz', 'warmup', 'review')),
    answer TEXT NOT NULL,
    correct INTEGER NOT NULL CHECK (correct IN (0, 1)),
    confidence TEXT NOT NULL CHECK (confidence IN ('sure', 'thinkso', 'guessing')),
    try_no INTEGER NOT NULL,
    elapsed_ms INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_attempts_user_lesson ON attempts(user_id, lesson_id);

CREATE TABLE IF NOT EXISTS grades (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    lesson_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    attempt_no INTEGER NOT NULL,
    answer TEXT NOT NULL,
    result_json TEXT NOT NULL,
    flagged INTEGER NOT NULL CHECK (flagged IN (0, 1)),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_grades_user_lesson ON grades(user_id, lesson_id, question_id);

CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
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
    id INTEGER PRIMARY KEY,
    card_id INTEGER NOT NULL REFERENCES cards(id),
    log_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    lesson_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    ceiling TEXT,
    citations_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chats_user_lesson ON chats(user_id, lesson_id, id);

CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    lesson_id TEXT NOT NULL,
    passed INTEGER NOT NULL CHECK (passed IN (0, 1)),
    output TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_checks_user_lesson ON checks(user_id, lesson_id, id);

CREATE TABLE IF NOT EXISTS mastery (
    user_id INTEGER NOT NULL REFERENCES users(id),
    lesson_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('notstarted', 'learning', 'mastered')),
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    kind TEXT NOT NULL,
    data_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_user_kind ON events(user_id, kind);
