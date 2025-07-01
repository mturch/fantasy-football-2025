#!/usr/bin/env python3
"""
Historical Data Import Script

This script imports weather data from CSV files into MySQL database
with a historical_data schema.

Files to import:
- games.csv: Game information and scheduling
- stadium_coordinates.csv: Stadium locations and characteristics
- games_weather.csv: Detailed weather conditions during games
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.fantasy_football_2025.database.connection import DatabaseConnection
from src.fantasy_football_2025.database.setup import create_database_if_not_exists

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HistoricalDataImporter:
    """Imports historical data from CSV files to MySQL database."""

    def __init__(self, db_config: Optional[Dict] = None):
        """Initialize the importer with database configuration."""
        self.db_config = db_config or {}
        self.connection = None
        self.schema_name = "historical_data"

    def connect_database(self) -> None:
        """Connect to the database and create schema if needed."""
        try:
            # Create database connection
            self.connection = DatabaseConnection()

            # Create schema if it doesn't exist
            create_database_if_not_exists(self.connection, self.schema_name)

            logger.info(
                f"Connected to database and ensured schema '{self.schema_name}' exists"
            )

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def create_tables(self) -> None:
        """Create the historical data tables."""
        try:
            with self.connection.get_connection() as conn:
                cursor = conn.cursor()

                # Create games table
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.schema_name}.games (
                        game_id VARCHAR(20) PRIMARY KEY,
                        season INT NOT NULL,
                        stadium_name VARCHAR(100) NOT NULL,
                        time_start_game DATETIME NOT NULL,
                        time_end_game DATETIME NOT NULL,
                        tz_offset INT NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
                )

                # Create stadium_coordinates table
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.schema_name}.stadium_coordinates (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        stadium_name VARCHAR(100) NOT NULL,
                        home_team VARCHAR(10) NOT NULL,
                        roof_type VARCHAR(20) NOT NULL,
                        longitude DECIMAL(10, 8) NOT NULL,
                        latitude DECIMAL(10, 8) NOT NULL,
                        stadium_azimuth_angle DECIMAL(5, 2),
                        UNIQUE KEY unique_stadium (stadium_name)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
                )

                # Create games_weather table
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.schema_name}.games_weather (
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
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
                )

                conn.commit()
                logger.info("Historical data tables created successfully")

        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    def import_games_data(self, file_path: str) -> int:
        """Import games data from CSV file."""
        try:
            logger.info(f"Importing games data from {file_path}")

            # Read CSV file
            df = pd.read_csv(file_path)
            logger.info(f"Loaded {len(df)} games records")

            # Clean and prepare data
            df["time_start_game"] = pd.to_datetime(df["TimeStartGame"])
            df["time_end_game"] = pd.to_datetime(df["TimeEndGame"])
            df["season"] = df["Season"].astype(int)
            df["tz_offset"] = df["TZOffset"].astype(int)

            # Insert data into database
            with self.connection.get_connection() as conn:
                cursor = conn.cursor()

                for _, row in df.iterrows():
                    cursor.execute(
                        f"""
                        INSERT INTO {self.schema_name}.games 
                        (game_id, season, stadium_name, time_start_game, time_end_game, tz_offset)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        season = VALUES(season),
                        stadium_name = VALUES(stadium_name),
                        time_start_game = VALUES(time_start_game),
                        time_end_game = VALUES(time_end_game),
                        tz_offset = VALUES(tz_offset)
                    """,
                        (
                            row["game_id"],
                            row["season"],
                            row["StadiumName"],
                            row["time_start_game"],
                            row["time_end_game"],
                            row["tz_offset"],
                        ),
                    )

                conn.commit()
                logger.info(f"Successfully imported {len(df)} games records")
                return len(df)

        except Exception as e:
            logger.error(f"Failed to import games data: {e}")
            raise

    def import_stadium_coordinates(self, file_path: str) -> int:
        """Import stadium coordinates data from CSV file."""
        try:
            logger.info(f"Importing stadium coordinates from {file_path}")

            # Read CSV file
            df = pd.read_csv(file_path)
            logger.info(f"Loaded {len(df)} stadium records")

            # Clean and prepare data
            df["longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
            df["latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
            df["stadium_azimuth_angle"] = pd.to_numeric(
                df["StadiumAzimuthAngle"], errors="coerce"
            )

            # Insert data into database
            with self.connection.get_connection() as conn:
                cursor = conn.cursor()

                for _, row in df.iterrows():
                    cursor.execute(
                        f"""
                        INSERT INTO {self.schema_name}.stadium_coordinates 
                        (stadium_name, home_team, roof_type, longitude, latitude, stadium_azimuth_angle)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        home_team = VALUES(home_team),
                        roof_type = VALUES(roof_type),
                        longitude = VALUES(longitude),
                        latitude = VALUES(latitude),
                        stadium_azimuth_angle = VALUES(stadium_azimuth_angle)
                    """,
                        (
                            row["StadiumName"],
                            row["HomeTeam"],
                            row["RoofType"],
                            row["longitude"],
                            row["latitude"],
                            row["stadium_azimuth_angle"],
                        ),
                    )

                conn.commit()
                logger.info(f"Successfully imported {len(df)} stadium records")
                return len(df)

        except Exception as e:
            logger.error(f"Failed to import stadium coordinates: {e}")
            raise

    def import_games_weather(self, file_path: str, batch_size: int = 1000) -> int:
        """Import games weather data from CSV file in batches."""
        try:
            logger.info(f"Importing games weather data from {file_path}")

            # Read CSV file in chunks to handle large files
            total_records = 0

            for chunk_num, df_chunk in enumerate(
                pd.read_csv(file_path, chunksize=batch_size)
            ):
                logger.info(
                    f"Processing chunk {chunk_num + 1} with {len(df_chunk)} records"
                )

                # Clean and prepare data
                df_chunk["time_measure"] = pd.to_datetime(df_chunk["TimeMeasure"])
                df_chunk["temperature"] = pd.to_numeric(
                    df_chunk["Temperature"], errors="coerce"
                )
                df_chunk["dew_point"] = pd.to_numeric(
                    df_chunk["DewPoint"], errors="coerce"
                )
                df_chunk["humidity"] = pd.to_numeric(
                    df_chunk["Humidity"], errors="coerce"
                )
                df_chunk["precipitation"] = pd.to_numeric(
                    df_chunk["Precipitation"], errors="coerce"
                )
                df_chunk["wind_speed"] = pd.to_numeric(
                    df_chunk["WindSpeed"], errors="coerce"
                )
                df_chunk["wind_direction"] = pd.to_numeric(
                    df_chunk["WindDirection"], errors="coerce"
                )
                df_chunk["pressure"] = pd.to_numeric(
                    df_chunk["Pressure"], errors="coerce"
                )
                df_chunk["distance_to_station"] = pd.to_numeric(
                    df_chunk["DistanceToStation"], errors="coerce"
                )

                # Insert data into database
                with self.connection.get_connection() as conn:
                    cursor = conn.cursor()

                    for _, row in df_chunk.iterrows():
                        cursor.execute(
                            f"""
                            INSERT INTO {self.schema_name}.games_weather 
                            (game_id, source, distance_to_station, time_measure, temperature, 
                             dew_point, humidity, precipitation, wind_speed, wind_direction, 
                             pressure, estimated_condition)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                            (
                                row["game_id"],
                                row["Source"],
                                row["distance_to_station"],
                                row["time_measure"],
                                row["temperature"],
                                row["dew_point"],
                                row["humidity"],
                                row["precipitation"],
                                row["wind_speed"],
                                row["wind_direction"],
                                row["pressure"],
                                row["EstimatedCondition"],
                            ),
                        )

                    conn.commit()
                    total_records += len(df_chunk)
                    logger.info(f"Processed {total_records} weather records so far")

            logger.info(f"Successfully imported {total_records} weather records")
            return total_records

        except Exception as e:
            logger.error(f"Failed to import games weather data: {e}")
            raise

    def validate_data(self) -> Dict[str, int]:
        """Validate imported data and return record counts."""
        try:
            with self.connection.get_connection() as conn:
                cursor = conn.cursor()

                # Get record counts
                cursor.execute(f"SELECT COUNT(*) FROM {self.schema_name}.games")
                games_count = cursor.fetchone()[0]

                cursor.execute(
                    f"SELECT COUNT(*) FROM {self.schema_name}.stadium_coordinates"
                )
                stadiums_count = cursor.fetchone()[0]

                cursor.execute(f"SELECT COUNT(*) FROM {self.schema_name}.games_weather")
                weather_count = cursor.fetchone()[0]

                # Get some sample data for validation
                cursor.execute(
                    f"""
                    SELECT 
                        COUNT(DISTINCT game_id) as unique_games,
                        MIN(time_start_game) as earliest_game,
                        MAX(time_start_game) as latest_game
                    FROM {self.schema_name}.games
                """
                )
                games_summary = cursor.fetchone()

                cursor.execute(
                    f"""
                    SELECT 
                        COUNT(DISTINCT stadium_name) as unique_stadiums,
                        COUNT(DISTINCT home_team) as unique_teams
                    FROM {self.schema_name}.stadium_coordinates
                """
                )
                stadiums_summary = cursor.fetchone()

                cursor.execute(
                    f"""
                    SELECT 
                        COUNT(DISTINCT game_id) as games_with_weather,
                        AVG(temperature) as avg_temperature,
                        AVG(wind_speed) as avg_wind_speed
                    FROM {self.schema_name}.games_weather
                """
                )
                weather_summary = cursor.fetchone()

                validation_results = {
                    "games_count": games_count,
                    "stadiums_count": stadiums_count,
                    "weather_count": weather_count,
                    "unique_games": games_summary[0],
                    "earliest_game": games_summary[1],
                    "latest_game": games_summary[2],
                    "unique_stadiums": stadiums_summary[0],
                    "unique_teams": stadiums_summary[1],
                    "games_with_weather": weather_summary[0],
                    "avg_temperature": weather_summary[1],
                    "avg_wind_speed": weather_summary[2],
                }

                logger.info("Data validation completed")
                return validation_results

        except Exception as e:
            logger.error(f"Failed to validate data: {e}")
            raise

    def import_all_data(self, data_dir: str) -> Dict[str, int]:
        """Import all historical data from the specified directory."""
        try:
            logger.info(f"Starting import of all historical data from {data_dir}")

            # Create tables
            self.create_tables()

            # Import data files
            results = {}

            # Import games data
            games_file = os.path.join(data_dir, "games.csv")
            if os.path.exists(games_file):
                results["games"] = self.import_games_data(games_file)
            else:
                logger.warning(f"Games file not found: {games_file}")
                results["games"] = 0

            # Import stadium coordinates
            stadiums_file = os.path.join(data_dir, "stadium_coordinates.csv")
            if os.path.exists(stadiums_file):
                results["stadiums"] = self.import_stadium_coordinates(stadiums_file)
            else:
                logger.warning(f"Stadium coordinates file not found: {stadiums_file}")
                results["stadiums"] = 0

            # Import weather data
            weather_file = os.path.join(data_dir, "games_weather.csv")
            if os.path.exists(weather_file):
                results["weather"] = self.import_games_weather(weather_file)
            else:
                logger.warning(f"Weather file not found: {weather_file}")
                results["weather"] = 0

            # Validate imported data
            validation = self.validate_data()
            results.update(validation)

            logger.info("Historical data import completed successfully")
            return results

        except Exception as e:
            logger.error(f"Failed to import historical data: {e}")
            raise


def main():
    """Main function for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Import historical data to MySQL database"
    )
    parser.add_argument(
        "--data-dir",
        default="data/external/weather",
        help="Directory containing CSV files",
    )
    parser.add_argument(
        "--schema", default="historical_data", help="Database schema name"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing data, don't import",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for weather data import",
    )

    args = parser.parse_args()

    try:
        # Initialize importer
        importer = HistoricalDataImporter()
        importer.schema_name = args.schema

        # Connect to database
        importer.connect_database()

        if args.validate_only:
            # Only validate existing data
            validation = importer.validate_data()
            print("\n=== Data Validation Results ===")
            print(f"Games: {validation['games_count']:,}")
            print(f"Stadiums: {validation['stadiums_count']:,}")
            print(f"Weather records: {validation['weather_count']:,}")
            print(f"Unique games: {validation['unique_games']:,}")
            print(f"Unique stadiums: {validation['unique_stadiums']:,}")
            print(f"Games with weather: {validation['games_with_weather']:,}")
            print(
                f"Date range: {validation['earliest_game']} to {validation['latest_game']}"
            )
            print(f"Average temperature: {validation['avg_temperature']:.1f}°F")
            print(f"Average wind speed: {validation['avg_wind_speed']:.1f} mph")
        else:
            # Import all data
            results = importer.import_all_data(args.data_dir)

            print("\n=== Import Results ===")
            print(f"Games imported: {results['games']:,}")
            print(f"Stadiums imported: {results['stadiums']:,}")
            print(f"Weather records imported: {results['weather']:,}")
            print(f"Total unique games: {results['unique_games']:,}")
            print(f"Total unique stadiums: {results['unique_stadiums']:,}")
            print(f"Games with weather data: {results['games_with_weather']:,}")
            print(f"Date range: {results['earliest_game']} to {results['latest_game']}")
            print(f"Average temperature: {results['avg_temperature']:.1f}°F")
            print(f"Average wind speed: {results['avg_wind_speed']:.1f} mph")

        print(f"\n✅ Historical data import completed successfully!")
        print(f"Schema: {args.schema}")

    except Exception as e:
        logger.error(f"Import failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
