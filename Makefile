.PHONY: up down build test lint migrate ingest-mock simulate-flood

# ─── Infrastructure ───────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

# ─── Database ─────────────────────────────────────────────
migrate:
	alembic upgrade head

migrate-rollback:
	alembic downgrade -1

# ─── Development ──────────────────────────────────────────
dev-api:
	uvicorn api.main:app --reload --port 8000

dev-dashboard:
	streamlit run dashboard/app.py

dev-worker:
	celery -A workers.celery_app worker --loglevel=debug

# ─── Testing ──────────────────────────────────────────────
test:
	pytest tests/ -v --cov=. --cov-report=term-missing

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

# ─── Code Quality ─────────────────────────────────────────
lint:
	ruff check .
	black --check .

format:
	black .
	ruff check --fix .

security-scan:
	bandit -r . -x tests/

# ─── Mock Data & Simulation ───────────────────────────────
ingest-mock:
	python -m ingestion.mock_data --state MH --farms 100

simulate-flood:
	python -m rules.simulate --rule FLOOD_RAIN_48H --state MH --dry-run

simulate-drought:
	python -m rules.simulate --rule DROUGHT_NDVI_30 --state MH --dry-run
