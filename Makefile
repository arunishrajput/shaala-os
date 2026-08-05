.PHONY: up seed reset demo verify test down logs

COMPOSE = docker compose
API_RUN = $(COMPOSE) run --rm api

# Postgres + API in Docker, migrations applied, ready to seed.
up:
	$(COMPOSE) up -d --build
	@echo "Waiting for API to be healthy..."
	@for i in $$(seq 1 30); do \
		curl -sf http://localhost:8000/health > /dev/null && break; \
		sleep 1; \
	done
	$(API_RUN) alembic upgrade head

seed:
	$(API_RUN) python -m app.db.seed

# Wipes and reseeds with the fixed-seed dataset (PROMPT.md §5) — same as `make seed`,
# named separately because it's also what the demo-reset story maps to conceptually.
reset: seed

# One command from cold to a working, seeded demo. CLAUDE.md: every commit leaves
# this working.
demo: up seed
	@echo "Backend: http://localhost:8000/health"
	@echo "Run the Flutter app separately: cd apps/admin && flutter run -d chrome"

# The gate. Nothing is done until this exits 0 (CLAUDE.md).
verify: up
	$(API_RUN) ruff check .
	$(API_RUN) mypy app --ignore-missing-imports
	$(API_RUN) pytest -q
	cd apps/admin && flutter analyze
	cd apps/admin && flutter build web

test:
	$(API_RUN) pytest -q

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f
