# Nexora Sentinel — Deployment Checklist
# Complete this top to bottom. Each step is < 5 minutes.
# Every value you need to copy-paste is pre-filled below.

---

## ✅ STEP 1 — Neon (database) — ~3 min

1. Open: https://neon.tech → Sign up with GitHub (free, no card)
2. Click "New Project"
   - Name: `nexora-sentinel`
   - Postgres version: 16
   - Region: pick closest to you
3. On the dashboard click **"Connect"** (top right)
   - Toggle "Connection pooling" → OFF
   - Copy the full connection string (starts with `postgresql://`)
   - **Paste it here so you don't lose it:** `DATABASE_URL=___________________`

4. Click **"SQL Editor"** in the left sidebar
5. Paste this entire block and click Run:

--- PASTE INTO NEON SQL EDITOR ---
(Contents of backend/migrations/001_initial_schema.sql — copy from the file)
--- END ---

6. Clear the editor, paste this block and click Run:

--- PASTE INTO NEON SQL EDITOR ---
(Contents of backend/migrations/002_seed_admin_user.sql — copy from the file)
--- END ---

✓ Database is ready. Admin login: admin@nexora-sentinel.local / Sentinel2024!

---

## ✅ STEP 2 — Run setup script (trains model) — ~5 min

Open PowerShell in C:\Projects\Nexora-sentinel and run:

```powershell
.\scripts\setup_local.ps1 -DatabaseUrl "postgresql://YOUR_NEON_URL_HERE"
```

This installs deps, ingests data, trains the XGBoost model, and pushes
ml/artifacts/ to GitHub. Render will auto-redeploy with the model loaded.

---

## ✅ STEP 3 — Render (backend API) — ~5 min

1. Open: https://render.com → Sign up with GitHub (free)
2. Click "New +" → "Web Service"
3. Click "Connect" next to: Eddiegah/Nexora-sentinel-build
4. Fill in the form — copy-paste exactly:

   | Field            | Value                                              |
   |------------------|----------------------------------------------------|
   | Name             | nexora-sentinel-api                                |
   | Region           | Oregon (US West)                                   |
   | Branch           | main                                               |
   | Root Directory   | backend                                            |
   | Runtime          | Python 3                                           |
   | Build Command    | pip install -r requirements.txt                    |
   | Start Command    | uvicorn app.main:app --host 0.0.0.0 --port $PORT  |
   | Instance Type    | Free                                               |

5. Scroll to "Environment Variables" → Add these one by one:

   | Key                  | Value                                              |
   |----------------------|----------------------------------------------------|
   | DATABASE_URL         | [your Neon connection string from Step 1]          |
   | JWT_SECRET           | 08bbfab93032e9268ac18e4009072398e729fd294e7e98ec7141cac906700a0d |
   | CORS_ORIGINS         | https://nexora-sentinel.vercel.app                 |
   | MODEL_ARTIFACT_PATH  | ../ml/artifacts                                    |

6. Click "Create Web Service" → wait ~3 min for first deploy
7. Copy your URL: https://nexora-sentinel-api.onrender.com
   - Test: https://nexora-sentinel-api.onrender.com/health
   - Expected: {"status":"ok","model_loaded":true,...}

---

## ✅ STEP 4 — Vercel (frontend) — ~3 min

1. Open: https://vercel.com → Sign up with GitHub (free)
2. Click "Add New" → "Project"
3. Click "Import" next to: Eddiegah/Nexora-sentinel-build
4. Configure:

   | Field             | Value         |
   |-------------------|---------------|
   | Framework Preset  | Vite          |
   | Root Directory    | frontend      |
   | Build Command     | npm run build |
   | Output Directory  | dist          |

5. Add Environment Variable:

   | Key               | Value                                              |
   |-------------------|----------------------------------------------------|
   | VITE_API_BASE_URL | https://nexora-sentinel-api.onrender.com           |

6. Click "Deploy" → wait ~1 min
7. Copy your URL: https://nexora-sentinel-XXXXX.vercel.app

---

## ✅ STEP 5 — Update CORS on Render — 1 min

1. Go back to Render → nexora-sentinel-api → Environment
2. Update CORS_ORIGINS to your exact Vercel URL:
   CORS_ORIGINS = https://nexora-sentinel-XXXXX.vercel.app
3. Render auto-redeploys (takes ~30 sec)

---

## ✅ STEP 6 — GitHub Actions secret — 1 min

1. Go to: https://github.com/Eddiegah/Nexora-sentinel-build
2. Settings → Secrets and variables → Actions → "New repository secret"
3. Add:
   Name:  DATABASE_URL
   Value: [your Neon connection string from Step 1]
4. Click "Add secret"

The daily ingestion cron (02:00 UTC) and weekly backup now run automatically.
To trigger immediately: Actions → "Data Ingestion (scheduled)" → "Run workflow" → days_back: 365

---

## ✅ STEP 7 — Seed predictions — 2 min

Once Render is live and model is loaded, run this in PowerShell to generate
risk predictions for all 10 seeded regions:

```powershell
$RENDER_URL = "https://nexora-sentinel-api.onrender.com"
$body = '{"email":"admin@nexora-sentinel.local","password":"Sentinel2024!"}'
$token = (Invoke-RestMethod -Uri "$RENDER_URL/auth/login" -Method POST -Body $body -ContentType "application/json").access_token
$headers = @{ Authorization = "Bearer $token" }
1..10 | ForEach-Object {
    $r = Invoke-RestMethod -Uri "$RENDER_URL/regions/$_/predict" -Method POST -Headers $headers
    Write-Host "Region $_ : $($r.risk_category) ($([math]::Round($r.risk_score*100,1))%)"
}
```

---

## Summary of credentials

| Item                  | Value                                                        |
|-----------------------|--------------------------------------------------------------|
| Admin email           | admin@nexora-sentinel.local                                  |
| Admin password        | Sentinel2024!  ← change after first login                   |
| JWT_SECRET            | 08bbfab93032e9268ac18e4009072398e729fd294e7e98ec7141cac906700a0d |
| GitHub repo           | https://github.com/Eddiegah/Nexora-sentinel-build            |
| API docs (after deploy) | https://nexora-sentinel-api.onrender.com/docs              |
