.DEFAULT_GOAL := help
POETRY ?= poetry
IMAGE ?= wg-peer-monitoring:local
.PHONY: help clean install dev lock update run build test lint format check security docker-build

install: ## Install locked runtime dependencies
	$(POETRY) sync --only main

dev: ## Install locked runtime and development dependencies
	$(POETRY) sync --with dev,test

lock: ## Resolve changed dependency constraints
	$(POETRY) lock

update: ## Update dependencies within their declared constraints
	$(POETRY) update

run: ## Run the monitor (set CONFIG_FILE for local configuration)
	$(POETRY) run python -m monitoring

build: ## Build wheel and source distribution
	$(POETRY) build

test: ## Run tests with branch coverage and a 95% minimum
	$(POETRY) run pytest

lint: ## Check formatting, import order, and Python code
	$(POETRY) run black --check monitoring tests
	$(POETRY) run isort --check-only monitoring tests
	$(POETRY) run pylint --rcfile=.pylintrc monitoring

format: ## Format Python code and imports
	$(POETRY) run isort monitoring tests
	$(POETRY) run black monitoring tests

security: ## Check runtime source for security issues
	$(POETRY) run bandit -r monitoring -ll

check: lint test security ## Run local CI checks
	$(POETRY) check --lock

docker-build: ## Build the local runtime image
	docker build --tag $(IMAGE) .

clean: ## Remove generated build and coverage reports
	rm -rf build dist htmlcov .pytest_cache .coverage coverage.xml

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "%-20s %s\n", $$1, $$2}'
