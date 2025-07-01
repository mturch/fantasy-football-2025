.PHONY: help install format check test run clean lint type-check

# Default target
help:
	@echo "Available targets:"
	@echo "  install     - Install dependencies using uv"
	@echo "  install-dev - Install package in development mode"
	@echo "  format      - Format code with black and isort"
	@echo "  check       - Run all checks (lint, type-check, test)"
	@echo "  lint        - Run flake8 linter"
	@echo "  type-check  - Run mypy type checker"
	@echo "  test        - Run pytest tests"
	@echo "  run         - Run the main application"
	@echo "  clean       - Clean up cache files and build artifacts"
	@echo "  dev-install - Install development dependencies"

# Install dependencies
install:
	uv sync

# # Install package in development mode
# install-dev:
# 	uv sync --dev
# 	uv pip install -e .

# Install development dependencies
dev-install:
	uv sync --dev

# Format code
format:
	uv run black src/fantasy_football_2025/ tests/ scripts/
	uv run isort src/fantasy_football_2025/ tests/ scripts/

# Lint code
lint:
	uv run flake8 src/fantasy_football_2025/ tests/ scripts/

# Type check
type-check:
	uv run mypy src/fantasy_football_2025/

# Run all checks
check: lint type-check test

# Run tests
test:
	uv run pytest

# Run tests with coverage
test-cov:
	uv run pytest --cov=fantasy_football_2025 --cov-report=term-missing --cov-report=html

# Run the main application
run:
	uv run python -m fantasy_football_2025.main

# Run lineup optimization
optimize:
	uv run python -m fantasy_football_2025.lineup_optimizer

# Pull Sleeper data
pull-data:
	uv run python -m fantasy_football_2025.sleeper_client --pull-all

# Analyze trades
analyze-trades:
	uv run python -m fantasy_football_2025.trade_analyzer

# Get waiver recommendations
waiver-wire:
	uv run python -m fantasy_football_2025.waiver_analyzer

# Run Jupyter notebook server
notebook:
	uv run jupyter notebook

# Clean up cache and build files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/

# Install pre-commit hooks
setup-hooks:
	uv run pre-commit install

# Run pre-commit on all files
pre-commit:
	uv run pre-commit run --all-files

# Build package
build:
	uv build

# Database operations
db-setup:
	uv run python scripts/setup_database.py --setup

db-reset:
	uv run python scripts/setup_database.py --reset

db-verify:
	uv run python scripts/setup_database.py --verify

db-info:
	uv run python scripts/setup_database.py --info

db-sample:
	uv run python scripts/setup_database.py --create-sample-data

# Data migration
migrate-json:
	uv run python scripts/migrate_data.py --migrate-json data/raw --league-id $(LEAGUE_ID)

backup-db:
	uv run python scripts/migrate_data.py --backup data/backups --league-id $(LEAGUE_ID)

# Historical data import
import-historical:
	uv run python scripts/import_historical_data.py --data-dir data/external/weather --schema historical_data

import-historical-validate:
	uv run python scripts/import_historical_data.py --data-dir data/external/weather --schema historical_data --validate-only

import-historical-custom:
	uv run python scripts/import_historical_data.py --data-dir $(DATA_DIR) --schema $(SCHEMA) --batch-size $(BATCH_SIZE)

test-historical-data:
	uv run python scripts/test_weather_data.py

# Weather API pull targets
pull-weather-games:
	uv run python scripts/pull_weather_data.py --api-key $(WEATHER_API_KEY) --api-provider $(WEATHER_API_PROVIDER) --days-ahead $(DAYS_AHEAD)

pull-weather-stadiums:
	uv run python scripts/pull_weather_data.py --api-key $(WEATHER_API_KEY) --api-provider $(WEATHER_API_PROVIDER) --stadiums-only

pull-weather-current:
	uv run python scripts/pull_weather_data.py --api-key $(WEATHER_API_KEY) --api-provider $(WEATHER_API_PROVIDER) --days-ahead 1 --no-forecast

pull-weather-forecast:
	uv run python scripts/pull_weather_data.py --api-key $(WEATHER_API_KEY) --api-provider $(WEATHER_API_PROVIDER) --days-ahead 7

# Show project info
info:
	@echo "Fantasy Football 2025 Analytics"
	@echo "Python version: $(shell python --version)"
	@echo "uv version: $(shell uv --version)"
	@echo "Project structure:"
	@tree -I '__pycache__|*.pyc|.git|.pytest_cache|.mypy_cache|htmlcov|*.egg-info' -L 2

# SageMaker Pipeline targets
pipeline-deploy:
	uv run python -m fantasy_football_2025.pipeline --deploy --league-id $(LEAGUE_ID) --user-id $(USER_ID)

pipeline-execute:
	uv run python -m fantasy_football_2025.pipeline --execute --league-id $(LEAGUE_ID) --user-id $(USER_ID) --season $(SEASON) --week $(WEEK)

pipeline-build-image:
	./scripts/build_sagemaker_image.sh $(AWS_REGION) $(AWS_ACCOUNT_ID) $(IMAGE_NAME)

# Docker targets for pipeline
docker-pipeline:
	docker-compose -f docker-compose.pipeline.yml up --build

docker-pipeline-build:
	docker build -f Dockerfile.pipeline -t fantasy-football-pipeline .

# Environment setup
env-setup:
	@echo "Setting up environment variables..."
	@source scripts/set_env.sh

env-show:
	@echo "Current environment variables:"
	@echo "DB_HOST: $${DB_HOST:-not set}"
	@echo "DB_NAME: $${DB_NAME:-not set}"
	@echo "WEATHER_API_KEY: $${WEATHER_API_KEY:-not set}"
	@echo "WEATHER_API_PROVIDER: $${WEATHER_API_PROVIDER:-not set}"
	@echo "SLEEPER_LEAGUE_ID: $${SLEEPER_LEAGUE_ID:-not set}"
	@echo "ENVIRONMENT: $${ENVIRONMENT:-not set}"

env-test:
	@echo "Testing environment configuration..."
	@source scripts/set_env.sh
	@echo "Environment variables loaded successfully!"

# AWS CLI helpers
aws-setup:
	@echo "Setting up AWS credentials and configuration..."
	aws configure list || aws configure

aws-test:
	@echo "Testing AWS connectivity..."
	aws sts get-caller-identity
	aws s3 ls

# Environment switching
env-dev:
	@export ENVIRONMENT=DEV && source scripts/set_env.sh && echo "Switched to DEV environment"

env-test:
	@export ENVIRONMENT=TEST && source scripts/set_env.sh && echo "Switched to TEST environment"

env-prod:
	@export ENVIRONMENT=PRODUCTION && source scripts/set_env.sh && echo "Switched to PRODUCTION environment"

run-dev:
	@export ENVIRONMENT=DEV && source scripts/set_env.sh && make run

run-test:
	@export ENVIRONMENT=TEST && source scripts/set_env.sh && make run

run-prod:
	@export ENVIRONMENT=PRODUCTION && source scripts/set_env.sh && make run