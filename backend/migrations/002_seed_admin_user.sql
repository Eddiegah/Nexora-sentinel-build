-- Nexora Sentinel — seed admin user
-- Default credentials:  admin@nexora-sentinel.local / Sentinel2024!
-- CHANGE THE PASSWORD before any public deployment:
--   1. Generate a new hash:
--      python -c "import bcrypt; print(bcrypt.hashpw(b'your-password', bcrypt.gensalt(12)).decode())"
--   2. Replace the hash value below and re-run this migration.
-- Run:  psql $DATABASE_URL -f backend/migrations/002_seed_admin_user.sql

BEGIN;

INSERT INTO users (email, password_hash, role)
VALUES (
    'admin@nexora-sentinel.local',
    '$2b$12$rjhnOyxBAHdaiqUL/UbcTe5zL9UzZ3WAbW7d6bLfFA8sPfnrCeV8u',
    'admin'
)
ON CONFLICT (email) DO NOTHING;

COMMIT;
