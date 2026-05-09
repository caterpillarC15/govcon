.PHONY: dev services-up services-down logs schemas migrate test typecheck lint format help

help:
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?##"}; {printf "  %-18s %s\n", $$1, $$2}'

dev: ## Run the FastAPI app with --reload (assumes services up)
	uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

services-up: ## Start native Postgres + Redis (idempotent; brew on macOS, systemctl on Linux)
	@if command -v brew >/dev/null 2>&1; then \
	  brew services start postgresql@16; \
	  brew services start redis; \
	else \
	  sudo systemctl start postgresql redis-server; \
	fi

services-down: ## Stop native Postgres + Redis
	@if command -v brew >/dev/null 2>&1; then \
	  brew services stop postgresql@16; \
	  brew services stop redis; \
	else \
	  sudo systemctl stop postgresql redis-server; \
	fi

logs: ## Tail Postgres logs (Redis is usually quiet)
	@if command -v brew >/dev/null 2>&1; then \
	  tail -F "$$(brew --prefix)/var/log/postgresql@16.log"; \
	else \
	  journalctl -u postgresql -f; \
	fi

schemas: ## Regenerate Pydantic models from /schemas/*.json (and TS if /web exists)
	@rm -rf api/schemas
	@mkdir -p api/schemas
	@uv run datamodel-codegen \
	  --input schemas \
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
