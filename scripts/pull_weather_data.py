#!/usr/bin/env python3
"""
Weather Data Pull Script

This script pulls weather data from a weather API for upcoming games
based on stadium coordinates stored in the MySQL database.

Features:
- Pulls weather data for upcoming games from stadium_coordinates table
- Supports multiple weather APIs (OpenWeatherMap, WeatherAPI, etc.)
- Stores weather data in the historical_data.games_weather table
- Handles rate limiting and error recovery
- Supports both current weather and forecasts
"""

import os
import sys
import requests
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import argparse
import json
from dataclasses import dataclass

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.fantasy_football_2025.database.connection import DatabaseConnection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class WeatherData:
    """Data class for weather information."""
    temperature: Optional[float] = None
    dew_point: Optional[float] = None
    humidity: Optional[int] = None
    precipitation: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[int] = None
    pressure: Optional[float] = None
    condition: Optional[str] = None
    timestamp: Optional[datetime] = None


class WeatherAPIClient:
    """Base class for weather API clients."""
    
    def __init__(self, api_key: str):
        """Initialize with API key."""
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'FantasyFootball2025/1.0'})
    
    def get_current_weather(self, lat: float, lon: float) -> Optional[WeatherData]:
        """Get current weather for coordinates. Override in subclasses."""
        raise NotImplementedError
    
    def get_forecast(self, lat: float, lon: float, days: int = 5) -> List[WeatherData]:
        """Get weather forecast for coordinates. Override in subclasses."""
        raise NotImplementedError


class OpenWeatherMapClient(WeatherAPIClient):
    """OpenWeatherMap API client."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.openweathermap.org/data/2.5"
    
    def get_current_weather(self, lat: float, lon: float) -> Optional[WeatherData]:
        """Get current weather from OpenWeatherMap."""
        try:
            url = f"{self.base_url}/weather"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'imperial'  # Fahrenheit
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return WeatherData(
                temperature=data['main'].get('temp'),
                dew_point=data['main'].get('feels_like'),  # OpenWeatherMap doesn't provide dew point in free tier
                humidity=data['main'].get('humidity'),
                precipitation=data.get('rain', {}).get('1h', 0) if 'rain' in data else 0,
                wind_speed=data['wind'].get('speed'),
                wind_direction=data['wind'].get('deg'),
                pressure=data['main'].get('pressure'),
                condition=data['weather'][0]['description'] if data['weather'] else None,
                timestamp=datetime.fromtimestamp(data['dt'])
            )
            
        except Exception as e:
            logger.error(f"Failed to get current weather from OpenWeatherMap: {e}")
            return None
    
    def get_forecast(self, lat: float, lon: float, days: int = 5) -> List[WeatherData]:
        """Get weather forecast from OpenWeatherMap."""
        try:
            url = f"{self.base_url}/forecast"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'imperial',
                'cnt': min(days * 8, 40)  # 8 forecasts per day, max 40
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            forecasts = []
            for item in data['list']:
                weather = WeatherData(
                    temperature=item['main'].get('temp'),
                    dew_point=item['main'].get('feels_like'),
                    humidity=item['main'].get('humidity'),
                    precipitation=item.get('rain', {}).get('3h', 0) if 'rain' in item else 0,
                    wind_speed=item['wind'].get('speed'),
                    wind_direction=item['wind'].get('deg'),
                    pressure=item['main'].get('pressure'),
                    condition=item['weather'][0]['description'] if item['weather'] else None,
                    timestamp=datetime.fromtimestamp(item['dt'])
                )
                forecasts.append(weather)
            
            return forecasts
            
        except Exception as e:
            logger.error(f"Failed to get forecast from OpenWeatherMap: {e}")
            return []


class WeatherAPIClient(WeatherAPIClient):
    """WeatherAPI.com client (alternative to OpenWeatherMap)."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "http://api.weatherapi.com/v1"
    
    def get_current_weather(self, lat: float, lon: float) -> Optional[WeatherData]:
        """Get current weather from WeatherAPI.com."""
        try:
            url = f"{self.base_url}/current.json"
            params = {
                'key': self.api_key,
                'q': f"{lat},{lon}",
                'aqi': 'no'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            current = data['current']
            return WeatherData(
                temperature=current.get('temp_f'),
                dew_point=current.get('dewpoint_f'),
                humidity=current.get('humidity'),
                precipitation=current.get('precip_in'),
                wind_speed=current.get('wind_mph'),
                wind_direction=current.get('wind_degree'),
                pressure=current.get('pressure_in'),
                condition=current['condition']['text'] if 'condition' in current else None,
                timestamp=datetime.fromisoformat(current['last_updated'].replace('Z', '+00:00'))
            )
            
        except Exception as e:
            logger.error(f"Failed to get current weather from WeatherAPI: {e}")
            return None
    
    def get_forecast(self, lat: float, lon: float, days: int = 5) -> List[WeatherData]:
        """Get weather forecast from WeatherAPI.com."""
        try:
            url = f"{self.base_url}/forecast.json"
            params = {
                'key': self.api_key,
                'q': f"{lat},{lon}",
                'days': min(days, 14),  # Max 14 days
                'aqi': 'no',
                'alerts': 'no'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            forecasts = []
            for day in data['forecast']['forecastday']:
                for hour in day['hour']:
                    weather = WeatherData(
                        temperature=hour.get('temp_f'),
                        dew_point=hour.get('dewpoint_f'),
                        humidity=hour.get('humidity'),
                        precipitation=hour.get('precip_in'),
                        wind_speed=hour.get('wind_mph'),
                        wind_direction=hour.get('wind_degree'),
                        pressure=hour.get('pressure_in'),
                        condition=hour['condition']['text'] if 'condition' in hour else None,
                        timestamp=datetime.fromisoformat(hour['time'].replace('Z', '+00:00'))
                    )
                    forecasts.append(weather)
            
            return forecasts
            
        except Exception as e:
            logger.error(f"Failed to get forecast from WeatherAPI: {e}")
            return []


class WeatherDataPuller:
    """Main class for pulling weather data for upcoming games."""
    
    def __init__(self, api_key: str, api_provider: str = "openweathermap"):
        """Initialize with API configuration."""
        self.api_key = api_key
        self.api_provider = api_provider.lower()
        self.connection = None
        
        # Initialize API client
        if self.api_provider == "openweathermap":
            self.weather_client = OpenWeatherMapClient(api_key)
        elif self.api_provider == "weatherapi":
            self.weather_client = WeatherAPIClient(api_key)
        else:
            raise ValueError(f"Unsupported API provider: {api_provider}")
    
    def connect_database(self) -> None:
        """Connect to the database."""
        try:
            self.connection = DatabaseConnection()
            logger.info("Connected to database successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def get_upcoming_games(self, days_ahead: int = 7) -> List[Dict]:
        """Get upcoming games from the database."""
        try:
            with self.connection.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                # Get games in the next N days
                query = """
                    SELECT 
                        g.game_id,
                        g.stadium_name,
                        g.time_start_game,
                        g.time_end_game,
                        sc.latitude,
                        sc.longitude,
                        sc.home_team
                    FROM historical_data.games g
                    JOIN historical_data.stadium_coordinates sc ON g.stadium_name = sc.stadium_name
                    WHERE g.time_start_game >= NOW()
                    AND g.time_start_game <= DATE_ADD(NOW(), INTERVAL %s DAY)
                    ORDER BY g.time_start_game
                """
                
                cursor.execute(query, (days_ahead,))
                games = cursor.fetchall()
                
                logger.info(f"Found {len(games)} upcoming games in the next {days_ahead} days")
                return games
                
        except Exception as e:
            logger.error(f"Failed to get upcoming games: {e}")
            raise
    
    def get_stadium_coordinates(self) -> List[Dict]:
        """Get all stadium coordinates from the database."""
        try:
            with self.connection.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                query = """
                    SELECT 
                        stadium_name,
                        home_team,
                        latitude,
                        longitude,
                        roof_type
                    FROM historical_data.stadium_coordinates
                    ORDER BY stadium_name
                """
                
                cursor.execute(query)
                stadiums = cursor.fetchall()
                
                logger.info(f"Found {len(stadiums)} stadiums with coordinates")
                return stadiums
                
        except Exception as e:
            logger.error(f"Failed to get stadium coordinates: {e}")
            raise
    
    def save_weather_data(self, game_id: str, weather_data: WeatherData, source: str = "API") -> bool:
        """Save weather data to the database."""
        try:
            with self.connection.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    INSERT INTO historical_data.games_weather 
                    (game_id, source, distance_to_station, time_measure, temperature, 
                     dew_point, humidity, precipitation, wind_speed, wind_direction, 
                     pressure, estimated_condition)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    temperature = VALUES(temperature),
                    dew_point = VALUES(dew_point),
                    humidity = VALUES(humidity),
                    precipitation = VALUES(precipitation),
                    wind_speed = VALUES(wind_speed),
                    wind_direction = VALUES(wind_direction),
                    pressure = VALUES(pressure),
                    estimated_condition = VALUES(estimated_condition)
                """
                
                cursor.execute(query, (
                    game_id,
                    source,
                    None,  # distance_to_station - not available from API
                    weather_data.timestamp,
                    weather_data.temperature,
                    weather_data.dew_point,
                    weather_data.humidity,
                    weather_data.precipitation,
                    weather_data.wind_speed,
                    weather_data.wind_direction,
                    weather_data.pressure,
                    weather_data.condition
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to save weather data for game {game_id}: {e}")
            return False
    
    def pull_weather_for_games(self, days_ahead: int = 7, include_forecast: bool = True) -> Dict:
        """Pull weather data for upcoming games."""
        try:
            logger.info(f"Starting weather data pull for next {days_ahead} days")
            
            # Get upcoming games
            games = self.get_upcoming_games(days_ahead)
            
            if not games:
                logger.info("No upcoming games found")
                return {'games_processed': 0, 'weather_records': 0, 'errors': 0}
            
            results = {
                'games_processed': 0,
                'weather_records': 0,
                'errors': 0,
                'games': []
            }
            
            for game in games:
                try:
                    logger.info(f"Processing weather for game {game['game_id']} at {game['stadium_name']}")
                    
                    game_result = {
                        'game_id': game['game_id'],
                        'stadium': game['stadium_name'],
                        'game_time': game['time_start_game'],
                        'current_weather': None,
                        'forecast_records': 0,
                        'success': False
                    }
                    
                    # Get current weather
                    current_weather = self.weather_client.get_current_weather(
                        game['latitude'], 
                        game['longitude']
                    )
                    
                    if current_weather:
                        game_result['current_weather'] = current_weather
                        if self.save_weather_data(game['game_id'], current_weather, f"{self.api_provider}_current"):
                            results['weather_records'] += 1
                    
                    # Get forecast if requested
                    if include_forecast:
                        forecasts = self.weather_client.get_forecast(
                            game['latitude'], 
                            game['longitude'], 
                            days=min(days_ahead, 5)
                        )
                        
                        for forecast in forecasts:
                            if self.save_weather_data(game['game_id'], forecast, f"{self.api_provider}_forecast"):
                                results['weather_records'] += 1
                                game_result['forecast_records'] += 1
                    
                    game_result['success'] = True
                    results['games_processed'] += 1
                    
                    # Rate limiting - be nice to the API
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Failed to process weather for game {game['game_id']}: {e}")
                    results['errors'] += 1
                
                results['games'].append(game_result)
            
            logger.info(f"Weather pull completed: {results['games_processed']} games, {results['weather_records']} records, {results['errors']} errors")
            return results
            
        except Exception as e:
            logger.error(f"Failed to pull weather data: {e}")
            raise
    
    def pull_weather_for_stadiums(self, include_forecast: bool = False) -> Dict:
        """Pull current weather for all stadiums (useful for testing)."""
        try:
            logger.info("Starting weather data pull for all stadiums")
            
            # Get all stadium coordinates
            stadiums = self.get_stadium_coordinates()
            
            results = {
                'stadiums_processed': 0,
                'weather_records': 0,
                'errors': 0,
                'stadiums': []
            }
            
            for stadium in stadiums:
                try:
                    logger.info(f"Processing weather for {stadium['stadium_name']}")
                    
                    stadium_result = {
                        'stadium_name': stadium['stadium_name'],
                        'home_team': stadium['home_team'],
                        'roof_type': stadium['roof_type'],
                        'current_weather': None,
                        'success': False
                    }
                    
                    # Get current weather
                    current_weather = self.weather_client.get_current_weather(
                        stadium['latitude'], 
                        stadium['longitude']
                    )
                    
                    if current_weather:
                        stadium_result['current_weather'] = current_weather
                        # Note: We don't save this to games_weather table since it's not tied to a specific game
                        results['weather_records'] += 1
                    
                    stadium_result['success'] = True
                    results['stadiums_processed'] += 1
                    
                    # Rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Failed to process weather for {stadium['stadium_name']}: {e}")
                    results['errors'] += 1
                
                results['stadiums'].append(stadium_result)
            
            logger.info(f"Stadium weather pull completed: {results['stadiums_processed']} stadiums, {results['weather_records']} records, {results['errors']} errors")
            return results
            
        except Exception as e:
            logger.error(f"Failed to pull stadium weather data: {e}")
            raise


def main():
    """Main function for CLI usage."""
    parser = argparse.ArgumentParser(description="Pull weather data for upcoming games")
    parser.add_argument(
        "--api-key", 
        required=True,
        help="Weather API key"
    )
    parser.add_argument(
        "--api-provider", 
        default="openweathermap",
        choices=["openweathermap", "weatherapi"],
        help="Weather API provider"
    )
    parser.add_argument(
        "--days-ahead", 
        type=int,
        default=7,
        help="Number of days ahead to pull weather for"
    )
    parser.add_argument(
        "--stadiums-only", 
        action="store_true",
        help="Pull weather for all stadiums instead of upcoming games"
    )
    parser.add_argument(
        "--no-forecast", 
        action="store_true",
        help="Skip forecast data, only get current weather"
    )
    parser.add_argument(
        "--output", 
        help="Output file for results (JSON format)"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize weather puller
        puller = WeatherDataPuller(args.api_key, args.api_provider)
        
        # Connect to database
        puller.connect_database()
        
        # Pull weather data
        if args.stadiums_only:
            results = puller.pull_weather_for_stadiums(include_forecast=not args.no_forecast)
        else:
            results = puller.pull_weather_for_games(
                days_ahead=args.days_ahead,
                include_forecast=not args.no_forecast
            )
        
        # Print summary
        if args.stadiums_only:
            print(f"\n=== Stadium Weather Results ===")
            print(f"Stadiums processed: {results['stadiums_processed']}")
            print(f"Weather records: {results['weather_records']}")
            print(f"Errors: {results['errors']}")
            
            # Show sample data
            for stadium in results['stadiums'][:5]:  # Show first 5
                if stadium['current_weather']:
                    w = stadium['current_weather']
                    print(f"\n{stadium['stadium_name']} ({stadium['home_team']}):")
                    print(f"  Temperature: {w.temperature}°F")
                    print(f"  Humidity: {w.humidity}%")
                    print(f"  Wind: {w.wind_speed} mph")
                    print(f"  Condition: {w.condition}")
        else:
            print(f"\n=== Game Weather Results ===")
            print(f"Games processed: {results['games_processed']}")
            print(f"Weather records: {results['weather_records']}")
            print(f"Errors: {results['errors']}")
            
            # Show sample data
            for game in results['games'][:3]:  # Show first 3
                if game['current_weather']:
                    w = game['current_weather']
                    print(f"\n{game['game_id']} at {game['stadium']}:")
                    print(f"  Game time: {game['game_time']}")
                    print(f"  Temperature: {w.temperature}°F")
                    print(f"  Humidity: {w.humidity}%")
                    print(f"  Wind: {w.wind_speed} mph")
                    print(f"  Condition: {w.condition}")
                    print(f"  Forecast records: {game['forecast_records']}")
        
        # Save results to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nResults saved to {args.output}")
        
        print(f"\n✅ Weather data pull completed successfully!")
        print(f"API Provider: {args.api_provider}")
        
    except Exception as e:
        logger.error(f"Weather pull failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 