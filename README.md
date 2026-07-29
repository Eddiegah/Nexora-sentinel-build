<div align="center">

# 🌍 Nexora Sentinel

### AI-powered malaria outbreak risk prediction for Africa

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0-FF6600?style=for-the-badge&logo=python&logoColor=white)](https://xgboost.readthedocs.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech)
[![Deployed on Render](https://img.shields.io/badge/API-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com)
[![Deployed on Vercel](https://img.shields.io/badge/Frontend-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/Eddiegah/Nexora-sentinel-build/actions)

<br/>

> **Nexora Sentinel** predicts malaria outbreak risk across 10 major African cities using real climate data, historical case counts, and an XGBoost model with SHAP explainability — surfaced on a live dashboard for health workers and policymakers.

<br/>

![Nexora Sentinel Dashboard Preview](https://raw.githubusercontent.com/Eddiegah/Nexora-sentinel-build/main/.github/assets/dashboard-preview.png)

</div>

---

## ✨ What it does

| Feature | Description |
|---------|-------------|
| 🗺️ **Risk Map** | Interactive OpenStreetMap showing outbreak risk levels across Africa, colored by severity |
| 📊 **Risk Scores** | XGBoost model predicts outbreak probability (0–100%) per region, categorized as Low / Medium / High |
| 🧠 **SHAP Explainability** | Every prediction comes with a ranked breakdown of contributing factors — no black box |
| 📈 **Historical Trends** | Time-series charts showing how each region's risk has evolved over time |
| 🔐 **JWT Auth** | Secure login for health workers and admins — no third-party auth service needed |
| ⏰ **Auto Ingestion** | GitHub Actions cron fetches fresh climate + disease data from open APIs every day |
| 💤 **Cold-Start UX** | Smart "waking up the server" banner handles Render's free-tier sleep gracefully |

---

## 🏗️ Architecture

```
  Open-Meteo API          WHO GHO API           WorldPop
  (climate data)       (malaria incidence)    (population)
       │                      │                    │
       └──────────────────────┴────────────────────┘
                              │
                    GitHub Actions Cron
                    (daily ingestion job)
                              │
                              ▼
                    ┌─────────────────┐
                    │  Neon Postgres  │  ← free tier, serverless
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  FastAPI / Render│  ← free web service
                    │  XGBoost + SHAP │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ React + Vite    │  ← free Vercel hobby
                    │ Vercel          │
                    └─────────────────┘
                             │
                    Health workers & Policymakers
```

---

## 🧬 ML Pipeline

```
region_indicators (Postgres)
        │
        ▼
ml/fetch_training_data.py    ← pulls features into a DataFrame
        │
        ▼
ml/train.py                  ← XGBoost classifier, scale_pos_weight
        │                       for class imbalance
        ├── ml/artifacts/model.json
        ├── ml/artifacts/explainer.pkl
        └── ml/artifacts/metrics.json
        │
        ▼
ml/evaluate.py               ← AUC, Precision, Recall, F1
        │
        ▼
FastAPI loads artifacts at startup
Every /predict response includes full SHAP explanation payload
```

**Model performance on bootstrap dataset:**

| Metric | Score |
|--------|-------|
| AUC | 1.000 |
| Precision | 1.000 |
| Recall | 1.000 |
| F1 | 1.000 |

> Metrics will reflect real-world complexity once the GitHub Actions ingestion cron accumulates months of live Open-Meteo + WHO data.

---

## 🌐 Tracked Regions

| # | City | Country |
|---|------|---------|
| 1 | Kampala | Uganda |
| 2 | Nairobi | Kenya |
| 3 | Dar es Salaam | Tanzania |
| 4 | Accra | Ghana |
| 5 | Lagos | Nigeria |
| 6 | Kinshasa | DRC |
| 7 | Lusaka | Zambia |
| 8 | Lilongwe | Malawi |
| 9 | Maputo | Mozambique |
| 10 | Antananarivo | Madagascar |

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | React 18 + Vite 5 | Fast SPA, Vercel-native |
| Mapping | React-Leaflet + OpenStreetMap | Free tiles, no API key |
| Charts | Chart.js + react-chartjs-2 | Lightweight, beautiful |
| Backend | FastAPI + Uvicorn | Async, auto-docs at `/docs` |
| Database | PostgreSQL on Neon | Free tier, no expiry, serverless |
| ORM | SQLAlchemy 2.0 | Type-safe, async-ready |
| ML Model | XGBoost 2.0 | Best-in-class gradient boosting |
| Explainability | SHAP 0.44 | TreeExplainer, feature attribution |
| Auth | JWT (python-jose + passlib) | No paid auth service |
| Rate Limiting | slowapi | Protects free-tier `/auth/login` |
| Ingestion | GitHub Actions cron | Free, no long-running worker |
| Backend hosting | Render (free) | Auto-deploy from GitHub |
| Frontend hosting | Vercel (free) | CDN-edge, instant deploys |

---

## 📁 Project Structure

```
nexora-sentinel/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── core/               # config, database, security, ml_loader
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── routers/            # auth, regions, predictions
│   │   └── schemas/            # Pydantic request/response schemas
│   ├── migrations/             # SQL migration files
│   └── requirements.txt
│
├── frontend/                   # React + Vite SPA
│   └── src/
│       ├── components/         # RiskMap, ColdStartBanner, NavBar
│       ├── hooks/              # useAuth
│       ├── lib/                # api.js — JWT fetch wrapper
│       └── pages/              # Login, Dashboard, RegionDetail
│
├── ml/                         # ML pipeline
│   ├── ingest/                 # Open-Meteo, WHO GHO, WorldPop clients
│   ├── artifacts/              # model.json, explainer.pkl, metrics.json
│   ├── fetch_training_data.py
│   ├── train.py
│   ├── evaluate.py
│   └── generate_synthetic_training_data.py
│
└── .github/workflows/
    ├── ingest.yml              # Daily data ingestion (02:00 UTC)
    ├── backup.yml              # Weekly Postgres backup (Sunday 03:00 UTC)
    └── ci.yml                  # Build check on every push
```

---

## 🚀 Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- A [Neon](https://neon.tech) Postgres database (free)

### 1. Clone & configure

```bash
git clone https://github.com/Eddiegah/Nexora-sentinel-build.git
cd Nexora-sentinel-build

cp backend/.env.example backend/.env
# Edit backend/.env — add your DATABASE_URL and JWT_SECRET

cp frontend/.env.example frontend/.env.local
# Edit frontend/.env.local — set VITE_API_BASE_URL=http://localhost:8000
```

### 2. Run migrations

Paste `backend/migrations/001_initial_schema.sql` then `002_seed_admin_user.sql`
into the [Neon SQL Editor](https://console.neon.tech).

### 3. Bootstrap data + train model

```bash
pip install -r ml/requirements.txt

# Generate synthetic bootstrap data and populate Postgres
python ml/generate_synthetic_training_data.py

# Train XGBoost model
python ml/train.py

# Evaluate
python ml/evaluate.py
```

### 4. Start the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (interactive API docs)
```

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

**Default login:** `admin@nexora-sentinel.local` / `Sentinel2024!`

---

## 🔌 API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/health` | None | Liveness check — used by frontend cold-start detection |
| `POST` | `/auth/login` | None | Get JWT token |
| `GET` | `/regions` | JWT | List all tracked regions |
| `GET` | `/regions/{id}` | JWT | Get single region details |
| `GET` | `/regions/{id}/predictions/latest` | JWT | Latest risk score + SHAP explanation |
| `GET` | `/regions/{id}/predictions/history` | JWT | Time-series of past predictions |
| `POST` | `/regions/{id}/predict` | JWT (admin) | Trigger fresh prediction |

Full interactive docs at **`/docs`** when the API is running.

---

## ⚠️ Free-Tier Notes

| Service | Behavior | How we handle it |
|---------|----------|-----------------|
| **Render** | Sleeps after 15 min idle, ~60s cold start | `ColdStartBanner` polls `/health` and shows a loading state |
| **Neon** | Compute suspends on inactivity, brief reconnect | `pool_pre_ping=True` + exponential back-off in `get_db()` |
| **Ingestion** | Runs as GitHub Actions cron, not a Render worker | Stays within free 750 instance-hours/month |

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Commit your changes: `git commit -m 'feat: add your feature'`
4. Push and open a PR

Please follow the conventions in `.kiro/steering/nexora-sentinel.md` — every prediction response must include a SHAP explanation payload.

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ❤️ for African public health intelligence

**[Live Demo](https://nexora-sentinel.vercel.app)** · **[API Docs](https://nexora-sentinel-api.onrender.com/docs)** · **[Report a Bug](https://github.com/Eddiegah/Nexora-sentinel-build/issues)**

</div>
