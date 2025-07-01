# Weather API Integration

This document describes the weather API integration functionality for pulling real-time weather data for upcoming games.

## Overview

The weather API integration system pulls current weather and forecast data for NFL stadiums and upcoming games. It supports multiple weather API providers and stores the data in the `historical_data.games_weather` table.

## Supported Weather APIs

### 1. OpenWeatherMap
- **URL**: https://openweathermap.org/
- **Free Tier**: 1,000 calls/day
- **Features**: Current weather, 5-day forecast
- **Rate Limit**: 60 calls/minute

### 2. WeatherAPI.com
- **URL**: https://www.weatherapi.com/
- **Free Tier**: 1,000,000 calls/month
- **Features**: Current weather, 14-day forecast
- **Rate Limit**: 1,000 calls/day

## Setup

### 1. Get API Keys

#### OpenWeatherMap
1. Sign up at https://openweathermap.org/
2. Go to "My API Keys" section
3. Copy your API key

#### WeatherAPI.com
1. Sign up at https://www.weatherapi.com/
2. Go to "API Keys" section
3. Copy your API key

### 2. Environment Configuration

Add your API key to your environment:

```bash
# For OpenWeatherMap
export WEATHER_API_KEY="your_openweathermap_api_key"
export WEATHER_API_PROVIDER="openweathermap"

# For WeatherAPI.com
export WEATHER_API_KEY="your_weatherapi_key"
export WEATHER_API_PROVIDER="weatherapi"
```

Or add to your `.env` file:

```env
WEATHER_API_KEY=your_api_key_here
WEATHER_API_PROVIDER=openweathermap
```

## Usage

### Basic Commands

#### Pull Weather for Upcoming Games
```bash
# Pull weather for games in the next 7 days
make pull-weather-games DAYS_AHEAD=7

# Pull weather for games in the next 3 days
make pull-weather-games DAYS_AHEAD=3
```

#### Pull Weather for All Stadiums
```bash
# Get current weather for all stadiums (useful for testing)
make pull-weather-stadiums
```

#### Pull Current Weather Only
```bash
# Pull current weather for games today (no forecast)
make pull-weather-current
```

#### Pull Weather with Forecast
```bash
# Pull current weather and 7-day forecast for upcoming games
make pull-weather-forecast
```

### Direct Script Usage

```bash
# Basic usage with OpenWeatherMap
uv run python scripts/pull_weather_data.py \
    --api-key "your_api_key" \
    --api-provider openweathermap \
    --days-ahead 7

# Usage with WeatherAPI.com
uv run python scripts/pull_weather_data.py \
    --api-key "your_api_key" \
    --api-provider weatherapi \
    --days-ahead 7

# Pull weather for all stadiums only
uv run python scripts/pull_weather_data.py \
    --api-key "your_api_key" \
    --api-provider openweathermap \
    --stadiums-only

# Current weather only (no forecast)
uv run python scripts/pull_weather_data.py \
    --api-key "your_api_key" \
    --api-provider openweathermap \
    --days-ahead 1 \
    --no-forecast

# Save results to file
uv run python scripts/pull_weather_data.py \
    --api-key "your_api_key" \
    --api-provider openweathermap \
    --days-ahead 7 \
    --output weather_results.json
```

## Data Structure

### Weather Data Fields

The script pulls the following weather data:

- **temperature**: Temperature in Fahrenheit
- **dew_point**: Dew point temperature in Fahrenheit
- **humidity**: Relative humidity percentage
- **precipitation**: Precipitation amount in inches
- **wind_speed**: Wind speed in mph
- **wind_direction**: Wind direction in degrees
- **pressure**: Atmospheric pressure in inches of mercury
- **condition**: Weather condition description
- **timestamp**: Time of weather measurement

### Database Storage

Weather data is stored in the `historical_data.games_weather` table with the following structure:

```sql
INSERT INTO historical_data.games_weather 
(game_id, source, distance_to_station, time_measure, temperature, 
 dew_point, humidity, precipitation, wind_speed, wind_direction, 
 pressure, estimated_condition)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

- **source**: API provider name (e.g., "openweathermap_current", "weatherapi_forecast")
- **game_id**: Links to the games table
- **distance_to_station**: Set to NULL for API data (not available)

## Example Queries

### Get Weather for Specific Game
```sql
SELECT 
    g.game_id,
    g.stadium_name,
    g.time_start_game,
    w.temperature,
    w.humidity,
    w.wind_speed,
    w.estimated_condition,
    w.source
FROM historical_data.games g
JOIN historical_data.games_weather w ON g.game_id = w.game_id
WHERE g.game_id = '2024120100'
ORDER BY w.time_measure;
```

### Compare API Sources
```sql
SELECT 
    source,
    COUNT(*) as records,
    AVG(temperature) as avg_temp,
    AVG(wind_speed) as avg_wind
FROM historical_data.games_weather
WHERE game_id = '2024120100'
GROUP BY source;
```

### Weather Trends for Stadium
```sql
SELECT 
    DATE(time_measure) as date,
    AVG(temperature) as avg_temp,
    AVG(wind_speed) as avg_wind,
    AVG(humidity) as avg_humidity
FROM historical_data.games_weather w
JOIN historical_data.games g ON w.game_id = g.game_id
WHERE g.stadium_name = 'Lambeau Field'
AND w.time_measure >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(time_measure)
ORDER BY date;
```

## Rate Limiting and Best Practices

### Rate Limits
- **OpenWeatherMap**: 60 calls/minute, 1,000 calls/day (free tier)
- **WeatherAPI.com**: 1,000 calls/day (free tier)

### Best Practices
1. **Use appropriate time intervals**: Don't pull data more frequently than needed
2. **Batch requests**: The script includes 1-second delays between requests
3. **Monitor usage**: Check your API usage regularly
4. **Error handling**: The script includes retry logic and error handling

### Recommended Usage Patterns

#### Daily Updates
```bash
# Pull current weather for today's games
make pull-weather-current
```

#### Weekly Planning
```bash
# Pull weather and forecast for the week ahead
make pull-weather-forecast
```

#### Testing
```bash
# Test with stadium data first
make pull-weather-stadiums
```

## Troubleshooting

### Common Issues

1. **API Key Errors**
   - Verify your API key is correct
   - Check if you've exceeded your rate limit
   - Ensure your account is active

2. **No Upcoming Games**
   - Check if there are games in the database for the specified date range
   - Verify the games table has future dates

3. **Database Connection Issues**
   - Ensure MySQL is running
   - Check database credentials
   - Verify the `historical_data` schema exists

4. **Rate Limiting**
   - Reduce the number of requests
   - Increase delays between requests
   - Upgrade your API plan if needed

### Debug Commands

```bash
# Test database connection
make db-verify

# Check upcoming games
uv run python -c "
from scripts.pull_weather_data import WeatherDataPuller
puller = WeatherDataPuller('test_key', 'openweathermap')
puller.connect_database()
games = puller.get_upcoming_games(7)
print(f'Found {len(games)} upcoming games')
"

# Test API connection
uv run python -c "
from scripts.pull_weather_data import OpenWeatherMapClient
client = OpenWeatherMapClient('your_api_key')
weather = client.get_current_weather(40.7128, -74.0060)  # NYC coordinates
print(f'Current weather: {weather}')
"
```

## Integration with Fantasy Football Analysis

The weather data can be used for:

1. **Player Performance Analysis**: Correlate weather conditions with player stats
2. **Game Strategy**: Consider weather impact on game plans
3. **Fantasy Decisions**: Factor weather into lineup decisions
4. **Historical Trends**: Analyze weather patterns over seasons

### Example Analysis Query
```sql
-- Weather impact on passing yards
SELECT 
    CASE 
        WHEN w.wind_speed > 20 THEN 'High Wind'
        WHEN w.wind_speed > 10 THEN 'Moderate Wind'
        ELSE 'Low Wind'
    END as wind_category,
    AVG(passing_yards) as avg_passing_yards,
    COUNT(*) as games
FROM game_stats gs
JOIN historical_data.games_weather w ON gs.game_id = w.game_id
WHERE w.source LIKE '%current%'
GROUP BY wind_category
ORDER BY avg_passing_yards DESC;
``` 