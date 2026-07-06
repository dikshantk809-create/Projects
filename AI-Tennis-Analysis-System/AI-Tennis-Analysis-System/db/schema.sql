-- ============================================================================
-- AI Tennis Analysis — PostgreSQL 16 + TimescaleDB schema
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE players (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, hand TEXT DEFAULT 'R'  -- R/L
);
CREATE TABLE matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    started_at TIMESTAMPTZ DEFAULT now(), ended_at TIMESTAMPTZ,
    player_a TEXT REFERENCES players(id), player_b TEXT REFERENCES players(id),
    best_of SMALLINT DEFAULT 3, surface TEXT DEFAULT 'hard',
    court_calibration JSONB,                      -- homography + court model
    status TEXT DEFAULT 'live'                    -- live/finished
);
CREATE TABLE sets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID REFERENCES matches(id) ON DELETE CASCADE,
    idx SMALLINT, games_a SMALLINT DEFAULT 0, games_b SMALLINT DEFAULT 0,
    winner TEXT
);
CREATE TABLE games (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    set_id UUID REFERENCES sets(id) ON DELETE CASCADE,
    idx SMALLINT, server TEXT, winner TEXT
);
CREATE TABLE points (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID REFERENCES games(id) ON DELETE CASCADE,
    ts TIMESTAMPTZ DEFAULT now(),
    winner TEXT,                                  -- 'a'/'b'
    reason TEXT,                                  -- winner/unforced_error/ace/double_fault/out
    score_after TEXT                              -- '15-0','40-30','AD-40'...
);
CREATE TABLE rallies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    point_id UUID REFERENCES points(id) ON DELETE CASCADE,
    shot_count SMALLINT, duration_s REAL
);
CREATE TABLE shots (
    id BIGSERIAL PRIMARY KEY, rally_id UUID REFERENCES rallies(id) ON DELETE CASCADE,
    player TEXT, ts TIMESTAMPTZ, kind TEXT,       -- serve/forehand/backhand/volley
    speed_kmh REAL, placement JSONB,              -- court-plane (x,y)
    outcome TEXT                                  -- in/out/net/winner/error
);
CREATE TABLE serves (
    id BIGSERIAL PRIMARY KEY, point_id UUID, player TEXT,
    speed_kmh REAL, is_ace BOOLEAN DEFAULT FALSE, is_fault BOOLEAN DEFAULT FALSE
);

-- ---- Time-series tracking (Timescale) -------------------------------------
CREATE TABLE ball_positions (
    match_id UUID, ts TIMESTAMPTZ NOT NULL,
    frame INTEGER, x REAL, y REAL,                -- image px
    cx REAL, cy REAL,                             -- court-plane meters (post-homography)
    visible BOOLEAN, PRIMARY KEY (match_id, ts, frame)
);
SELECT create_hypertable('ball_positions','ts', if_not_exists => TRUE);
CREATE TABLE player_tracks (
    match_id UUID, ts TIMESTAMPTZ NOT NULL, player TEXT,
    x REAL, y REAL, cx REAL, cy REAL, speed_ms REAL,
    PRIMARY KEY (match_id, ts, player)
);
SELECT create_hypertable('player_tracks','ts', if_not_exists => TRUE);

CREATE TABLE line_calls (
    id BIGSERIAL PRIMARY KEY, match_id UUID, point_id UUID, ts TIMESTAMPTZ DEFAULT now(),
    call TEXT,                                    -- in/out/let
    bounce_cx REAL, bounce_cy REAL, margin_cm REAL, confidence REAL, frame INTEGER
);
CREATE TABLE highlights (
    id BIGSERIAL PRIMARY KEY, match_id UUID, ts TIMESTAMPTZ,
    kind TEXT, media_ref TEXT, label TEXT          -- ace/winner/long_rally/break_point
);
