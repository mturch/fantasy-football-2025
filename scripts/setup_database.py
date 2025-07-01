#!/usr/bin/env python3
"""Database setup and migration script."""

import logging
import os
import sys
from pathlib import Path

from fantasy_football_2025.database.setup import (
    get_database_info,
    reset_database,
    setup_database,
    verify_database_setup,
)


def main():
    """Main database setup script."""
    import argparse

    parser = argparse.ArgumentParser(description="Fantasy Football Database Setup")
    parser.add_argument("--setup", action="store_true", help="Set up the database")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the database (WARNING: Deletes all data)",
    )
    parser.add_argument("--verify", action="store_true", help="Verify database setup")
    parser.add_argument("--info", action="store_true", help="Show database information")
    parser.add_argument(
        "--create-sample-data",
        action="store_true",
        help="Create sample data for testing",
    )
    parser.add_argument("--database-url", help="Database URL override")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    if not any(
        [args.setup, args.reset, args.verify, args.info, args.create_sample_data]
    ):
        parser.print_help()
        return

    print("🏈 Fantasy Football Database Management")
    print("=" * 50)

    if args.info:
        print("📊 Database Information:")
        info = get_database_info()
        for key, value in info.items():
            print(f"  {key}: {value}")
        print()

    if args.setup:
        print("🔧 Setting up database...")
        success = setup_database(args.database_url)
        if success:
            print("✅ Database setup completed successfully")
        else:
            print("❌ Database setup failed")
            sys.exit(1)

    if args.reset:
        print("⚠️  WARNING: This will delete ALL data in the database!")
        confirm = input("Type 'DELETE ALL DATA' to confirm: ")
        if confirm == "DELETE ALL DATA":
            print("🗑️  Resetting database...")
            success = reset_database(args.database_url)
            if success:
                print("✅ Database reset completed successfully")
            else:
                print("❌ Database reset failed")
                sys.exit(1)
        else:
            print("Database reset cancelled")

    if args.verify:
        print("🔍 Verifying database setup...")
        success = verify_database_setup()
        if success:
            print("✅ Database verification successful")
        else:
            print("❌ Database verification failed")
            sys.exit(1)

    if args.create_sample_data:
        print("📝 Creating sample data...")
        create_sample_data()
        print("✅ Sample data created successfully")


def create_sample_data():
    """Create sample data for testing."""
    from datetime import date, datetime

    from fantasy_football_2025.database.data_service import DataService

    data_service = DataService()

    # Sample league
    league_data = {
        "league_id": "sample_league_123",
        "name": "Sample Fantasy League",
        "season": "2024",
        "total_rosters": 12,
        "scoring_settings": {
            "pass_yd": 0.04,
            "pass_td": 4,
            "pass_int": -2,
            "rush_yd": 0.1,
            "rush_td": 6,
            "rec": 1,  # PPR
            "rec_yd": 0.1,
            "rec_td": 6,
        },
        "roster_positions": [
            "QB",
            "RB",
            "RB",
            "WR",
            "WR",
            "TE",
            "FLEX",
            "FLEX",
            "K",
            "DEF",
            "BN",
            "BN",
            "BN",
            "BN",
            "BN",
        ],
        "league_type": "redraft",
        "playoff_week_start": 15,
        "status": "in_season",
    }

    league = data_service.create_or_update_league(league_data)
    print(f"Created league: {league.name}")

    # Sample users
    users_data = [
        {
            "user_id": "user_001",
            "username": "team_owner_1",
            "display_name": "Fantasy Champion",
            "team_name": "The Destroyers",
            "is_owner": False,
        },
        {
            "user_id": "user_002",
            "username": "team_owner_2",
            "display_name": "Points Machine",
            "team_name": "Touchdown Kings",
            "is_owner": False,
        },
    ]

    users = data_service.create_or_update_users(users_data, league.league_id)
    print(f"Created {len(users)} users")

    # Sample players
    players_data = {
        "player_001": {
            "first_name": "Josh",
            "last_name": "Allen",
            "position": "QB",
            "team": "BUF",
            "age": 28,
            "status": "Active",
            "fantasy_positions": ["QB"],
        },
        "player_002": {
            "first_name": "Christian",
            "last_name": "McCaffrey",
            "position": "RB",
            "team": "SF",
            "age": 28,
            "status": "Active",
            "fantasy_positions": ["RB"],
        },
        "player_003": {
            "first_name": "Davante",
            "last_name": "Adams",
            "position": "WR",
            "team": "LV",
            "age": 31,
            "status": "Active",
            "fantasy_positions": ["WR"],
        },
        "player_004": {
            "first_name": "Travis",
            "last_name": "Kelce",
            "position": "TE",
            "team": "KC",
            "age": 34,
            "status": "Active",
            "fantasy_positions": ["TE"],
        },
    }

    player_count = data_service.create_or_update_players(players_data)
    print(f"Created {player_count} players")

    # Sample rosters
    rosters_data = [
        {
            "roster_id": 1,
            "owner_id": "user_001",
            "players": ["player_001", "player_002"],
            "settings": {
                "wins": 8,
                "losses": 5,
                "ties": 0,
                "fpts": 1650.5,
                "fpts_against": 1520.3,
                "waiver_position": 5,
            },
        },
        {
            "roster_id": 2,
            "owner_id": "user_002",
            "players": ["player_003", "player_004"],
            "settings": {
                "wins": 7,
                "losses": 6,
                "ties": 0,
                "fpts": 1580.2,
                "fpts_against": 1590.8,
                "waiver_position": 8,
            },
        },
    ]

    rosters = data_service.create_or_update_rosters(rosters_data, league.league_id)
    print(f"Created {len(rosters)} rosters")

    # Sample player stats
    stats_data = [
        {
            "player_id": "player_001",
            "season": "2024",
            "week": 1,
            "pass_att": 35,
            "pass_comp": 25,
            "pass_yds": 320,
            "pass_td": 3,
            "pass_int": 1,
            "rush_att": 8,
            "rush_yds": 45,
            "rush_td": 1,
            "fantasy_points_ppr": 28.8,
        },
        {
            "player_id": "player_002",
            "season": "2024",
            "week": 1,
            "rush_att": 20,
            "rush_yds": 120,
            "rush_td": 2,
            "rec": 5,
            "rec_yds": 40,
            "rec_td": 0,
            "fantasy_points_ppr": 22.0,
        },
    ]

    stats_count = data_service.create_or_update_player_stats(stats_data)
    print(f"Created {stats_count} player stats")

    # Sample projections
    projections_data = [
        {
            "player_id": "player_001",
            "season": "2024",
            "week": 14,
            "proj_pass_yds": 280.0,
            "proj_pass_td": 2.5,
            "proj_pass_int": 0.8,
            "proj_rush_yds": 35.0,
            "proj_rush_td": 0.3,
            "proj_fantasy_points_ppr": 24.2,
            "proj_floor": 18.0,
            "proj_ceiling": 32.0,
            "model_version": "sample_v1",
            "confidence_score": 0.75,
        },
        {
            "player_id": "player_002",
            "season": "2024",
            "week": 14,
            "proj_rush_yds": 95.0,
            "proj_rush_td": 1.2,
            "proj_rec": 4.5,
            "proj_rec_yds": 35.0,
            "proj_rec_td": 0.2,
            "proj_fantasy_points_ppr": 19.5,
            "proj_floor": 14.0,
            "proj_ceiling": 28.0,
            "model_version": "sample_v1",
            "confidence_score": 0.80,
        },
    ]

    proj_count = data_service.create_or_update_projections(projections_data)
    print(f"Created {proj_count} projections")


if __name__ == "__main__":
    main()
