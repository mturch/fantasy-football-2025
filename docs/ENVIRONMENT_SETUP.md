# Environment Variables Setup

This document explains how to set up environment variables for the Fantasy Football 2025 project using uv.

## Overview

The project uses environment variables for configuration including database connections, API keys, and application settings. There are several ways to manage these with uv.

## Environment Variables

### Required Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DB_HOST` | Database host | localhost | Yes |
| `DB_PORT` | Database port | 3306 | Yes |
| `DB_USER` | Database username | fantasy_user | Yes |
| `DB_PASSWORD` | Database password | fantasy_password | Yes |
| `DB_NAME` | Database name | fantasy_football | Yes |
| `DB_ECHO` | Enable SQL logging | false | No |

### API Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SLEEPER_LEAGUE_ID` | Sleeper API league ID | - | Yes |
| `SLEEPER_USER_ID` | Sleeper API user ID | - | Yes |
| `WEATHER_API_KEY` | Weather API key | - | Yes |
| `WEATHER_API_PROVIDER` | Weather API provider | openweathermap | No |

### AWS Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `AWS_REGION` | AWS region | us-east-1 | No |
| `AWS_ACCOUNT_ID` | AWS account ID | - | No |
| `IMAGE_NAME` | Docker image name | fantasy-football-pipeline | No |

### Application Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Application environment | development | No |

## Setup Methods

### Method 1: .env File (Recommended)

Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env

# Edit with your actual values
nano .env
```

Example `.env` file:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=fantasy_user
DB_PASSWORD=your_secure_password
DB_NAME=fantasy_football
DB_ECHO=false

# Sleeper API Configuration
SLEEPER_LEAGUE_ID=your_actual_league_id
SLEEPER_USER_ID=your_actual_user_id

# Weather API Configuration
WEATHER_API_KEY=your_weather_api_key
WEATHER_API_PROVIDER=openweathermap

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=your_aws_account_id
IMAGE_NAME=fantasy-football-pipeline

# Application Settings
ENVIRONMENT=development
```

### Method 2: pyproject.toml Configuration

Environment variables are already configured in `pyproject.toml` under `[tool.uv.env]`. You can modify these values directly in the file.

### Method 3: Shell Script

Use the provided shell script:

```bash
# Set up environment variables
source scripts/set_env.sh

# Or with custom values
export WEATHER_API_KEY="your_key" && source scripts/set_env.sh
```

### Method 4: Makefile Commands

Use the provided Makefile targets:

```bash
# Set up environment variables
make env-setup

# Show current environment variables
make env-show

# Test environment configuration
make env-test
```

## Usage with uv

### Running Scripts with Environment Variables

```bash
# Environment variables are automatically loaded when using uv run
uv run python scripts/pull_weather_data.py --api-key $WEATHER_API_KEY

# Or use the Makefile targets which handle environment setup
make pull-weather-games DAYS_AHEAD=7
```

### Development Environment

```bash
# Install dependencies
uv sync

# Run with environment variables
uv run python -m fantasy_football_2025.main

# Or use the environment setup script first
source scripts/set_env.sh
uv run python -m fantasy_football_2025.main
```

## Getting API Keys

### Weather API Keys

#### OpenWeatherMap
1. Sign up at https://openweathermap.org/
2. Go to "My API Keys" section
3. Copy your API key

#### WeatherAPI.com
1. Sign up at https://www.weatherapi.com/
2. Go to "API Keys" section
3. Copy your API key

### Sleeper API

1. Go to https://sleeper.com/
2. Log in to your account
3. Find your league ID in the URL: `https://sleeper.com/leagues/YOUR_LEAGUE_ID`
4. Find your user ID in your profile settings

## Security Best Practices

### 1. Never Commit Sensitive Data

```bash
# Ensure .env is in .gitignore
echo ".env" >> .gitignore

# Use .env.example for templates
cp .env.example .env
```

### 2. Use Strong Passwords

```bash
# Generate a secure database password
openssl rand -base64 32

# Use it in your .env file
DB_PASSWORD=your_generated_password
```

### 3. Environment-Specific Configuration

```bash
# Development
ENVIRONMENT=development
DB_ECHO=true

# Production
ENVIRONMENT=production
DB_ECHO=false
```

## Troubleshooting

### Common Issues

1. **Environment Variables Not Loading**
   ```bash
   # Check if .env file exists
   ls -la .env
   
   # Verify environment variables are set
   make env-show
   ```

2. **Database Connection Issues**
   ```bash
   # Test database connection
   make db-verify
   
   # Check environment variables
   echo $DB_HOST $DB_NAME $DB_USER
   ```

3. **API Key Issues**
   ```bash
   # Test weather API
   make pull-weather-stadiums
   
   # Check API key is set
   echo $WEATHER_API_KEY
   ```

### Debug Commands

```bash
# Show all environment variables
env | grep -E "(DB_|SLEEPER_|WEATHER_|AWS_)"

# Test specific functionality
make env-test
make db-verify
make pull-weather-stadiums
```

## Integration with CI/CD

For continuous integration, set environment variables in your CI system:

```yaml
# GitHub Actions example
env:
  DB_HOST: ${{ secrets.DB_HOST }}
  DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
  WEATHER_API_KEY: ${{ secrets.WEATHER_API_KEY }}
  SLEEPER_LEAGUE_ID: ${{ secrets.SLEEPER_LEAGUE_ID }}
```

## Next Steps

1. Create your `.env` file with actual values
2. Test the environment setup: `make env-test`
3. Verify database connection: `make db-verify`
4. Test weather API: `make pull-weather-stadiums`
5. Start using the application: `make run`

## Multi-Environment Database Support

This project supports separate database configurations for development, testing, and production environments.

### Environment Variables

Set the `ENVIRONMENT` variable to one of:
- `DEV`
- `TEST`
- `PRODUCTION`

Example in `.env`:
```env
ENVIRONMENT=DEV
```

Each environment uses its own set of variables:

```env
# DEV Database
DEV_DB_HOST=localhost
DEV_DB_PORT=3306
DEV_DB_USER=fantasy_user
DEV_DB_PASSWORD=fantasy_password
DEV_DB_NAME=fantasy_football_dev

# TEST Database
TEST_DB_HOST=localhost
TEST_DB_PORT=3306
TEST_DB_USER=fantasy_user
TEST_DB_PASSWORD=fantasy_password
TEST_DB_NAME=fantasy_football_test

# PRODUCTION Database
PROD_DB_HOST=prod-db-host
PROD_DB_PORT=3306
PROD_DB_USER=prod_user
PROD_DB_PASSWORD=prod_password
PROD_DB_NAME=fantasy_football_prod
```

### How It Works
- The application reads the `ENVIRONMENT` variable.
- It uses the corresponding database credentials for all connections.
- Change `ENVIRONMENT` to switch between databases.

### Example Usage

```bash
# Use DEV database
export ENVIRONMENT=DEV && source scripts/set_env.sh

# Use TEST database
export ENVIRONMENT=TEST && source scripts/set_env.sh

# Use PRODUCTION database
export ENVIRONMENT=PRODUCTION && source scripts/set_env.sh
```

You can also set these in your `.env` file for persistent configuration.

See `scripts/set_env.sh` for details. 