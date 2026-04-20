# Project: Agricultural Micro-Insurance Trigger Engine

## Who This Is For
This file is the single source of truth for any Claude session working on this project.
It explains what the project is, what is fully built, what is pending, what credentials are needed, and what must never be changed without understanding the implications.

---

## What This Project Is
A **parametric micro-insurance system** for Indian farmers that automatically triggers UPI payouts within 24 hours of a verifiable weather event (flood or drought) — using live satellite + weather data. No claims forms. No adjusters. Fully automated.

**Project owner:** Jignesh (student project — AgriTech + FinTech social impact)
**GitHub:** https://github.com/Pavo321/agri-insurance-engine (account: Pavo321, no collaborators ever)
**Scope:** All India (pilot currently wired for Maharashtra — 20 districts)

---

## The Problem Being Solved
- 70% of Indian farmers have no crop insurance
- Existing PMFBY (govt scheme) claims take 3–6 months to process
- All the data needed to verify weather events already exists (satellites, rain gauges, sensors)
- This project connects that data to an automated payout engine — cutting time from 3 months to 24 hours

---

## How To Run The Project (Quick Start)

```bash
cd /Users/jignesh/Desktop/Tranpal/agri-insurance-engine

# Install dependencies (macOS system Python — use this flag)
pip install streamlit folium streamlit-folium structlog --break-system-packages

# Run the live dashboard (opens at http://localhost:8501)
streamlit run dashboard/app.py

# Run the rules evaluator directly (prints live trigger report)
python -m rules.evaluator

# Test individual data sources
python -m ingestion.open_meteo         # Live rainfall — 20 MH districts
python -m ingestion.modis_flood        # NASA flood granules over Maharashtra
python -m processing.raster.ndvi_pipeline  # NDVI stats from NASA MODIS
```

---

## Architecture — End-to-End Flow (9 Steps)

```
[1] INGEST         Open-Meteo (rainfall) + NASA MODIS (NDVI + flood)
        ↓
[2] STORE          PostGIS (farm polygons) + TimescaleDB (time-series) + S3 (rasters)
        ↓
[3] PROCESS RASTER GDAL + Dask → NDVI % change vs 30-day seasonal baseline
        ↓
[4] FARM MATCH     PySpark spatial join: each farm polygon × satellite pixels
        ↓
[5] RULES CHECK    Python engine evaluates 5 YAML rules hourly → TriggerEvent list
        ↓
[6] CALCULATE      payout_inr = sum_insured × tier_pct, capped at ₹25,000
        ↓
[7] DEDUP          Redis atomic SET NX: SHA-256(farm_id+rule_id+date), 90-day TTL
        ↓
[8] PAY FARMER     UPI AutoPay API → poll for UTR → retry up to 4 hours
        ↓
[9] AUDIT          payout_records table + Streamlit dashboard + Folium map
```

---

## Trigger Rules (YAML — in `rules/definitions/`)

| Rule ID | Condition | Tier | Payout |
|---|---|---|---|
| DROUGHT_RAIN_14D | Rainfall ≤ 20mm over 14 days | Tier 2 | 25% of sum insured |
| FLOOD_RAIN_48H | Rainfall ≥ 200mm in 48 hours | Tier 1 | 40% of sum insured |
| DROUGHT_NDVI_30 | NDVI drops ≥ 30% vs 30-day baseline | Tier 2 | 25% of sum insured |
| FLOOD_MODIS | NASA MODIS flood product detected on farm | Tier 1 | 40% of sum insured |
| DROUGHT_SOIL_VWC | Soil moisture ≤ 15% for 3 consecutive days | Tier 3 | 15% of sum insured |

**Hard cap:** ₹25,000 per event (set in `.env` as `MAX_PAYOUT_PER_EVENT_INR`)
**Sample sum insured:** ₹60,000 per farmer (pilot placeholder — real system reads from policy DB)
**30-day cooldown:** same farm + same rule cannot trigger again within 30 days

---

## Data Sources — What's Live vs Pending

| Source | Status | What It Provides | File |
|---|---|---|---|
| **Open-Meteo** | ✅ LIVE — free, no auth | 14-day + 48h rainfall for all India | `ingestion/open_meteo.py` |
| **NASA MODIS NDVI** (MOD13A2) | ✅ LIVE — needs NASA token | 16-day NDVI composite, 1km, over Maharashtra | `processing/raster/ndvi_pipeline.py` |
| **NASA MODIS Flood** (MCDWD_L3_F2_NRT) | ✅ LIVE — needs NASA token | Real-time flood detection, 250m, 5+ granules/day | `ingestion/modis_flood.py` |
| **IMD Weather** | ❌ BLOCKED — IP whitelisting required | Official govt rainfall data | `ingestion/imd_weather.py` |
| **ISRO Bhuvan NDVI** | ❌ BLOCKED — 24h expiring tokens, wrong API | Higher-res NDVI (360m) | `ingestion/modis_ndvi.py` |
| **IoT Soil Sensors** | ❌ NOT DEPLOYED — MQTT stub only | Soil moisture (VWC%) | `ingestion/soil_moisture.py` (stub) |
| **Fasal Bima / PMFBY** | ❌ NOT INTEGRATED | Farmer enrollment sync | `ingestion/fasal_bima.py` (stub) |

**Why Open-Meteo instead of IMD:** IMD requires IP whitelisting. Jignesh's ISP assigns dynamic IPs (43.241.194.x range) — whitelisting is impossible. Open-Meteo provides ERA5 + ECMWF data (same quality used internally by PMFBY).

**Why NASA MODIS instead of ISRO Bhuvan:** ISRO Bhuvan's public API only provides routing/location services with 24-hour expiring tokens — not NDVI raster data. NASA MODIS provides identical NDVI data with a permanent token.

---

## Credentials Needed (`.env` file — never commit this)

The `.env` file lives at `agri-insurance-engine/.env` and is gitignored.

| Variable | Status | How To Get |
|---|---|---|
| `NASA_EARTHDATA_TOKEN` | ✅ Set — expires 2026-06-02 | urs.earthdata.nasa.gov → account: pavo321 → generate token |
| `UPI_MERCHANT_ID` | ❌ Missing | Razorpay sandbox: dashboard.razorpay.com |
| `UPI_API_KEY` | ❌ Missing | Same Razorpay sandbox account |
| `FERNET_KEY` | ❌ Missing | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `POSTGRES_DSN` | Set to localhost default | Change for production DB |
| `REDIS_URL` | Set to localhost default | Change for production Redis |

**To regenerate NASA token:** Go to https://urs.earthdata.nasa.gov → profile → "Generate Token" → paste into `.env`

---

## What Is Fully Built and Working

### Data Ingestion
- `ingestion/open_meteo.py` — fetches live rainfall for 20 Maharashtra districts, computes 14d and 48h rolling sums, evaluates drought/flood thresholds
- `ingestion/modis_flood.py` — searches NASA CMR for MCDWD flood granules over Maharashtra bounding box (72.6,15.6,80.9,22.1)
- `ingestion/modis_ndvi.py` — searches NASA CMR for MOD13A2 NDVI granules, extracts HDF download URLs

### NDVI Processing
- `processing/raster/ndvi_pipeline.py` — fetches MODIS granule metadata, uses seasonal NDVI baseline (MH_NDVI_BASELINE dict by month), computes per-district NDVI stats without GDAL (pilot mode)
- **Pilot note:** Production version would download actual HDF files and use GDAL/Dask for per-pixel NDVI. The current code uses a seasonal baseline + spatial adjustment as a proxy — realistic for demonstration, not survey-grade.

### Rules Engine
- `rules/definitions/*.yaml` — 5 YAML rule files, thresholds tunable without code change
- `rules/loader.py` — parses YAML into Pydantic Rule objects
- `rules/models.py` — TriggerEvent, FarmMetrics, RuleResult Pydantic models
- `rules/engine.py` — RulesEngine.evaluate() → list[TriggerEvent], with cooldown enforcement
- `rules/evaluator.py` — full end-to-end: fetches Open-Meteo + NASA MODIS → evaluates all rules → returns complete report. **Live verified: 40 triggers across 20 districts** (April pre-monsoon — all drought-triggering, correct)

### Payout Pipeline
- `payout/calculator.py` — payout_inr = sum_insured × tier_pct, capped at MAX_PAYOUT_PER_EVENT_INR
- `payout/deduplication.py` — SHA-256(farm_id+rule_id+date) idempotency key, Redis atomic SET NX, 90-day TTL
- `payout/upi_client.py` — Razorpay UPI API wrapper (wired but needs sandbox credentials in .env)
- `payout/pipeline.py` — orchestrates: Redis dedup → calculate → write queued record → UPI call → update ledger

### Registry / Database Models
- `registry/models.py` — SQLAlchemy ORM: Farmer (aadhaar_hash), Farm (PostGIS GEOMETRY), Policy, SensorReading (TimescaleDB hypertable), FarmDailyStat, PayoutRecord
- `db/init_sql/` — PostGIS + TimescaleDB setup SQL, hypertable definitions, spatial indexes
- `alembic/` — 3 migration versions: farmer_registry, timeseries, payout_ledger

### API
- `api/main.py` — FastAPI app
- `api/routers/admin.py` — farmer + farm CRUD
- `api/routers/events.py` — event log, dry-run simulate
- `api/routers/payouts.py` — payout status, retry
- `api/routers/webhooks.py` — HMAC-verified inbound webhooks

### Dashboard
- `dashboard/app.py` — 4-page Streamlit dashboard with live data, animated CSS
  - 📊 Dashboard — KPI metrics, rainfall bar chart, NDVI chart, district status table
  - 🗺️ Map View — Folium interactive map, markers color-coded by drought risk
  - ⚡ Triggers — active trigger events with color-coded rows (drought=orange, flood=blue)
  - 💸 Payouts — payout ledger with SUCCESS/PENDING status, UTR numbers

### Workers
- `workers/celery_app.py` — Celery + Beat schedule: weather every 30min, NDVI daily 03:00, rules hourly, payout poll every 10min

### Tests
- `tests/unit/test_rules_engine.py`
- `tests/unit/test_ndvi.py`
- `tests/unit/test_payout_calculator.py`
- `tests/unit/test_deduplication.py`

---

## What Is NOT Done / Remaining Work

### High Priority
1. **UPI live payout testing** — Add `UPI_MERCHANT_ID` and `UPI_API_KEY` (Razorpay sandbox) to `.env`. The payout pipeline code is complete — it just needs credentials.
2. **PostgreSQL + Redis running locally** — The DB and queue are not running. To start: `docker compose up postgres redis` (docker-compose.yml exists). Without this, the payout pipeline and Celery workers cannot run.
3. **Database migrations** — Once Postgres is running: `alembic upgrade head` to create all tables.

### Medium Priority
4. **GDAL-based NDVI** — The current NDVI uses a seasonal baseline proxy. Production needs: download MODIS HDF files → GDAL reads raster → Dask tiles processing → actual per-pixel NDVI per farm polygon. Files exist (`processing/raster/ndvi.py`, `processing/polygon/zonal_stats.py`) but are stubs.
5. **PySpark farm polygon overlay** — `processing/polygon/spark_overlay.py` — spatial join of farm polygons × satellite pixels at scale. Not implemented (stub). Required for production with millions of farms.
6. **Farmer enrollment** — No real farmers in the DB. The pilot uses district-level data as a proxy. Real deployment needs actual Farmer + Farm + Policy records via the API.

### Low Priority / Future
7. **IMD integration** — Only possible with a static IP. Jignesh's current ISP uses dynamic IPs.
8. **ISRO Bhoonidhi NDVI** — Register at bhoonidhi.nrsc.gov.in for 360m NDVI (vs NASA's 1km). Optional upgrade.
9. **MQTT soil sensors** — `ingestion/soil_moisture.py` is a stub. IoT sensors not deployed.
10. **AWS production deployment** — docker-compose.yml exists for local. AWS: S3, RDS Aurora, EMR Serverless, ECS Fargate, KMS, ElastiCache (planned, not built).
11. **Load testing** — 10,000 simultaneous farm triggers stress test not run.

---

## Key Files — What Each Does (Critical)

| File | Why It Matters |
|---|---|
| `config/settings.py` | All thresholds + secrets + DB URLs. Every module depends on this. |
| `rules/engine.py` | Core business logic. A bug here = wrong financial decisions. |
| `rules/definitions/*.yaml` | Threshold values. Change here — not in code — when agronomists update thresholds. |
| `payout/pipeline.py` | Where a bug causes missed or duplicate payments. |
| `payout/deduplication.py` | The dedup key generation. Must be deterministic — same inputs always produce same key. |
| `ingestion/open_meteo.py` | Live rainfall source. Contains all 20 district coordinates. |
| `processing/raster/ndvi_pipeline.py` | NDVI computation. Currently uses baseline proxy — production needs real GDAL path. |
| `registry/models.py` | Aadhaar stored as SHA-256 hash ONLY — India Aadhaar Act compliance. Never store plaintext. |
| `dashboard/app.py` | Loads `.env` manually at startup (lines 4-12) — required so NASA token is available. |

---

## Security Rules — Must Not Be Violated

1. **Aadhaar numbers** — SHA-256 hash only. Never store, log, or transmit plaintext. India Aadhaar Act.
2. **`.env` file** — Never commit. Gitignored. Contains NASA token and (when added) UPI keys.
3. **UPI IDs + bank accounts** — Fernet-encrypted at rest. Key stored in AWS KMS in production.
4. **Webhook endpoints** — HMAC-verified. Do not accept unsigned webhook payloads.
5. **GitHub** — Only account Pavo321. No collaborators added. Ever.

---

## Directory Structure (Full)

```
agri-insurance-engine/
├── .env                        # secrets — NEVER commit
├── .env.example                # template — safe to commit
├── .gitignore                  # blocks .env, *.tif, *.hdf, __pycache__
├── docker-compose.yml          # postgres, redis, api, worker, beat, spark, dashboard, mqtt
├── pyproject.toml              # Python dependencies
├── Makefile                    # convenience commands
├── alembic/                    # DB migrations (3 versions)
│   └── versions/
├── config/
│   └── settings.py             # Pydantic BaseSettings — all config here
├── ingestion/
│   ├── open_meteo.py           # ✅ LIVE — rainfall, 20 MH districts
│   ├── modis_flood.py          # ✅ LIVE — NASA flood granules
│   ├── modis_ndvi.py           # ✅ LIVE — NASA NDVI granule metadata
│   ├── imd_weather.py          # ❌ BLOCKED — needs static IP for IMD whitelist
│   └── base.py                 # AbstractIngester protocol
├── processing/
│   ├── raster/
│   │   ├── ndvi_pipeline.py    # ✅ LIVE — seasonal baseline proxy (pilot)
│   │   └── ndvi.py             # stub — GDAL production path
│   └── polygon/
│       └── zonal_stats.py      # stub — farm polygon overlay
├── rules/
│   ├── definitions/            # 5 YAML rule files
│   ├── engine.py               # RulesEngine.evaluate()
│   ├── evaluator.py            # ✅ LIVE — full district evaluation
│   ├── loader.py               # YAML → Pydantic Rule objects
│   └── models.py               # TriggerEvent, FarmMetrics, RuleResult
├── registry/
│   └── models.py               # SQLAlchemy ORM — Farmer, Farm, Policy, PayoutRecord
├── payout/
│   ├── pipeline.py             # orchestrates dedup → calculate → UPI → ledger
│   ├── calculator.py           # payout_inr = sum_insured × tier_pct
│   ├── deduplication.py        # Redis idempotency key
│   └── upi_client.py           # Razorpay UPI wrapper (needs .env keys)
├── api/
│   ├── main.py                 # FastAPI app
│   └── routers/                # admin, events, payouts, webhooks
├── dashboard/
│   └── app.py                  # ✅ LIVE — 4-page Streamlit dashboard
├── workers/
│   ├── celery_app.py           # Celery + Beat schedule
│   └── tasks/                  # ingest_weather, ingest_ndvi, evaluate_rules, dispatch_payout
├── db/
│   └── init_sql/               # PostGIS + TimescaleDB SQL setup
└── tests/
    └── unit/                   # rules, NDVI, payout, dedup tests
```

---

## Known Issues / Things To Watch

- **NASA token expiry:** `NASA_EARTHDATA_TOKEN` expires 2026-06-02. Regenerate at urs.earthdata.nasa.gov before that date.
- **NDVI is a proxy:** `processing/raster/ndvi_pipeline.py` uses a seasonal baseline + spatial adjustment, not actual pixel-level NDVI from downloaded HDF files. This is intentional for the pilot phase. It is realistic but not survey-grade.
- **FLOOD_MODIS fires statewide:** The current flood check uses `flood_data_available` (a boolean for the whole state) rather than per-farm polygon intersection. In production, MODIS flood pixels must be spatially joined to individual farm polygons.
- **District-level only:** The pilot works at district granularity. Real deployment requires farm-level polygon data (Farmer + Farm records in PostGIS).
- **No DB running by default:** `docker compose up postgres redis` is needed before payout pipeline, Celery workers, or Alembic migrations can run.
