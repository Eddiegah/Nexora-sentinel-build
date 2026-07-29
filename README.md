# Nexora Sentinel

> AI-powered malaria outbreak risk prediction and public-health intelligence platform for Africa.

## Architecture

```
[Open-Meteo]  [Malaria Atlas Project]  [WorldPop]
      \                  |                  /
       ──────────────────┼─────────────────
                         ↓
           GitHub Actions cron (ingest.yml)
                         │
                         ↓
             Neon Postgres (free tier)
                         │
                         ↓
          FastAPI backend  ←── XGBoost + SHAP
           (Render free)         (ml/artifacts/)
                         │
                         ↓
         React + Vite frontend (Vercel free)
                         │
                         ↓
            Health workers / Policymakers
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- A [Neon](https://neon.tech) Postgres database (free tier)

### 1. Clone & configure

```bash
git clone https://github.com/your-org/nexora-sentinel.git
cd nexora-sentinel
```

Copy and fill in your secrets:
```bash
cp backend/.env.example backend/.env
# edit backend/.env with your DATABASE_URL and JWT_SECRET

cp frontend/.env.example frontend/.env.local
# edit frontend/.env.local with VITE_API_BASE_URL=http://localhost:8000
```

### 2. Run database migrations

```bash
psql $DATABASE_URL -f backend/migrations/001_initial_schema.sql
```

Generate a real bcrypt hash for the admin user, then run:
```bash
python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('your-password'))"
# paste hash into backend/migrations/002_seed_admin_user.sql, then:
psql $DATABASE_URL -f backend/migrations/002_seed_admin_user.sql
```

### 3. Ingest data

```bash
cd <repo root>
pip install -r ml/requirements.txt
python -m ml.ingest.ingest --days-back 90
```

### 4. Train the model

```bash
python ml/fetch_training_data.py
python ml/train.py
python ml/evaluate.py
```

Artifacts are written to `ml/artifacts/`. Commit them (or attach as a GitHub Release asset).

### 5. Start the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
# API running at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
# App running at http://localhost:5173
```

---

## Deployment

### Backend → Render

1. Create a new **Web Service** on [Render](https://render.com).
2. Connect your GitHub repo.
3. Build command: `pip install -r backend/requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Set environment variables: `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `MODEL_ARTIFACT_PATH`

### Frontend → Vercel

1. Import the repo on [Vercel](https://vercel.com).
2. Set root directory to `frontend`.
3. Set `VITE_API_BASE_URL` to your Render service URL.

### Scheduled ingestion → GitHub Actions

Add `DATABASE_URL` to your GitHub repo secrets.  
The `ingest.yml` workflow runs automatically at 02:00 UTC daily.

---

## ⚠️ Free-Tier Gotchas

| Service | Behavior | How we handle it |
|---------|----------|-----------------|
| **Render** | Web service sleeps after **15 min idle**; ~60s cold start | `ColdStartBanner` component polls `/health` and shows a loading state |
| **Neon** | Compute suspends on inactivity; brief reconnect delay on first query | `pool_pre_ping=True` + exponential backoff in `get_db()` |
| **GitHub Actions** | Ingestion runs as cron, not a long-lived process | No Redis / no Celery — keeps within Render's free 750 instance-hours |

The first paid upgrade worth making (once you have real daily users) is **Render's paid web service tier** to eliminate the sleep behavior — not the database.

---

## Environment Variables Reference

### Backend (Render)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Neon Postgres connection string |
| `JWT_SECRET` | Secret for signing JWTs |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins |
| `MODEL_ARTIFACT_PATH` | Path to `ml/artifacts/` relative to repo root |

### Frontend (Vercel)

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Render backend public URL |

---

## Project Structure

```
nexora-sentinel/
├── backend/
│   ├── app/
│   │   ├── core/          # config, database, security, ml_loader
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── routers/       # auth, regions, predictions
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   └── main.py
│   ├── migrations/        # SQL migration files
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/    # RiskMap, ColdStartBanner
│   │   ├── hooks/         # useAuth
│   │   ├── lib/           # api.js
│   │   └── pages/         # Login, Dashboard, RegionDetail
│   ├── package.json
│   └── .env.example
├── ml/
│   ├── ingest/            # open_meteo_client, malaria_atlas_client, worldpop_client, ingest.py
│   ├── artifacts/         # model.json, explainer.pkl, metrics.json (generated)
│   ├── fetch_training_data.py
│   ├── train.py
│   └── evaluate.py
└── .github/
    └── workflows/
        ├── ingest.yml     # daily data ingestion
        └── backup.yml     # weekly Postgres backup
```
