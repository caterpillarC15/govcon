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
	# Hand-written modules under api/schemas/ MUST survive codegen. JSON Schema
	# can't express field validators, alternate class names, or PATCH-shape
	# subsets — so these files are authored by hand:
	#   api_key.py         — typed wrapper for /api/keys (no JSON Schema source)
	#   tool_requests.py   — typed wrappers for POST /tools/<name> (no source)
	#   profile.py         — Profile + ProfileUpdate (PATCH-shape; no source for Update)
	#   waitlist.py        — WaitlistSignupCreate (with email-normalize validator)
	#                        + WaitlistSignupResponse (no source)
	#   opportunity.py     — Opportunity (source/active are required-with-default,
	#                        not nullable; JSON Schema expresses defaults but not
	#                        "required AND non-null AND has default")
	#   fixture_manifest.py — has two distinct attachment shapes that codegen
	#                        names Attachment / Attachment1; hand version uses
	#                        OpportunityAttachment / Attachment for clarity.
	#
	# The for-loop below only deletes files whose stem matches a JSON Schema
	# source AND is not in the hand-written allowlist.
	@rm -rf /tmp/govcon-schema-input
	@mkdir -p api/schemas /tmp/govcon-schema-input
	@for src in schemas/*.schema.json; do \
	  base=$$(basename "$$src" .schema.json); \
	  stem=$$(echo "$$base" | tr '-' '_'); \
	  case "$$stem" in \
	    api_key|tool_requests|profile|waitlist|opportunity|fixture_manifest) \
	      continue ;; \
	  esac; \
	  rm -f "api/schemas/$$stem.py"; \
	  cp "$$src" /tmp/govcon-schema-input/; \
	done
	@rm -f api/schemas/__init__.py
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

eval: ## Deterministic skill regression — diff committed goldens (PRD v1.2.6, no LLM)
	uv run python -m eval.runner.runner

eval-bootstrap: ## (Re)write goldens from current deterministic skill output
	uv run python -m eval.runner.runner --bootstrap

sse-stub: ## Publish a stub trace to Redis (RUN_ID=<uuid>) — exercises /web SSE without orchestrator
	@if [ -z "$(RUN_ID)" ]; then echo "Usage: make sse-stub RUN_ID=<run-uuid> [DELAY_MS=500]"; exit 2; fi
	uv run python scripts/sse_stub_publisher.py "$(RUN_ID)" --delay-ms $${DELAY_MS:-500}
