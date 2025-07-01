# Fantasy Football Analytics 2025

A data-driven approach to fantasy football analysis and decision making for the 2025 season with MySQL database backend.

## 🏈 Project Overview

This repository contains comprehensive statistical analysis tools and models for fantasy football, focusing on:
- **Player performance prediction** using machine learning
- **Weekly matchup analysis** with opponent strength ratings
- **Lineup optimization** using linear programming
- **Waiver wire recommendations** with priority scoring
- **Trade value analysis** with market-based valuations
- **Sleeper API integration** for live league data
- **MySQL database** for persistent data storage

## 🏗️ Project Structure

```
├── data/
│   ├── raw/           # Raw data files (CSV, JSON, etc.)
│   ├── processed/     # Cleaned and processed datasets
│   ├── backups/       # Database backups
│   └── external/      # External data sources
├── fantasy_football_2025/  # Main package
│   ├── __init__.py          # Package initialization
│   ├── __main__.py          # Module entry point
│   ├── cli.py               # Command-line interface
│   ├── main.py              # Main application logic
│   ├── sleeper_client.py    # Sleeper API integration
│   ├── lineup_optimizer.py  # Lineup optimization engine
│   ├── trade_analyzer.py    # Trade analysis tools
│   ├── waiver_analyzer.py   # Waiver wire analysis
│   └── database/            # Database models and services
│       ├── __init__.py         # Database package init
│       ├── models.py           # SQLAlchemy database models
│       ├── connection.py       # Database connection management
│       ├── setup.py            # Database setup utilities
│       └── data_service.py     # Data access layer
├── scripts/           # Database and migration scripts
├── notebooks/         # Jupyter notebooks for analysis
├── tests/            # Unit tests
├── pyproject.toml    # Project configuration and dependencies
├── Makefile          # Build and development commands
└── docs/             # Documentation
```

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# Set database credentials and Sleeper league/user IDs
```

### 2. Package Installation & Database Setup

```bash
# Install dependencies and package in development mode
make install-dev

# Set up MySQL database
make db-setup

# Verify database connection
make db-verify

# (Optional) Create sample data for testing
make db-sample
```

### 3. Data Collection

```bash
# Pull all league data from Sleeper (saves to database)
make pull-data LEAGUE_ID=your_league_id USER_ID=your_user_id

# Or use the CLI directly
ff analyze --league-id YOUR_LEAGUE_ID --user-id YOUR_USER_ID --pull-data

# Or use the module
python -m fantasy_football_2025 --league-id YOUR_LEAGUE_ID --user-id YOUR_USER_ID --pull-data
```

### 4. Run Analytics

```bash
# Full analysis suite (after installation)
ff analyze --league-id YOUR_LEAGUE_ID --user-id YOUR_USER_ID --full-analysis

# Individual analysis tools
ff optimize --league-id YOUR_LEAGUE_ID --user-id YOUR_USER_ID
ff trades --league-id YOUR_LEAGUE_ID --user-id YOUR_USER_ID --find-opportunities
ff waiver --league-id YOUR_LEAGUE_ID --user-id YOUR_USER_ID

make optimize      # Lineup optimization
make analyze-trades # Trade opportunities  
make waiver-wire   # Waiver recommendations
```

## 🛠️ Available Commands

### Package Installation
- `make install` - Install dependencies using uv
- `make install-dev` - Install package in development mode
- `uv pip install -e .` - Install package in editable mode
- `uv pip install fantasy-football-2025` - Install released package

### CLI Commands (after installation)
- `ff --help` - Show all available commands
- `ff analyze` - Run comprehensive analysis
- `ff optimize` - Generate optimal lineups
- `ff trades` - Analyze trade opportunities
- `ff waiver` - Get waiver wire recommendations

### Database Management
- `make db-setup` - Initialize database and tables
- `make db-reset` - Reset database (⚠️ deletes all data)
- `make db-verify` - Verify database setup
- `make db-info` - Show database information
- `make backup-db` - Create database backup

### Data Operations
- `make pull-data` - Pull fresh data from Sleeper API
- `make migrate-json` - Import JSON files to database

### SageMaker Pipeline
- `make pipeline-deploy` - Deploy pipeline to SageMaker
- `make pipeline-execute` - Execute pipeline with parameters
- `make pipeline-build-image` - Build and push Docker image to ECR
- `make docker-pipeline` - Run pipeline locally with Docker
- `make aws-test` - Test AWS connectivity

### Analysis Tools (using make)
- `make optimize` - Generate optimal lineups
- `make analyze-trades` - Find trade opportunities
- `make waiver-wire` - Get waiver wire recommendations
- `make run` - Run main CLI application

### Development
- `make format` - Format code with black/isort
- `make check` - Run all checks (lint, type, test)
- `make test` - Run pytest tests

## 🗄️ Database Schema

The MySQL database stores:
- **Leagues**: League settings and configuration
- **Users**: League managers and team information
- **Players**: NFL player master data
- **Rosters**: Team rosters and player ownership
- **PlayerStats**: Historical performance data
- **PlayerProjections**: Future performance predictions
- **Transactions**: Trades, waivers, and free agent moves
- **Matchups**: Weekly head-to-head results
- **TrendingPlayers**: Waiver wire activity tracking

## ☁️ SageMaker Pipeline

The project includes a SageMaker pipeline for automated data collection:

### Pipeline Features
- **Automated data collection** from Sleeper API and NFL data sources
- **Scalable processing** using SageMaker Processing jobs
- **S3 storage** for processed data and metadata
- **Docker containerization** for consistent execution
- **Parameterized execution** for different leagues and weeks

### Quick Pipeline Setup
```bash
# Build and push Docker image
make pipeline-build-image AWS_REGION=us-east-1 AWS_ACCOUNT_ID=123456789012

# Deploy pipeline
make pipeline-deploy LEAGUE_ID=your-league-id USER_ID=your-user-id

# Execute pipeline
make pipeline-execute LEAGUE_ID=your-league-id USER_ID=your-user-id SEASON=2024 WEEK=1
```

See [PIPELINE.md](docs/PIPELINE.md) for detailed documentation.

## 🤖 Core Features

### Lineup Optimization
- **Linear programming** for optimal lineup construction
- **Multiple objectives**: points, ceiling, floor optimization
- **Constraint handling**: position requirements, flex positions
- **PPR scoring** with 2 flex player support

### Trade Analysis
- **Player valuation** using replacement-level calculations
- **Scarcity adjustments** for position-specific value
- **Risk assessment** including injury and schedule factors
- **Counter-offer generation** for failed proposals

### Waiver Wire Intelligence
- **Positional need analysis** based on roster construction
- **Matchup-based scoring** for streaming decisions
- **Ownership trend tracking** from Sleeper data
- **Drop candidate identification** for roster management

### Sleeper Integration
- **Real-time data sync** with automatic database updates
- **League configuration** detection (PPR, flex positions)
- **Transaction history** tracking and analysis
- **Trending player** monitoring

## 📊 Data Sources

- **Sleeper API**: Live league data, player ownership, transactions
- **NFL Data**: Player statistics and game information
- **Internal Models**: Projection algorithms and valuations

## 🔧 Configuration

### Database Configuration (.env)
```bash
# Database connection
DB_HOST=localhost
DB_PORT=3306
DB_USER=fantasy_user
DB_PASSWORD=fantasy_password
DB_NAME=fantasy_football

# Sleeper API
SLEEPER_LEAGUE_ID=your_league_id
SLEEPER_USER_ID=your_user_id
```

### League Requirements
- **Sleeper league** (other platforms not currently supported)
- **PPR scoring** (standard scoring support planned)
- **2 flex positions** (customizable in league settings)

## 🧪 Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Create sample data for testing
make db-sample
```

## 📦 Package Usage

After installation, you can use the package in several ways:

### As a CLI tool:
```bash
ff --help                                    # Show help
ff analyze --league-id XXX --user-id YYY --full-analysis
ff optimize --league-id XXX --user-id YYY --num-lineups 5
```

### As a Python module:
```bash
python -m fantasy_football_2025 --league-id XXX --user-id YYY --pull-data
```

### As a Python package:
```python
from fantasy_football_2025 import SleeperClient, SleeperConfig, LineupOptimizer

# Set up client
config = SleeperConfig(league_id="your_league_id", user_id="your_user_id")
client = SleeperClient(config)

# Create optimizer
optimizer = LineupOptimizer(client)
optimizer.generate_projections()
lineups = optimizer.optimize_lineup()
```

## 📈 Performance

- **Database caching** for improved response times
- **Batch processing** for large data operations
- **Optimized queries** with proper indexing
- **Connection pooling** for database efficiency

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Run `make check` to ensure code quality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.