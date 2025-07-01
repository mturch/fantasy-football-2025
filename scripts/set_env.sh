#!/bin/bash
# Environment Variables Setup Script for Fantasy Football 2025
# This script sets up environment variables for the project

# Environment (DEV, TEST, PRODUCTION)
export ENVIRONMENT=${ENVIRONMENT:-"DEV"}

# DEV Database
export DEV_DB_HOST=${DEV_DB_HOST:-"localhost"}
export DEV_DB_PORT=${DEV_DB_PORT:-"3306"}
export DEV_DB_USER=${DEV_DB_USER:-"fantasy_user"}
export DEV_DB_PASSWORD=${DEV_DB_PASSWORD:-"fantasy_password"}
export DEV_DB_NAME=${DEV_DB_NAME:-"fantasy_football_dev"}

# TEST Database
export TEST_DB_HOST=${TEST_DB_HOST:-"localhost"}
export TEST_DB_PORT=${TEST_DB_PORT:-"3306"}
export TEST_DB_USER=${TEST_DB_USER:-"fantasy_user"}
export TEST_DB_PASSWORD=${TEST_DB_PASSWORD:-"fantasy_password"}
export TEST_DB_NAME=${TEST_DB_NAME:-"fantasy_football_test"}

# PRODUCTION Database
export PROD_DB_HOST=${PROD_DB_HOST:-"prod-db-host"}
export PROD_DB_PORT=${PROD_DB_PORT:-"3306"}
export PROD_DB_USER=${PROD_DB_USER:-"prod_user"}
export PROD_DB_PASSWORD=${PROD_DB_PASSWORD:-"prod_password"}
export PROD_DB_NAME=${PROD_DB_NAME:-"fantasy_football_prod"}

# Sleeper API Configuration
export SLEEPER_LEAGUE_ID=${SLEEPER_LEAGUE_ID:-"your_league_id_here"}
export SLEEPER_USER_ID=${SLEEPER_USER_ID:-"your_user_id_here"}

# Weather API Configuration
export WEATHER_API_KEY=${WEATHER_API_KEY:-"your_weather_api_key_here"}
export WEATHER_API_PROVIDER=${WEATHER_API_PROVIDER:-"openweathermap"}

# AWS Configuration
export AWS_REGION=${AWS_REGION:-"us-east-1"}
export AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-"your_aws_account_id"}
export IMAGE_NAME=${IMAGE_NAME:-"fantasy-football-pipeline"}

# Application Settings
# ENVIRONMENT already set above

echo "Environment variables set for Fantasy Football 2025"
echo "ENVIRONMENT: $ENVIRONMENT"
echo "DEV_DB_NAME: $DEV_DB_NAME"
echo "TEST_DB_NAME: $TEST_DB_NAME"
echo "PROD_DB_NAME: $PROD_DB_NAME"
echo "WEATHER_API_PROVIDER: $WEATHER_API_PROVIDER"
echo ""
echo "To use these variables in your current shell, run:"
echo "source scripts/set_env.sh"
echo ""
echo "To set specific values, export them before sourcing:"
echo "export ENVIRONMENT=PRODUCTION && source scripts/set_env.sh" 