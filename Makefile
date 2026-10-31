.PHONY: api web migrate seed test reset-db openapi

api:
	cd apps/api && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000

web:
	cd apps/web && npm run dev

migrate:
	cd apps/api && uv run alembic upgrade head

seed:
	cd apps/api && uv run python scripts/seed_dev.py

test:
	cd apps/api && uv run ruff check app tests scripts && uv run pytest
	cd apps/web && npm test && npm run typecheck && npm run lint

reset-db:
	cd apps/api && uv run python scripts/reset_dev_db.py --yes

openapi:
	cd apps/api && uv run python scripts/export_openapi.py
	cd apps/web && npm run generate:api
