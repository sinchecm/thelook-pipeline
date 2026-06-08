.DEFAULT_GOAL := help
SHELL         := /bin/bash
VENV          := .venv
DBT_DIR       := dbt_project
PYTHON        := $(VENV)/bin/python
DBT           := /home/ming/thelook-pipeline/thelook-pipeline/.venv/bin/dbt
PIP           := $(VENV)/bin/pip
DBT           := /home/ming/thelook-pipeline/thelook-pipeline/.venv/bin/dbt

RESET  := [0m
BOLD   := [1m
CYAN   := [36m
GREEN  := [32m
YELLOW := [33m
RED    := [31m

.PHONY: help
help:
	@echo ""
	@echo "$(BOLD)TheLook E-Commerce Data Pipeline$(RESET)"
	@echo ""
	@echo "$(BOLD)Setup$(RESET)"
	@echo "  $(CYAN)make install$(RESET)       Install Python dependencies"
	@echo "  $(CYAN)make setup-db$(RESET)      Create schemas in Supabase"
	@echo "  $(CYAN)make dbt-deps$(RESET)      Install $(DBT) packages"
	@echo "  $(CYAN)make dbt-debug$(RESET)     Test $(DBT) connection"
	@echo ""
	@echo "$(BOLD)Pipeline$(RESET)"
	@echo "  $(CYAN)make ingest$(RESET)        Extract BigQuery → raw schema"
	@echo "  $(CYAN)make dbt-run$(RESET)       Run all $(DBT) models"
	@echo "  $(CYAN)make dbt-test$(RESET)      Run $(DBT) tests"
	@echo "  $(CYAN)make quality$(RESET)       Run data quality checks"
	@echo "  $(CYAN)make analyse$(RESET)       Run Python EDA"
	@echo "  $(CYAN)make pipeline$(RESET)      Run full pipeline end-to-end"
	@echo ""
	@echo "$(BOLD)Utilities$(RESET)"
	@echo "  $(CYAN)make env-check$(RESET)     Verify .env variables"
	@echo "  $(CYAN)make clean$(RESET)         Remove generated files"
	@echo ""

.PHONY: install
install:
	@echo "$(YELLOW)→ Creating virtual environment...$(RESET)"
	python3.11 -m venv $(VENV)
	@echo "$(YELLOW)→ Installing dependencies...$(RESET)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(RESET)"

.PHONY: dbt-deps
dbt-deps:
	@echo "$(YELLOW)→ Installing $(DBT) packages...$(RESET)"
	cd $(DBT_DIR) && $(DBT) deps
	@echo "$(GREEN)✓ $(DBT) packages installed$(RESET)"

.PHONY: dbt-debug
dbt-debug:
	@echo "$(YELLOW)→ Testing $(DBT) connection...$(RESET)"
	cd $(DBT_DIR) && $(DBT) debug

.PHONY: ingest
ingest:
	@echo "$(YELLOW)→ Starting ingestion...$(RESET)"
	$(PYTHON) -m ingestion.extract
	@echo "$(GREEN)✓ Ingestion complete$(RESET)"

.PHONY: dbt-run
dbt-run:
	@echo "$(YELLOW)→ Running $(DBT) models...$(RESET)"
	cd $(DBT_DIR) && $(DBT) run
	@echo "$(GREEN)✓ $(DBT) models built$(RESET)"

.PHONY: dbt-staging
dbt-staging:
	cd $(DBT_DIR) && $(DBT) run --select staging

.PHONY: dbt-marts
dbt-marts:
	cd $(DBT_DIR) && $(DBT) run --select marts

.PHONY: dbt-test
dbt-test:
	@echo "$(YELLOW)→ Running $(DBT) tests...$(RESET)"
	cd $(DBT_DIR) && $(DBT) test
	@echo "$(GREEN)✓ $(DBT) tests passed$(RESET)"

.PHONY: quality
quality:
	@echo "$(YELLOW)→ Running data quality checks...$(RESET)"
	$(PYTHON) -m quality.expectations
	$(PYTHON) -m quality.custom_sql_checks
	@echo "$(GREEN)✓ Quality checks passed$(RESET)"

.PHONY: analyse
analyse:
	@echo "$(YELLOW)→ Running Python analysis...$(RESET)"
	mkdir -p analysis/outputs
	$(PYTHON) -m analysis.eda
	@echo "$(GREEN)✓ Analysis complete$(RESET)"

.PHONY: pipeline
pipeline: ingest dbt-run dbt-test quality analyse
	@echo "$(GREEN)$(BOLD)✓ Full pipeline complete$(RESET)"

.PHONY: dbt-docs
dbt-docs:
	cd $(DBT_DIR) && $(DBT) docs generate && $(DBT) docs serve --port 8080

.PHONY: dbt-clean
dbt-clean:
	rm -rf $(DBT_DIR)/target $(DBT_DIR)/logs $(DBT_DIR)/dbt_packages

.PHONY: dagster
dagster:
	$(VENV)/bin/dagster dev -f orchestration/pipeline.py

.PHONY: env-check
env-check:
	@echo "$(YELLOW)→ Checking environment variables...$(RESET)"
	@for var in GCP_PROJECT_ID BQ_DATASET DW_HOST DW_PORT DW_DATABASE DW_USER DW_PASSWORD DBT_HOST DBT_USER DBT_PASSWORD GOOGLE_APPLICATION_CREDENTIALS; do \
		val=$$(grep -s "^$$var=" .env | cut -d= -f2-); \
		if [ -z "$$val" ]; then \
			echo "  $(RED)✗ $$var is not set$(RESET)"; \
		else \
			echo "  $(GREEN)✓ $$var$(RESET)"; \
		fi; \
	done

.PHONY: clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf analysis/outputs/*.png analysis/outputs/*.csv .dagster/
	@echo "$(GREEN)✓ Clean complete$(RESET)"
