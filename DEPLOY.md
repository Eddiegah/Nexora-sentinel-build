# Nexora Sentinel — Complete Deployment Guide

Everything you need to go from "code on GitHub" to a live, working application.

---

## Step 1 — Neon Postgres (database, ~5 min)

1. Go to **https://neon.tech** → Sign up free (GitHub login works)
2. Click **"New Project"** → name it `nexora-sentinel` → region: closest to you → Create
3. On the project dashboard, click **"Connect"** (top right)
4. Select: Branch `main`, Role `neondb_owner`, Database `neondb`
5. Toggle **"Connection pooling" OFF** (direct connection is better for migrations)
6. Copy the full connection string — it looks like:
   ```
   postgresql://neondb_owner:xxxx@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
7. **Save this string** — you'll need it in Steps 2, 3, and 4

### Run migrations against Neon

You need `psql` installed locally, OR you can use the Neon SQL Editor in the browser:

**Option A — Neon SQL Editor (no local tools needed):**
1. In your Neon project, click **"SQL Editor"** in the left sidebar
2. Paste the contents of `backend/migrations/001_initial_schema.sql` → Run
3. Paste the contents of `backend/migrations/002_seed_admin_user.sql` → Run

**Option B — psql locally:**
```bash
psql "postgresql://neondb_owner:xxxx@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require" \
  -f backend/migrations/001_initial_schema.sql

psql "postgresql://neondb_owner:xxxx@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require" \
  -f backend/migrations/002_seed_admin_user.sql
```

Default admin credentials after migration:
- Email: `admin@nexora-sentinel.local`
- Password: `Sentinel2024!`
- **Change this password before sharing the URL publicly** (see migrations/002 file)

---

## Step 2 — Render (backend, ~10 min)

1. Go to **https://render.com** → Sign up free → Connect GitHub
2. Click **"New +"** → **"Web Service"**
3. Connect repository: select **`Eddiegah/Nexora-sentinel-build`**
4. Configure the service:
   | Field | Value |
   |-------|-------|
   | Name | `nexora-sentinel-api` |
   | Region | Oregon (or closest) |
   | Branch | `main` |
   | Root Directory | `backend` |
   | Runtime | `Python 3` |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Instance Type | **Free** |

5. Scroll to **"Environment Variables"** — add all of these:

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | Your Neon connection string from Step 1 |
   | `JWT_SECRET` | Any long random string, e.g. run: `openssl rand -hex 32` |
   | `CORS_ORIGINS` | `https://nexora-sentinel.vercel.app` (update after Vercel deploy) |
   | `MODEL_ARTIFACT_PATH` | `../ml/artifacts` |

6. Click **"Create Web Service"** — first deploy takes ~3 minutes
7. Once deployed, copy your service URL: `https://nexora-sentinel-api.onrender.com`
   - Test it: visit `https://nexora-sentinel-api.onrender.com/health`
   - You should see: `{"status":"ok","model_loaded":false,"model_version":null}`
   - `model_loaded: false` is expected until we train the model in Step 4

> **Note:** The free tier sleeps after 15 minutes idle. The first request after sleep takes ~60 seconds. The frontend's ColdStartBanner handles this automatically.

---

## Step 3 — Vercel (frontend, ~5 min)

1. Go to **https://vercel.com** → Sign up free → Connect GitHub
2. Click **"Add New"** → **"Project"**
3. Import **`Eddiegah/Nexora-sentinel-build`**
4. Configure:
   | Field | Value |
   |-------|-------|
   | Framework Preset | `Vite` |
   | Root Directory | `frontend` |
   | Build Command | `npm run build` |
   | Output Directory | `dist` |

5. Add **Environment Variable**:
   | Key | Value |
   |-----|-------|
   | `VITE_API_BASE_URL` | `https://nexora-sentinel-api.onrender.com` (your Render URL) |

6. Click **"Deploy"** — takes ~1 minute
7. Copy your Vercel URL: `https://nexora-sentinel-xxx.vercel.app`

### Update CORS on Render

Go back to Render → your service → **Environment** → update:
```
CORS_ORIGINS = https://nexora-sentinel-xxx.vercel.app
```
Render will auto-redeploy.

---

## Step 4 — GitHub Actions secrets (ingestion + backup)

1. Go to **https://github.com/Eddiegah/Nexora-sentinel-build** → **Settings** → **Secrets and variables** → **Actions**
2. Click **"New repository secret"** — add:

   | Name | Value |
   |------|-------|
   | `DATABASE_URL` | Your Neon connection string from Step 1 |

This enables:
- **Daily ingestion** (`.github/workflows/ingest.yml`) — runs at 02:00 UTC, fetches real climate/disease data
- **Weekly backup** (`.github/workflows/backup.yml`) — runs Sunday 03:00 UTC, uploads pg_dump as artifact

To trigger the first ingestion manually right now:
1. Go to your repo → **Actions** → **"Data Ingestion (scheduled)"**
2. Click **"Run workflow"** → set days_back to `365` → Run
3. This populates your database with a year of climate + case data

---

## Step 5 — Train the ML model locally

Once the ingestion job has run (Step 4), train the model locally and push the artifacts:

```bash
# Install ML dependencies
pip install -r ml/requirements.txt

# Set your DATABASE_URL
# Windows PowerShell:
$env:DATABASE_URL = "postgresql://neondb_owner:xxxx@ep-xxx.neon.tech/neondb?sslmode=require"
# Mac/Linux:
export DATABASE_URL="postgresql://neondb_owner:xxxx@ep-xxx.neon.tech/neondb?sslmode=require"

# Fetch training data
python ml/fetch_training_data.py

# Train the model (saves to ml/artifacts/)
python ml/train.py

# Evaluate and log metrics
python ml/evaluate.py

# Commit and push the artifacts
git add ml/artifacts/model.json ml/artifacts/explainer.pkl ml/artifacts/metrics.json
git commit -m "feat: add trained model artifacts"
git push
```

Render will auto-redeploy when you push. After the redeploy, `/health` will return `model_loaded: true`.

To generate predictions for all regions, call the predict endpoint for each:
```bash
# First get a token
TOKEN=$(curl -s -X POST https://nexora-sentinel-api.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@nexora-sentinel.local","password":"Sentinel2024!"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Trigger prediction for region 1 (repeat for 1-10)
curl -X POST https://nexora-sentinel-api.onrender.com/regions/1/predict \
  -H "Authorization: Bearer $TOKEN"
```

---

## Summary — URLs after deployment

| Service | URL |
|---------|-----|
| **Frontend** | `https://nexora-sentinel-xxx.vercel.app` |
| **API** | `https://nexora-sentinel-api.onrender.com` |
| **API Docs** | `https://nexora-sentinel-api.onrender.com/docs` |
| **Health check** | `https://nexora-sentinel-api.onrender.com/health` |
| **GitHub repo** | `https://github.com/Eddiegah/Nexora-sentinel-build` |

---

## Troubleshooting

**Backend returns 503 on `/predict`**
→ Model not loaded. Complete Step 5 and push artifacts.

**Frontend shows blank map, no regions**
→ Either the backend is waking up (wait 60s), or the ingestion hasn't run yet (Step 4).

**Login fails with 401**
→ Migration 002 wasn't run, or the placeholder hash is still there. Re-run the SQL.

**CORS error in browser console**
→ `CORS_ORIGINS` on Render doesn't match your exact Vercel URL. Update it (no trailing slash).

**Neon connection timeout on first request**
→ Normal — Neon's free compute suspends on inactivity. The retry logic in `database.py` handles this with up to 3 attempts and exponential back-off.
