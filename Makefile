COMPOSE ?= docker compose
PYTHON_IMAGE ?= python:3.12-slim
POSTGRES_IMAGE ?= postgres:16-alpine
BACKUP_DIR ?= ./backups

.PHONY: help up build test down logs fmt backup restore seed shell

help:
	@echo "up       - build and start the whole stack (tests run first, as a gate)"
	@echo "build    - build the images only"
	@echo "test     - run ruff + pytest in the tests container"
	@echo "down     - stop the stack"
	@echo "logs     - follow the app and worker logs"
	@echo "fmt      - format the code with ruff"
	@echo "backup   - dump the database into ./backups"
	@echo "restore  - restore a backup from ./backups (BACKUP_FILE=...)"
	@echo "seed     - insert Persian demo data"

up:
	$(COMPOSE) up --build -d

build:
	$(COMPOSE) build

test:
	$(COMPOSE) run --rm tests

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f app worker

fmt:
	$(COMPOSE) run --rm --no-deps tests sh -c "ruff format . && ruff check --fix ."

backup:
	@mkdir -p $(BACKUP_DIR)
	@$(COMPOSE) exec -T db pg_dump -U $${POSTGRES_USER:-varagh} $${POSTGRES_DB:-varagh} > $(BACKUP_DIR)/varagh-$$(date +%Y%m%d-%H%M%S).sql
	@echo "backup written to $(BACKUP_DIR)"

restore:
	@test -n "$(BACKUP_FILE)" || (echo "usage: make restore BACKUP_FILE=backups/<file>.sql" && exit 1)
	$(COMPOSE) exec -T db psql -U $${POSTGRES_USER:-varagh} -d $${POSTGRES_DB:-varagh} < $(BACKUP_FILE)

seed:
	$(COMPOSE) run --rm app python -m app.seed

shell:
	$(COMPOSE) run --rm app bash
