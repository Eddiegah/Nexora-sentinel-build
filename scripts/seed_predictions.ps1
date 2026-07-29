# Nexora Sentinel — Seed predictions for all 10 regions
# Run this AFTER Render is deployed and the model is loaded.
#
# Usage:
#   .\scripts\seed_predictions.ps1 -RenderUrl "https://nexora-sentinel-api.onrender.com"
#
# It will:
#   1. Wake up the Render instance (may take ~60s on free tier)
#   2. Login as admin and get a JWT
#   3. Trigger POST /regions/{id}/predict for all 10 regions
#   4. Print each region's risk score and category

param(
    [Parameter(Mandatory=$true)]
    [string]$RenderUrl
)

$RenderUrl = $RenderUrl.TrimEnd("/")

Write-Host "`n=== Nexora Sentinel — Seeding Predictions ===" -ForegroundColor Cyan
Write-Host "API: $RenderUrl`n"

# ── Step 1: Wake up the server ───────────────────────────────────────────────
Write-Host "Waking up the server (may take up to 60 seconds on free tier)..." -ForegroundColor Yellow
$maxAttempts = 20
$attempt = 0
$awake = $false
while ($attempt -lt $maxAttempts -and -not $awake) {
    try {
        $health = Invoke-RestMethod -Uri "$RenderUrl/health" -Method GET -TimeoutSec 10 -ErrorAction Stop
        Write-Host "✓ Server is awake. Model loaded: $($health.model_loaded), version: $($health.model_version)" -ForegroundColor Green
        $awake = $true
    } catch {
        $attempt++
        Write-Host "  Waiting... (attempt $attempt/$maxAttempts)" -ForegroundColor Gray
        Start-Sleep -Seconds 5
    }
}

if (-not $awake) {
    Write-Host "✗ Server did not wake up after $($maxAttempts * 5) seconds. Check Render dashboard." -ForegroundColor Red
    exit 1
}

# ── Step 2: Login ────────────────────────────────────────────────────────────
Write-Host "`nLogging in as admin..." -ForegroundColor Yellow
$loginBody = '{"email":"admin@nexora-sentinel.local","password":"Sentinel2024!"}'
try {
    $loginResp = Invoke-RestMethod -Uri "$RenderUrl/auth/login" `
        -Method POST `
        -Body $loginBody `
        -ContentType "application/json" `
        -ErrorAction Stop
    $token = $loginResp.access_token
    Write-Host "✓ Login successful" -ForegroundColor Green
} catch {
    Write-Host "✗ Login failed: $_" -ForegroundColor Red
    Write-Host "  Make sure migration 002 was run and credentials are correct." -ForegroundColor Yellow
    exit 1
}

$headers = @{ Authorization = "Bearer $token" }

# ── Step 3: Trigger predictions for all 10 regions ──────────────────────────
Write-Host "`nGenerating predictions for all 10 regions..." -ForegroundColor Yellow

$regions = @(
    @{id=1;  name="Kampala";         country="Uganda"},
    @{id=2;  name="Nairobi";         country="Kenya"},
    @{id=3;  name="Dar es Salaam";   country="Tanzania"},
    @{id=4;  name="Accra";           country="Ghana"},
    @{id=5;  name="Lagos";           country="Nigeria"},
    @{id=6;  name="Kinshasa";        country="DRC"},
    @{id=7;  name="Lusaka";          country="Zambia"},
    @{id=8;  name="Lilongwe";        country="Malawi"},
    @{id=9;  name="Maputo";          country="Mozambique"},
    @{id=10; name="Antananarivo";    country="Madagascar"}
)

$categoryColors = @{ low = "Green"; medium = "Yellow"; high = "Red" }

foreach ($region in $regions) {
    try {
        $pred = Invoke-RestMethod `
            -Uri "$RenderUrl/regions/$($region.id)/predict" `
            -Method POST `
            -Headers $headers `
            -ErrorAction Stop

        $score = [math]::Round($pred.risk_score * 100, 1)
        $cat = $pred.risk_category
        $color = $categoryColors[$cat] ?? "White"
        Write-Host ("  ✓ {0,-20} {1,-12} {2,6}%  [{3}]" -f `
            "$($region.name),", $region.country, $score, $cat.ToUpper()) `
            -ForegroundColor $color
    } catch {
        Write-Host "  ✗ $($region.name): $_" -ForegroundColor Red
    }
}

Write-Host "`n=== Done! Open your Vercel URL to see the dashboard. ===" -ForegroundColor Cyan
Write-Host "API docs: $RenderUrl/docs" -ForegroundColor White
