# Nexora Sentinel — Project Steering File

## Project Overview

**Name:** Nexora Sentinel  
**Description:** An AI-powered clinical/public-health intelligence platform that predicts malaria outbreak risk across regions in Africa, explains its predictions with SHAP, and surfaces them on a dashboard for health workers and policymakers.

---

## Tech Stack (fixed — do not substitute without updating this file)

| Layer | Technology | Hosting |
|-------|-----------|---------|
| Frontend | React (Vite) | Vercel (free Hobby tier) |
| Backend | Python FastAPI | Render (free Web Service tier) |
| Database | PostgreSQL | Neon (free tier, serverless — NOT Render's built-in Postgres, which auto-deletes after 30 days) |
| ML Model | XGBoost + SHAP | Trained offline, artifacts committed to repo, loaded by API at startup |
| Auth | JWT (custom, no paid provider) | — |
| Background jobs | GitHub Actions cron (free) | — |
| Task queue | None in MVP — keep synchronous | — |

---

## Repo Layout Conventions

```
/backend   — FastAPI application
/frontend  — React + Vite application
/ml        — ML pipeline scripts and artifacts
  /ml/artifacts  — trained model files (model.json, explainer.pkl, metrics.json)
```

---

## Coding Conventions

- **Secrets**: All secrets (API keys, DB URLs, JWT secret) come from environment variables — never hard-coded.
- **Caching**: All external data pulls are cached in Postgres. The app never calls a third-party API synchronously on every user request.
- **Predictions**: Every model prediction returned by the API must include a SHAP-based explanation payload alongside the risk score — never return a bare risk number.
- **Background jobs**: Anything resembling a background job must run as a scheduled GitHub Actions workflow, not a long-running Render worker service, to stay within free instance-hours.
- **Python style**: Follow PEP 8. Use type hints on all function signatures.
- **React style**: Functional components with hooks. No class components.

---

## Free-Tier Constraints (design around these — do not fight them)

### Render (Backend)
- Free web services **sleep after 15 minutes of inactivity** and take ~60 seconds to wake.
- The frontend **must** show a "waking up the server" loading state (via `ColdStartBanner`) on the first request after idle.
- 750 instance-hours/month shared across all services in the workspace — keep it to one web service.

### Neon (Database)
- Compute suspends on inactivity; the first query after idle will have a brief reconnect delay — this is normal and not data loss.
- Storage cap on free tier — fine for this project's data volumes.
- The app must tolerate the brief reconnect delay gracefully (use connection pooling with retry).

### Vercel (Frontend)
- Free Hobby tier. No special constraints for a static SPA.

### No Redis / No paid queue
- Do not introduce Redis, Celery, or any long-running worker.
- Use GitHub Actions cron jobs for scheduled data ingestion.

---

## Free Data Sources

| Data | Source | Notes |
|------|--------|-------|
| Climate (rainfall, temp, humidity) | [Open-Meteo API](https://open-meteo.com) | No API key required |
| Malaria incidence / prevalence | [Malaria Atlas Project (MAP)](https://malariaatlas.org) | Open geospatial data and API |
| Population density | [WorldPop](https://www.worldpop.org) | Free, open, gridded datasets for Africa |
| Map tiles | [OpenStreetMap](https://www.openstreetmap.org) | Free tile usage, no billing |
| Health burden context | [WHO Global Health Observatory API](https://www.who.int/data/gho) | Free, no key required |

---

## Environment Variables

### Backend (set on Render)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Neon Postgres connection string |
| `JWT_SECRET` | Random secret for signing tokens |
| `CORS_ORIGINS` | Vercel frontend URL(s) |
| `MODEL_ARTIFACT_PATH` | Path to committed model files (or GitHub Release download URL) |

### Frontend (set on Vercel)

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Render backend's public URL |

---

## Database Schema

```sql
-- Supported geographic regions
CREATE TABLE regions (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Raw ingested indicators — one row per region/date/source
CREATE TABLE region_indicators (
    id SERIAL PRIMARY KEY,
    region_id INTEGER REFERENCES regions(id),
    date DATE NOT NULL,
    rainfall_mm DOUBLE PRECISION,
    avg_temp_c DOUBLE PRECISION,
    humidity_pct DOUBLE PRECISION,
    population_density DOUBLE PRECISION,
    historical_cases INTEGER,
    source TEXT NOT NULL,
    UNIQUE (region_id, date, source)
);

-- Model predictions — one row per region/date the model was run
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    region_id INTEGER REFERENCES regions(id),
    predicted_at TIMESTAMPTZ DEFAULT now(),
    risk_score DOUBLE PRECISION NOT NULL,
    risk_category TEXT NOT NULL,
    model_version TEXT NOT NULL,
    shap_explanation JSONB NOT NULL
);

-- Users (health workers, admins)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'health_worker',
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## API Contract

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/auth/login` | None | Exchange email/password for JWT |
| `GET` | `/regions` | JWT | List all supported regions |
| `GET` | `/regions/{id}/predictions/latest` | JWT | Latest risk score + SHAP explanation |
| `GET` | `/regions/{id}/predictions/history` | JWT | Time-series of past predictions |
| `POST` | `/regions/{id}/predict` | JWT (admin) | Trigger a fresh prediction from latest stored indicators |
| `GET` | `/health` | None | Liveness check; used by frontend to detect cold-start wake-up |

---

## ML Pipeline (`/ml`)

1. **`ml/fetch_training_data.py`** — pulls historical data from Postgres into a Pandas DataFrame.
2. **`ml/train.py`** — trains an XGBoost classifier on historical indicators → outbreak risk; saves `ml/artifacts/model.json` and `ml/artifacts/explainer.pkl`.
3. **`ml/evaluate.py`** — runs train/test split evaluation (precision, recall, AUC); writes `ml/artifacts/metrics.json`.
4. The FastAPI backend loads `model.json` and `explainer.pkl` at startup from `ml/artifacts/`.

---

## Frontend Structure

```
frontend/src/
  pages/
    Login.jsx          — login form wired to /auth/login
    Dashboard.jsx      — map + sortable region risk table
    RegionDetail.jsx   — SHAP explanation view + history chart
  components/
    RiskMap.jsx        — OpenStreetMap tiles, no API key required
    ColdStartBanner.jsx — shown while backend is waking from Render sleep
  lib/
    api.js             — fetch wrapper: attaches JWT, retries once on 502/503
```

---

## Suggested Build Order

| Session | Phase | Focus |
|---------|-------|-------|
| 1 | Foundations + Data Ingestion | Scaffold repo, set up Neon, run migrations, get real data flowing into Postgres |
| 2 | ML Pipeline | Train on real ingested data, commit artifacts |
| 3 | Backend API | Wire trained model into live endpoints |
| 4 | Frontend | Build against the working API |
| 5 | Deployment Hardening | Env vars, CORS, backups, README |

---

## Cost Control Notes

Everything fits inside free tiers as long as this stays a single-service MVP:
- No Redis/worker tier.
- One Render web service.
- Neon free tier is permanent (unlike Render's built-in Postgres, which deletes after 30 days).

**First paid upgrade worth making** (if real daily users arrive): Render's paid web service tier to eliminate the sleep/cold-start behavior — not the database.

---

## Key Gotchas for Future Contributors

- **Render sleeps after 15 min idle** — the `ColdStartBanner` component handles this gracefully. Do not remove it.
- **Neon suspends compute on inactivity** — brief reconnect delay on first query is normal, not a bug.
- **Ingestion is a GitHub Actions cron**, not a Render service — do not move it to a long-running process without upgrading the Render plan.
- **Every prediction response must include `shap_explanation`** — this is a hard requirement, not optional.
