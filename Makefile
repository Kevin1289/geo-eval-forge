# geo-eval-forge — convenience targets.
# The offline targets (build/run/test/validate) need only Docker; the live
# targets additionally boot PostGIS + GeoServer. Everything runs inside the
# worker image so the Python/GDAL versions are pinned and reproducible.

COMPOSE := docker compose
WORKER  := $(COMPOSE) run --rm --no-deps worker
WORKER_LIVE := $(COMPOSE) run --rm worker

.PHONY: help build up down logs seed run run-live test validate judge \
        dashboard dashboard-dev clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

build: ## Build the worker image (GDAL + python + geoeval)
	$(COMPOSE) build worker

up: ## Boot postgis + geoserver (detached) and wait for health
	$(COMPOSE) up -d postgis geoserver
	@echo "waiting for postgis..." && $(COMPOSE) exec -T postgis sh -c 'until pg_isready -U $${POSTGRES_USER:-geoeval} >/dev/null 2>&1; do sleep 1; done' || true

down: ## Stop everything and remove volumes
	$(COMPOSE) down -v

logs: ## Tail service logs
	$(COMPOSE) logs -f

seed: build ## Generate deterministic synthetic data (files; + PostGIS if up)
	$(WORKER) python -m data.seed.make_seed

run: build ## Offline: grade the recorded candidates → results/results.json
	$(WORKER) geoeval run --offline --out results/results.json

run-live: build up ## Live: execute candidates against PostGIS/GeoServer, then verify
	$(WORKER_LIVE) geoeval run --live --out results/results.json

validate: build ## Validate every task.json against the schema
	$(WORKER) geoeval validate

judge: build ## Run the (optional) LLM-as-judge and report human agreement
	$(WORKER_LIVE) geoeval judge

export: build ## Export AI-training data (dataset/records.jsonl + preference_pairs.jsonl)
	$(WORKER) geoeval export

test: build ## Run the test suite (schema + verifiers; golden passes / wrong fails)
	$(WORKER) pytest

dashboard: ## Build the static dashboard from results/results.json
	@mkdir -p dashboard/public
	@cp -f results/results.json dashboard/public/results.json
	@cp -rf results/geojson dashboard/public/geojson 2>/dev/null || true
	cd dashboard && npm install && npm run build
	@echo "Static site in dashboard/out/ — open dashboard/out/index.html"

dashboard-dev: ## Run the dashboard in dev mode (hot reload)
	@mkdir -p dashboard/public && cp -f results/results.json dashboard/public/results.json
	@cp -rf results/geojson dashboard/public/geojson 2>/dev/null || true
	cd dashboard && npm install && npm run dev

clean: ## Remove generated run artifacts
	rm -rf results/run-* dashboard/.next dashboard/out dashboard/public/results.json dashboard/public/geojson
