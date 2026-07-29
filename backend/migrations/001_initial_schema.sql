-- Nexora Sentinel — initial schema migration
-- Run once against your Neon Postgres database:
--   psql $DATABASE_URL -f backend/migrations/001_initial_schema.sql

BEGIN;

CREATE TABLE IF NOT EXISTS regions (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    country    TEXT NOT NULL,
    latitude   DOUBLE PRECISION NOT NULL,
    longitude  DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS region_indicators (
    id                 SERIAL PRIMARY KEY,
    region_id          INTEGER REFERENCES regions(id) ON DELETE CASCADE,
    date               DATE NOT NULL,
    rainfall_mm        DOUBLE PRECISION,
    avg_temp_c         DOUBLE PRECISION,
    humidity_pct       DOUBLE PRECISION,
    population_density DOUBLE PRECISION,
    historical_cases   INTEGER,
    source             TEXT NOT NULL,
    CONSTRAINT uq_indicator_region_date_source UNIQUE (region_id, date, source)
);

CREATE TABLE IF NOT EXISTS predictions (
    id               SERIAL PRIMARY KEY,
    region_id        INTEGER REFERENCES regions(id) ON DELETE CASCADE,
    predicted_at     TIMESTAMPTZ DEFAULT now(),
    risk_score       DOUBLE PRECISION NOT NULL,
    risk_category    TEXT NOT NULL,
    model_version    TEXT NOT NULL,
    shap_explanation JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'health_worker',
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- Seed a small set of African regions to populate the dashboard immediately.
-- Coordinates are centroids of major health districts / capitals.
INSERT INTO regions (name, country, latitude, longitude) VALUES
    ('Kampala',         'Uganda',       0.3476,   32.5825),
    ('Nairobi',         'Kenya',       -1.2921,   36.8219),
    ('Dar es Salaam',   'Tanzania',    -6.7924,   39.2083),
    ('Accra',           'Ghana',        5.6037,   -0.1870),
    ('Lagos',           'Nigeria',      6.5244,    3.3792),
    ('Kinshasa',        'DRC',         -4.4419,   15.2663),
    ('Lusaka',          'Zambia',     -15.4167,   28.2833),
    ('Lilongwe',        'Malawi',     -13.9626,   33.7741),
    ('Maputo',          'Mozambique', -25.9692,   32.5732),
    ('Antananarivo',    'Madagascar', -18.9137,   47.5361)
ON CONFLICT DO NOTHING;

COMMIT;
