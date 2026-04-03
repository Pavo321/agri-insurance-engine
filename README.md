# 🌾 Agricultural Micro-Insurance Trigger Engine

**Parametric micro-insurance for Indian farmers — satellite + sensor data to UPI payout in under 24 hours.**

[![CI](https://github.com/Pavo321/agri-insurance-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/Pavo321/agri-insurance-engine/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## The Problem

70% of Indian farmers have no crop insurance. Existing PMFBY claims take **3–6 months**. Farmers need money within **days** of a flood or drought. All the data — ISRO satellite NDVI, IMD rain gauges, soil moisture sensors — exists but isn't wired to a fast payout engine.

## The Solution

Parametric insurance: **if a verifiable weather event crosses a defined threshold → automatically pay the farmer within 24 hours — no claims forms, no inspectors.**

```
Satellite detects flood → Rules engine fires → UPI payout to farmer → Done
```

---

## How It Works

| Step | What Happens | Tools |
|------|-------------|-------|
| 1. Ingest | Pull satellite + weather + sensor data | GDAL, MQTT, REST APIs |
| 2. Process | Compute NDVI crop health per farm pixel | GDAL + Dask |
| 3. Match | Link each farm polygon to its NDVI + rain values | Apache Spark + PostGIS |
| 4. Rules | Check 5 parametric trigger thresholds hourly | Python Rules Engine + YAML |
| 5. Pay | Send money to farmer's UPI ID | NPCI UPI API |
| 6. Audit | Full ledger: satellite URL → UTR number | PostgreSQL |

---

## Trigger Rules

| Rule | Condition | Payout |
|------|-----------|--------|
| `FLOOD_RAIN_48H` | Rainfall >= 200mm in 48 hours | 40% of sum insured |
| `DROUGHT_RAIN_14D` | Rainfall <= 20mm over 14 days | 25% of sum insured |
| `DROUGHT_NDVI_30` | NDVI drops >= 30% for 3 consecutive days | 25% of sum insured |
| `FLOOD_MODIS` | NASA MODIS flood detected on farm | 40% of sum insured |
| `DROUGHT_SOIL_VWC` | Soil moisture <= 15% for 3 days | 15% of sum insured |

Rules are defined in YAML — agronomists can tune thresholds without code changes.

---

## Tech Stack

```
Data Sources:   ISRO Bhuvan (NDVI) · IMD (rainfall) · NASA MODIS (flood) · IoT Sensors (soil)
Processing:     GDAL · Dask · Apache Spark (PySpark)
Databases:      PostgreSQL + PostGIS · TimescaleDB · Redis
Backend:        FastAPI · Celery + Celery Beat
Dashboard:      Streamlit · Folium
Infrastructure: Docker Compose · (AWS: S3, RDS, EMR, ECS in production)
Payout:         NPCI UPI AutoPay API
```

---

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/Pavo321/agri-insurance-engine.git
cd agri-insurance-engine
cp .env.example .env   # fill in your API keys

# 2. Start all services
make up

# 3. Run database migrations
make migrate

# 4. Run tests
make test

# 5. Open dashboard
open http://localhost:8501

# 6. Open API docs
open http://localhost:8000/docs
```

---

## Project Structure

```
agri-insurance-engine/
├── config/          # Pydantic settings — all config here
├── ingestion/       # Data fetchers: ISRO, IMD, NASA, IoT sensors
├── processing/      # GDAL + Dask raster pipeline + Spark polygon overlay
├── rules/           # YAML rule definitions + Python evaluation engine
├── registry/        # Farmer, Farm, Policy database models
├── payout/          # UPI payout pipeline with Redis deduplication
├── api/             # FastAPI endpoints + HMAC-verified webhooks
├── dashboard/       # Streamlit monitoring dashboard + Folium maps
├── workers/         # Celery tasks + Beat schedule
├── db/              # PostGIS + TimescaleDB SQL initialization
└── tests/           # Unit tests (NDVI, rules, payout, dedup)
```

---

## Implementation Phases

- [x] **Phase 0** — Project structure, agents, documentation
- [ ] **Phase 1** — Foundation: Docker, DB migrations, farmer CRUD API
- [ ] **Phase 2** — Ingestion: IMD weather + soil MQTT -> TimescaleDB
- [ ] **Phase 3** — Raster: GDAL + Dask NDVI pipeline
- [ ] **Phase 4** — Rules engine: YAML evaluation + Celery task
- [ ] **Phase 5** — Payout: Redis dedup + UPI + audit ledger
- [ ] **Phase 6** — Spark: full-state polygon overlay
- [ ] **Phase 7** — Dashboard + hardening + load test

---

## Security

- Aadhaar numbers: SHA-256 hashed (India Aadhaar Act compliance) — never stored plaintext
- UPI IDs + bank accounts: Fernet encrypted at rest (key in AWS KMS in production)
- Webhooks: HMAC-SHA256 verified + 5-minute timestamp window (replay attack prevention)
- Payout: dual-layer deduplication (30-day DB cooldown + Redis idempotency key)

---

## Pilot

**State: Maharashtra** — largest agricultural state, highest PMFBY enrollment, covers cotton, soybean, and sugarcane crops.

---

## License

MIT License
