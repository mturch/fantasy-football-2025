#!/bin/bash
# Environment Variables Setup Script for Fantasy Football 2025
# This script sets up environment variables for the project

# Database Configuration
export DB_HOST=${DB_HOST:-"localhost"}
export DB_PORT=${DB_PORT:-"3306"}
export DB_USER=${DB_USER:-"fantasy_user"}
export DB_PASSWORD=${DB_PASSWORD:-"fantasy_password"}
export DB_NAME=${DB_NAME:-"fantasy_football"}
export DB_ECHO=${DB_ECHO:-"false"}

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
export ENVIRONMENT=${ENVIRONMENT:-"development"}

echo "Environment variables set for Fantasy Football 2025"
echo "DB_HOST: $DB_HOST"
echo "DB_NAME: $DB_NAME"
echo "WEATHER_API_PROVIDER: $WEATHER_API_PROVIDER"
echo "ENVIRONMENT: $ENVIRONMENT"
echo ""
echo "To use these variables in your current shell, run:"
echo "source scripts/set_env.sh"
echo ""
echo "To set specific values, export them before sourcing:"
echo "export WEATHER_API_KEY='your_actual_key' && source scripts/set_env.sh" 