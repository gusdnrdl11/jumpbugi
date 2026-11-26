-- Local PostgreSQL schema. Initialization only; no destructive migrations.
CREATE TABLE IF NOT EXISTS players (
    player_id UUID PRIMARY KEY,
    nickname TEXT NOT NULL CHECK (char_length(btrim(nickname)) BETWEEN 1 AND 40),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS runs (
    run_id UUID PRIMARY KEY,
    player_id UUID NOT NULL REFERENCES players (player_id),
    nickname TEXT NOT NULL CHECK (char_length(btrim(nickname)) BETWEEN 1 AND 40),
    score BIGINT NOT NULL CHECK (score BETWEEN 0 AND 9007199254740991),
    survival_time DOUBLE PRECISION NOT NULL CHECK (survival_time BETWEEN 0 AND 315360000),
    game_version TEXT NOT NULL CHECK (char_length(btrim(game_version)) BETWEEN 1 AND 40),
    played_at TIMESTAMPTZ NOT NULL,
    death_obstacle TEXT CHECK (char_length(death_obstacle) <= 100),
    max_speed DOUBLE PRECISION NOT NULL CHECK (max_speed BETWEEN 0 AND 1000000),
    device_type TEXT NOT NULL CHECK (device_type IN ('desktop', 'mobile')),
    received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS runs_player_history
    ON runs (player_id, played_at DESC, run_id);
CREATE INDEX IF NOT EXISTS runs_player_best
    ON runs (player_id, score DESC, survival_time DESC, played_at, run_id);
