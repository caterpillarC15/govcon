.PHONY: dev services-up services-down logs schemas migrate test typecheck lint format help

help:
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?##"}; {printf "  %-18s %s\n", $$1, $$2}'

dev: ## Run the FastAPI app with --reload (assumes services up)
	uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

services-up: ## Start Redis (PRD v1.2.3 — Postgres is Supabase). Pass PG=1 to also start a local Postgres dev fallback.
	@if command -v brew >/dev/null 2>&1; then \
	  brew services start redis; \
	  [ "$(PG)" = "1" ] && brew services start postgresql@16 || true; \
	else \
	  sudo systemctl start redis-server; \
	  [ "$(PG)" = "1" ] && sudo systemctl start postgresql || true; \
	fi

services-down: ## Stop Redis (and local Postgres dev fallback if started with PG=1).
	@if command -v brew >/dev/null 2>&1; then \
	  brew services stop redis; \
	  brew services stop postgresql@16 2>/dev/null || true; \
	else \
	  sudo systemctl stop redis-server; \
	  sudo systemctl stop postgresql 2>/dev/null || true; \
	fi

logs: ## Tail local Postgres logs (only useful when running PG=1 fallback; Supabase logs live in the dashboard).
	@if command -v brew >/dev/null 2>&1; then \
	  tail -F "$$(brew --prefix)/var/log/postgresql@16.log"; \
	else \
	  journalctl -u postgresql -f; \
	fi

schemas: ## Regenerate Pydantic models from /schemas/*.schema.json (and TS if /web exists)
	@rm -rf api/schemas /tmp/govcon-schema-input
	@mkdir -p api/schemas /tmp/govcon-schema-input
	@cp schemas/*.schema.json /tmp/govcon-schema-input/
	@uv run datamodel-codegen \
	  --input /tmp/govcon-schema-input \
	  --input-file-type jsonschema \
	  --output api/schemas \
	  --output-model-type pydantic_v2.BaseModel \
	  --use-standard-collections \
	  --use-union-operator \
	  --target-python-version 3.12 \
	  --use-schema-description \
	  --field-constraints \
	  --use-default \
	  --enum-field-as-literal all \
	  --disable-timestamp
	@rm -rf /tmp/govcon-schema-input
	@for f in api/schemas/*_schema.py; do \
	  [ -e "$$f" ] || continue; \
	  mv "$$f" "$${f%_schema.py}.py"; \
	done
	@touch api/schemas/__init__.py
	@echo "✓ Pydantic models generated in api/schemas/"
	@if [ -d web ]; then \
	  echo "⚠ TS codegen for /web is Dev 2's wire-up — see CONTRACTS.md §2"; \
	else \
	  echo "⚠ /web/ not present — skipping TS codegen (Dev 2 wires when /web exists)"; \
	fi

migrate: ## Apply Alembic migrations
	cd api && uv run alembic upgrade head

migrate-down: ## Roll back one Alembic migration
	cd api && uv run alembic downgrade -1

migration: ## Create a new Alembic revision (autogenerate). Usage: make migration MSG="describe change"
	cd api && uv run alembic revision --autogenerate -m "$(MSG)"

test: ## Run the test suite
	uv run pytest -v api/tests

typecheck: ## Run mypy
	uv run mypy api

lint: ## Run ruff
	uv run ruff check api

format: ## Format with ruff
	uv run ruff format api
