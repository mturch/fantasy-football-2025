#!/usr/bin/env python3
"""Data migration script for moving data between systems."""

import sys
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any

from fantasy_football_2025.database.data_service import DataService
from fantasy_football_2025.sleeper_client import SleeperClient, SleeperConfig


def migrate_json_to_database(json_dir: str, league_id: str) -> None:
    """Migrate data from JSON files to database."""
    json_path = Path(json_dir)
    if not json_path.exists():
        print(f"❌ JSON directory does not exist: {json_dir}")
        return
    
    data_service = DataService()
    
    print(f"🔄 Migrating data from {json_dir} to database...")
    
    # Migrate league info
    league_file = json_path / "league_info.json"
    if league_file.exists():
        with open(league_file, 'r') as f:
            league_data = json.load(f)
        
        league_info = {
            'league_id': league_id,
            'name': league_data.get('name', ''),
            'season': '2024',
            'total_rosters': league_data.get('total_rosters', 0),
            'scoring_settings': league_data.get('scoring_settings'),
            'roster_positions': league_data.get('roster_positions'),
            'league_type': league_data.get('type'),
            'playoff_week_start': league_data.get('playoff_week_start'),
            'status': league_data.get('status')
        }
        
        data_service.create_or_update_league(league_info)
        print("✅ Migrated league info")
    
    # Migrate users
    users_file = json_path / "users.json"
    if users_file.exists():
        with open(users_file, 'r') as f:
            users_data = json.load(f)
        
        user_list = []
        for user in users_data:
            user_info = {
                'user_id': user.get('user_id'),
                'username': user.get('username'),
                'display_name': user.get('display_name'),
                'team_name': user.get('metadata', {}).get('team_name'),
                'avatar': user.get('avatar'),
                'is_owner': user.get('is_owner', False)
            }
            user_list.append(user_info)
        
        data_service.create_or_update_users(user_list, league_id)
        print(f"✅ Migrated {len(user_list)} users")
    
    # Migrate players
    players_file = json_path / "players.json"
    if players_file.exists():
        with open(players_file, 'r') as f:
            players_data = json.load(f)
        
        count = data_service.create_or_update_players(players_data)
        print(f"✅ Migrated {count} players")
    
    # Migrate rosters
    rosters_file = json_path / "rosters.json"
    if rosters_file.exists():
        with open(rosters_file, 'r') as f:
            rosters_data = json.load(f)
        
        data_service.create_or_update_rosters(rosters_data, league_id)
        print(f"✅ Migrated {len(rosters_data)} rosters")
    
    # Migrate transactions
    transactions_file = json_path / "transactions.json"
    if transactions_file.exists():
        with open(transactions_file, 'r') as f:
            transactions_data = json.load(f)
        
        count = data_service.create_transactions(transactions_data, league_id)
        print(f"✅ Migrated {count} transactions")
    
    # Migrate trending players
    for trend_type in ['add', 'drop']:
        trending_file = json_path / f"trending_{trend_type}s.json"
        if trending_file.exists():
            with open(trending_file, 'r') as f:
                trending_data = json.load(f)
            
            count = data_service.update_trending_players(trending_data, trend_type)
            print(f"✅ Migrated {count} trending {trend_type} players")
    
    # Migrate weekly matchups
    for week in range(1, 19):  # Weeks 1-18
        matchup_file = json_path / f"matchups_week_{week}.json"
        if matchup_file.exists():
            with open(matchup_file, 'r') as f:
                matchups_data = json.load(f)
            
            if matchups_data:
                count = data_service.create_matchups(matchups_data, league_id, week)
                if count > 0:
                    print(f"✅ Migrated {count} matchups for week {week}")


def export_database_to_json(output_dir: str, league_id: str) -> None:
    """Export database data to JSON files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    data_service = DataService()
    
    print(f"📤 Exporting database data to {output_dir}...")
    
    # Export league summary
    summary = data_service.get_league_summary(league_id)
    if summary:
        with open(output_path / "league_summary.json", 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print("✅ Exported league summary")
    
    # Export available players
    available_players = data_service.get_available_players(league_id)
    player_list = []
    for player in available_players:
        player_dict = {
            'player_id': player.player_id,
            'name': player.full_name,
            'position': player.position,
            'team': player.team,
            'status': player.status,
            'injury_status': player.injury_status
        }
        player_list.append(player_dict)
    
    with open(output_path / "available_players.json", 'w') as f:
        json.dump(player_list, f, indent=2)
    print(f"✅ Exported {len(player_list)} available players")


def backup_database(backup_dir: str, league_id: str) -> None:
    """Create a complete backup of database data."""
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_subdir = backup_path / f"backup_{timestamp}"
    backup_subdir.mkdir(exist_ok=True)
    
    print(f"💾 Creating database backup in {backup_subdir}...")
    
    export_database_to_json(str(backup_subdir), league_id)
    
    # Create backup metadata
    metadata = {
        'backup_date': datetime.now().isoformat(),
        'league_id': league_id,
        'backup_type': 'full',
        'version': '1.0'
    }
    
    with open(backup_subdir / "backup_metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Backup completed: {backup_subdir}")


def pull_fresh_data(league_id: str, user_id: str) -> None:
    """Pull fresh data from Sleeper API and save to database."""
    print(f"🔄 Pulling fresh data from Sleeper API...")
    
    config = SleeperConfig(league_id=league_id, user_id=user_id)
    client = SleeperClient(config, use_database=True)
    
    # This will automatically save to database
    client.export_league_data()
    
    print("✅ Fresh data pulled and saved to database")


def main():
    """Main migration script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fantasy Football Data Migration")
    parser.add_argument("--migrate-json", help="Migrate JSON files to database (provide directory path)")
    parser.add_argument("--export-json", help="Export database to JSON files (provide output directory)")
    parser.add_argument("--backup", help="Create database backup (provide backup directory)")
    parser.add_argument("--pull-fresh", action="store_true", help="Pull fresh data from Sleeper API")
    parser.add_argument("--league-id", required=True, help="Sleeper league ID")
    parser.add_argument("--user-id", help="Your Sleeper user ID (required for --pull-fresh)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🏈 Fantasy Football Data Migration")
    print("=" * 50)
    
    if args.migrate_json:
        migrate_json_to_database(args.migrate_json, args.league_id)
    
    if args.export_json:
        export_database_to_json(args.export_json, args.league_id)
    
    if args.backup:
        backup_database(args.backup, args.league_id)
    
    if args.pull_fresh:
        if not args.user_id:
            print("❌ --user-id is required when using --pull-fresh")
            sys.exit(1)
        pull_fresh_data(args.league_id, args.user_id)
    
    if not any([args.migrate_json, args.export_json, args.backup, args.pull_fresh]):
        parser.print_help()


if __name__ == "__main__":
    main()