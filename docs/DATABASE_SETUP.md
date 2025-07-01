# Database Setup Guide

This guide walks you through setting up the MySQL database from scratch for the Fantasy Football 2025 analytics project.

## Overview

The project uses MySQL to store:
- Historical game data
- Weather information
- Stadium coordinates
- Player statistics
- Fantasy football data

## Prerequisites

### Required Software

1. **MySQL Server** (8.0 or higher recommended)
   - [MySQL Community Server](https://dev.mysql.com/downloads/mysql/)
   - [MySQL Workbench](https://dev.mysql.com/downloads/workbench/) (optional, for GUI)

2. **Python Dependencies**
   ```bash
   uv sync
   ```

### System Requirements

- **RAM**: Minimum 2GB, recommended 4GB+
- **Storage**: At least 1GB free space
- **OS**: macOS, Linux, or Windows

## Installation

### 1. Install MySQL Server

#### macOS (using Homebrew)
```bash
# Install MySQL
brew install mysql

# Start MySQL service
brew services start mysql

# Secure the installation
mysql_secure_installation
```

#### Ubuntu/Debian
```bash
# Update package list
sudo apt update

# Install MySQL
sudo apt install mysql-server

# Start MySQL service
sudo systemctl start mysql
sudo systemctl enable mysql

# Secure the installation
sudo mysql_secure_installation
```

#### Windows
1. Download MySQL Installer from [MySQL Downloads](https://dev.mysql.com/downloads/installer/)
2. Run the installer and follow the setup wizard
3. Choose "Server only" or "Custom" installation
4. Set root password during installation

### 2. Verify MySQL Installation

```bash
# Check MySQL version
mysql --version

# Connect to MySQL as root
mysql -u root -p
```

## Database Setup

### 1. Create Database and User

Connect to MySQL as root and run the following commands:

```sql
-- Create the database
CREATE DATABASE fantasy_football CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create a dedicated user for the application
CREATE USER 'fantasy_user'@'localhost' IDENTIFIED BY 'your_secure_password';

-- Grant privileges to the user
GRANT ALL PRIVILEGES ON fantasy_football.* TO 'fantasy_user'@'localhost';
GRANT ALL PRIVILEGES ON fantasy_football.* TO 'fantasy_user'@'127.0.0.1';

-- Create the historical_data schema
CREATE DATABASE historical_data CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON historical_data.* TO 'fantasy_user'@'localhost';
GRANT ALL PRIVILEGES ON historical_data.* TO 'fantasy_user'@'127.0.0.1';

-- Apply changes
FLUSH PRIVILEGES;

-- Verify the setup
SHOW DATABASES;
SELECT User, Host FROM mysql.user WHERE User = 'fantasy_user';
```

### 2. Test Database Connection

```bash
# Test connection with the new user
mysql -u fantasy_user -p fantasy_football

# Or test from Python
uv run python -c "
from src.fantasy_football_2025.database.connection import DatabaseConnection
conn = DatabaseConnection()
print('Database connection successful!')
"
```

## Environment Configuration

### 1. Set Environment Variables

Create or update your `.env` file:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=fantasy_user
DB_PASSWORD=your_secure_password
DB_NAME=fantasy_football
DB_ECHO=false

# Application Settings
ENVIRONMENT=development
```

### 2. Test Environment Setup

```bash
# Test environment variables
make env-test

# Test database connection
make db-verify
```

## Schema Setup

### 1. Run Database Setup Script

```bash
# Set up the database schema
make db-setup

# Or run manually
uv run python scripts/setup_database.py --setup
```

### 2. Verify Schema Creation

```sql
-- Connect to the database
mysql -u fantasy_user -p fantasy_football

-- Check tables
SHOW TABLES;

-- Check historical_data schema
USE historical_data;
SHOW TABLES;
```

## Data Import

### 1. Import Historical Data

```bash
# Import weather and game data
make import-historical

# Or run manually
uv run python scripts/import_historical_data.py --data-dir data/external/weather --schema historical_data
```

### 2. Verify Data Import

```bash
# Validate imported data
make import-historical-validate

# Or run manually
uv run python scripts/import_historical_data.py --data-dir data/external/weather --schema historical_data --validate-only
```

## Database Maintenance

### 1. Backup Database

```bash
# Create backup
make backup-db

# Or manually
mysqldump -u fantasy_user -p fantasy_football > backup_fantasy_football.sql
mysqldump -u fantasy_user -p historical_data > backup_historical_data.sql
```

### 2. Restore Database

```bash
# Restore from backup
mysql -u fantasy_user -p fantasy_football < backup_fantasy_football.sql
mysql -u fantasy_user -p historical_data < backup_historical_data.sql
```

### 3. Reset Database (Development)

```bash
# Reset database (WARNING: This will delete all data)
make db-reset

# Or manually
uv run python scripts/setup_database.py --reset
```

## Performance Optimization

### 1. MySQL Configuration

Edit `/etc/mysql/mysql.conf.d/mysqld.cnf` MySQL configuration file:

```ini
[mysqld]
# Increase buffer sizes for better performance
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
innodb_log_buffer_size = 64M

# Optimize for read-heavy workloads
innodb_read_io_threads = 8
innodb_write_io_threads = 8

# Enable query cache
query_cache_type = 1
query_cache_size = 128M
query_cache_limit = 2M
```

### 2. Index Optimization

```sql
-- Add indexes for better query performance
USE fantasy_football;

-- Index on game_id for joins
CREATE INDEX idx_games_game_id ON games(game_id);
CREATE INDEX idx_weather_game_id ON games_weather(game_id);

-- Index on dates for time-based queries
CREATE INDEX idx_games_date ON games(time_start_game);
CREATE INDEX idx_weather_date ON games_weather(time_measure);

-- Index on stadium for location-based queries
CREATE INDEX idx_games_stadium ON games(stadium_name);
```

## Troubleshooting

### Common Issues

#### 1. Connection Refused
```bash
# Check if MySQL is running
brew services list | grep mysql  # macOS

# Start MySQL if not running
brew services start mysql  # macOS
```

#### 2. Access Denied
```bash
# Reset MySQL root password
sudo mysql -u root
ALTER USER 'root'@'localhost' IDENTIFIED BY 'new_password';
FLUSH PRIVILEGES;
```

#### 3. Character Set Issues
```sql
-- Check character set
SHOW VARIABLES LIKE 'character_set%';

-- Set proper character set
SET NAMES utf8mb4;
```

#### 4. Port Already in Use
```bash
# Check what's using port 3306
sudo lsof -i :3306

# Kill the process if needed
sudo kill -9 <PID>
```

### Debug Commands

```bash
# Test database connection
make db-verify

# Show database info
make db-info

# Check environment variables
make env-show

# Test with sample data
make db-sample
```

## Security Best Practices

### 1. User Permissions
- Use dedicated database user (not root)
- Grant minimal required privileges
- Use strong passwords

### 2. Network Security
- Bind MySQL to localhost only
- Use SSL connections in production
- Firewall port 3306

### 3. Data Protection
- Regular backups
- Encrypt sensitive data
- Monitor access logs

## Production Deployment

### 1. Production Configuration

```env
# Production environment variables
DB_HOST=your_production_host
DB_PORT=3306
DB_USER=fantasy_prod_user
DB_PASSWORD=your_secure_production_password
DB_NAME=fantasy_football_prod
DB_ECHO=false
ENVIRONMENT=production
```

### 2. High Availability
- Set up MySQL replication
- Use connection pooling
- Implement failover mechanisms

### 3. Monitoring
- Set up database monitoring
- Monitor query performance
- Track disk usage

## Next Steps

1. **Test the setup**: Run `make db-verify`
2. **Import sample data**: Run `make db-sample`
3. **Start development**: Begin working on database features
4. **Set up monitoring**: Configure database monitoring tools

## Additional Resources

- [MySQL Documentation](https://dev.mysql.com/doc/)
- [MySQL Performance Tuning](https://dev.mysql.com/doc/refman/8.0/en/optimization.html)
- [Database Design Best Practices](https://dev.mysql.com/doc/refman/8.0/en/optimization-best-practices.html)

## Multi-Environment Database Support

This project supports separate databases for development, testing, and production.

### How to Configure

1. Set the `ENVIRONMENT` variable to `DEV`, `TEST`, or `PRODUCTION` in your `.env` or shell.
2. Set the corresponding database variables for each environment:

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

### How to Use

- The application will automatically use the correct database based on the `ENVIRONMENT` variable.
- To switch environments, change `ENVIRONMENT` and reload your environment variables:

```bash
export ENVIRONMENT=TEST && source scripts/set_env.sh
```

- This allows you to safely test and develop without affecting production data.

See `docs/ENVIRONMENT_SETUP.md` and `scripts/set_env.sh` for more details. 