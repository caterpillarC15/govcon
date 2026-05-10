.PHONY: dev services-up services-down schemas db-push db-pull db-new test typecheck lint format help

help:
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?##"}; {printf "  %-18s %s\n", $$1, $$2}'

dev: ## Run the FastAPI app with --reload (Postgres = Supabase remote, Redis = local)
	uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

services-up: ## Start local Redis (Postgres is Supabase remote — nothing local for DB)
	@if command -v brew >/dev/null 2>&1; then \
	  brew services start redis; \
	else \
	  sudo systemctl start redis-server; \
	fi

services-down: ## Stop local Redis
	@if command -v brew >/dev/null 2>&1; then \
	  brew services stop redis; \
	else \
	  sudo systemctl stop redis-server; \
	fi

db-push: ## Apply pending Supabase migrations to the linked remote project
	supabase db push

db-pull: ## Pull current remote schema into supabase/migrations/ as a baseline
	supabase db pull

db-new: ## Create a new Supabase migration. Usage: make db-new NAME=add_feature_x
	supabase migration new $(NAME)

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

test: ## Run the test suite
	uv run pytest -v api/tests

typecheck: ## Run mypy
	uv run mypy api

lint: ## Run ruff
	uv run ruff check api

format: ## Format with ruff
	uv run ruff format api
