.PHONY: dev services-up services-down schemas db-push db-new db-pull migrate fixtures-validate test typecheck lint format eval eval-bootstrap help

help:
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?##"}; {printf "  %-18s %s\n", $$1, $$2}'

dev: ## Run the FastAPI app with --reload (assumes Redis up + Supabase configured)
	uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

services-up: ## Start Redis. Postgres lives in Supabase — managed externally.
	@if command -v brew >/dev/null 2>&1; then \
	  brew services start redis; \
	else \
	  sudo systemctl start redis-server; \
	fi

services-down: ## Stop Redis.
	@if command -v brew >/dev/null 2>&1; then \
	  brew services stop redis; \
	else \
	  sudo systemctl stop redis-server; \
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
	  echo "⚠ TS schema codegen for /web is not currently wired or consumed — see CONTRACTS.md §2"; \
	else \
	  echo "⚠ /web/ not present — skipping TS codegen (Dev 2 wires when /web exists)"; \
	fi

fixtures-validate: ## Validate every fixture manifest against schemas/fixture-manifest.schema.json
	@uv run python -c "import json, jsonschema, glob; \
schema = json.load(open('schemas/fixture-manifest.schema.json')); \
[ (jsonschema.validate(json.load(open(f)), schema), print(f'OK {f}')) \
  for f in sorted(glob.glob('fixtures/*/manifest.json')) \
  if '/_template/' not in f ] or print('(no fixtures yet)')"

db-push: ## Apply Supabase SQL migrations to the linked Supabase project
	supabase db push

db-new: ## Create a Supabase SQL migration. Usage: make db-new NAME=add_table
	supabase migration new "$(NAME)"

db-pull: ## Pull remote Supabase schema into supabase/migrations
	supabase db pull

migrate: db-push ## Backward-compatible alias for Supabase migrations

test: ## Run the test suite
	uv run pytest -v api/tests

typecheck: ## Run mypy
	uv run mypy api

lint: ## Run ruff
	uv run ruff check api

format: ## Format with ruff
	uv run ruff format api

eval: ## run LLM-skill regression eval against committed goldens
	uv run python -m eval.runner.runner

eval-bootstrap: ## (re)write goldens by running real LLM calls — costs Anthropic tokens
	uv run python -m eval.runner.runner --bootstrap
