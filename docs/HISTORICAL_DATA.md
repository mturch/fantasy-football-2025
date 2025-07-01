# Historical Data Import

This document describes the historical data import functionality for the Fantasy Football Analytics project.

## Overview

The historical data import system imports weather and game data from CSV files into a MySQL database with a `historical_data` schema.

## Data Files

The import system processes three CSV files:

### 1. `games.csv`
Contains game scheduling and basic information:
- **game_id**: Unique game identifier
- **Season**: NFL season year
- **StadiumName**: Stadium where game was played
- **TimeStartGame**: Game start time
- **TimeEndGame**: Game end time
- **TZOffset**: Timezone offset

### 2. `stadium_coordinates.csv`
Contains stadium location and characteristics:
- **StadiumName**: Stadium name
- **HomeTeam**: NFL team that calls this stadium home
- **RoofType**: Indoor, Outdoor, or Retractable
- **Longitude**: Geographic longitude
- **Latitude**: Geographic latitude
- **StadiumAzimuthAngle**: Stadium orientation angle

### 3. `games_weather.csv`
Contains detailed weather conditions during games:
- **game_id**: Links to games table
- **Source**: Weather data source (e.g., Meteostat)
- **DistanceToStation**: Distance to weather station
- **TimeMeasure**: Time of weather measurement
- **Temperature**: Temperature in Fahrenheit
- **DewPoint**: Dew point temperature
- **Humidity**: Relative humidity percentage
- **Precipitation**: Precipitation amount
- **WindSpeed**: Wind speed in mph
- **WindDirection**: Wind direction in degrees
- **Pressure**: Atmospheric pressure
- **EstimatedCondition**: Weather condition description

## Database Schema

The import creates a `historical_data` schema with three tables:

### `games` Table
```sql
CREATE TABLE historical_data.games (
    game_id VARCHAR(20) PRIMARY KEY,
    season INT NOT NULL,
    stadium_name VARCHAR(100) NOT NULL,
    time_start_game DATETIME NOT NULL,
    time_end_game DATETIME NOT NULL,
    tz_offset INT NOT NULL
);
```

### `stadium_coordinates` Table
```sql
CREATE TABLE historical_data.stadium_coordinates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stadium_name VARCHAR(100) NOT NULL,
    home_team VARCHAR(10) NOT NULL,
    roof_type VARCHAR(20) NOT NULL,
    longitude DECIMAL(10, 8) NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    stadium_azimuth_angle DECIMAL(5, 2),
    UNIQUE KEY unique_stadium (stadium_name)
);
```

### `games_weather` Table
```sql
CREATE TABLE historical_data.games_weather (
    id INT AUTO_INCREMENT PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    source VARCHAR(50) NOT NULL,
    distance_to_station DECIMAL(8, 2),
    time_measure DATETIME NOT NULL,
    temperature DECIMAL(5, 2),
    dew_point DECIMAL(5, 2),
    humidity INT,
    precipitation DECIMAL(8, 4),
    wind_speed DECIMAL(6, 2),
    wind_direction INT,
    pressure DECIMAL(8, 4),
    estimated_condition VARCHAR(50)
);
```

## Usage

### Basic Import

Import all historical data with default settings:

```bash
make import-historical
```

### Validate Existing Data

Check existing data without importing:

```bash
make import-historical-validate
```

### Custom Import

Import with custom parameters:

```bash
make import-historical-custom DATA_DIR=/path/to/data SCHEMA=my_schema BATCH_SIZE=500
```

### Test Data Files

Examine data files before import:

```bash
make test-historical-data
```

### Direct Script Usage

```bash
# Basic import
uv run python scripts/import_historical_data.py

# Custom data directory
uv run python scripts/import_historical_data.py --data-dir /custom/path

# Custom schema name
uv run python scripts/import_historical_data.py --schema my_schema

# Validate only
uv run python scripts/import_historical_data.py --validate-only

# Custom batch size for large files
uv run python scripts/import_historical_data.py --batch-size 2000
```

## Example Queries

### Basic Weather Analysis

```sql
-- Get weather conditions for a specific game
SELECT 
    g.game_id,
    g.stadium_name,
    g.time_start_game,
    w.temperature,
    w.wind_speed,
    w.estimated_condition
FROM historical_data.games g
JOIN historical_data.games_weather w ON g.game_id = w.game_id
WHERE g.game_id = '2023120100'
ORDER BY w.time_measure;
```

### Stadium Weather Patterns

```sql
-- Average temperature by stadium
SELECT 
    g.stadium_name,
    sc.roof_type,
    AVG(w.temperature) as avg_temp,
    COUNT(DISTINCT g.game_id) as games
FROM historical_data.games g
JOIN historical_data.games_weather w ON g.game_id = w.game_id
JOIN historical_data.stadium_coordinates sc ON g.stadium_name = sc.stadium_name
GROUP BY g.stadium_name, sc.roof_type
ORDER BY avg_temp DESC;
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Ensure MySQL is running
   - Check database credentials in `.env` file
   - Verify database user has CREATE privileges

2. **File Not Found Errors**
   - Check that CSV files exist in `data/external/weather/`
   - Verify file permissions
   - Ensure files are not corrupted

3. **Memory Issues with Large Files**
   - Reduce batch size: `--batch-size 500`
   - Ensure sufficient system memory

### Debug Commands

```bash
# Test database connection
make db-verify

# Check file structure
make test-historical-data

# Validate existing data
make import-historical-validate
``` 