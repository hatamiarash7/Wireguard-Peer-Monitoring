.PHONY: clean shell install dev lock run build test lint help
.DEFAULT_GOAL := help

clean: ## Clean build files
	@rm -rf dist

shell: ## Activate venv
	@poetry env activate

install: ## Install dependencies
	@poetry install

dev: ## Install dependencies - dev env
	@poetry install --with=dev,test

lock: ## Update poetry.lock
	@poetry lock

run: ## Run project
	@poetry run python -m monitoring

build: clean ## Build package
	@poetry build

test: ## Run tests
	@poetry run pytest

lint: ## Lint files
	@find . -name "*.py" -not -ipath "./.venv/*" | xargs python3 -m pylint --rcfile=.pylintrc --ignore-patterns=test_.*?py

vuln: ## Check for vulnerabilities
	@osv-scanner scan --lockfile poetry.lock
	@bandit -r . --severity-level=high --exclude ./.venv,./.git

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
