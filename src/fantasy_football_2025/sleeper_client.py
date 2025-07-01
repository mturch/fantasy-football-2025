"""Sleeper API client for fantasy football data."""

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from python_dotenv import load_dotenv
from sleeper_api_wrapper import Drafts, League, Players, Stats, User

from .database.data_service import DataService

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class SleeperConfig:
    """Configuration for Sleeper API client."""

    league_id: str
    user_id: Optional[str] = None
    season: str = "2024"
    cache_duration: int = 3600  # 1 hour in seconds


class SleeperClient:
    """Client for interacting with Sleeper API."""

    def __init__(self, config: SleeperConfig, use_database: bool = True):
        self.config = config
        self.league = League(config.league_id)
        self.players = Players()
        self.stats = Stats()
        self.drafts = Drafts()
        self._cache = {}
        self._cache_timestamps = {}
        self.use_database = use_database
        self.data_service = DataService() if use_database else None

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid."""
        if key not in self._cache_timestamps:
            return False

        timestamp = self._cache_timestamps[key]
        return (datetime.now() - timestamp).seconds < self.config.cache_duration

    def _get_cached_or_fetch(self, key: str, fetch_func) -> Any:
        """Get data from cache or fetch from API."""
        if self._is_cache_valid(key):
            return self._cache[key]

        data = fetch_func()
        self._cache[key] = data
        self._cache_timestamps[key] = datetime.now()
        return data

    def get_league_info(self) -> Dict[str, Any]:
        """Get league information."""
        return self._get_cached_or_fetch(
            "league_info", lambda: self.league.get_league()
        )

    def get_rosters(self) -> List[Dict[str, Any]]:
        """Get all rosters in the league."""
        return self._get_cached_or_fetch("rosters", lambda: self.league.get_rosters())

    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users in the league."""
        return self._get_cached_or_fetch("users", lambda: self.league.get_users())

    def get_matchups(self, week: int) -> List[Dict[str, Any]]:
        """Get matchups for a specific week."""
        cache_key = f"matchups_week_{week}"
        return self._get_cached_or_fetch(
            cache_key, lambda: self.league.get_matchups(week)
        )

    def get_players_data(self) -> Dict[str, Any]:
        """Get all NFL players data."""
        return self._get_cached_or_fetch(
            "players_data", lambda: self.players.get_all_players()
        )

    def get_trending_players(
        self, sport: str = "nfl", add_type: str = "add"
    ) -> List[Dict[str, Any]]:
        """Get trending players (adds/drops)."""
        cache_key = f"trending_{add_type}"
        return self._get_cached_or_fetch(
            cache_key,
            lambda: self.players.get_trending_players(
                sport, add_type, hours=24, limit=50
            ),
        )

    def get_player_stats(self, player_id: str, season: str = None) -> Dict[str, Any]:
        """Get stats for a specific player."""
        season = season or self.config.season
        cache_key = f"player_stats_{player_id}_{season}"
        return self._get_cached_or_fetch(
            cache_key,
            lambda: self.stats.get_player_stats_by_player_id(player_id, season),
        )

    def get_transactions(self, week: int = None) -> List[Dict[str, Any]]:
        """Get league transactions."""
        cache_key = f"transactions_week_{week}" if week else "transactions_all"
        return self._get_cached_or_fetch(
            cache_key,
            lambda: (
                self.league.get_transactions(week)
                if week
                else self.league.get_transactions()
            ),
        )

    def get_waiver_wire(self) -> List[Dict[str, Any]]:
        """Get current waiver wire claims."""
        return self._get_cached_or_fetch(
            "waiver_wire",
            lambda: self.league.get_transactions(transaction_type="waiver"),
        )

    def get_draft_info(self) -> List[Dict[str, Any]]:
        """Get draft information."""
        return self._get_cached_or_fetch("draft_info", lambda: self.league.get_drafts())

    def get_draft_picks(self, draft_id: str) -> List[Dict[str, Any]]:
        """Get picks for a specific draft."""
        cache_key = f"draft_picks_{draft_id}"
        return self._get_cached_or_fetch(
            cache_key, lambda: self.drafts.get_all_picks(draft_id)
        )

    def get_roster_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get roster for a specific user."""
        rosters = self.get_rosters()
        for roster in rosters:
            if roster.get("owner_id") == user_id:
                return roster
        return None

    def get_my_roster(self) -> Optional[Dict[str, Any]]:
        """Get current user's roster."""
        if not self.config.user_id:
            raise ValueError("User ID not configured")
        return self.get_roster_by_user_id(self.config.user_id)

    def get_league_settings(self) -> Dict[str, Any]:
        """Get league scoring and roster settings."""
        league_info = self.get_league_info()
        return {
            "scoring_settings": league_info.get("scoring_settings", {}),
            "roster_positions": league_info.get("roster_positions", []),
            "total_rosters": league_info.get("total_rosters", 0),
            "playoff_week_start": league_info.get("playoff_week_start", 14),
            "league_type": league_info.get("type", "redraft"),
        }

    def is_ppr_league(self) -> bool:
        """Check if league uses PPR scoring."""
        settings = self.get_league_settings()
        scoring = settings.get("scoring_settings", {})
        return scoring.get("rec", 0) > 0

    def get_flex_positions(self) -> List[str]:
        """Get flex position requirements."""
        settings = self.get_league_settings()
        positions = settings.get("roster_positions", [])
        return [pos for pos in positions if "FLEX" in pos]

    def export_league_data(self, output_dir: str = "data/raw") -> None:
        """Export all league data to JSON files and database."""
        # Save to database if enabled
        if self.use_database and self.data_service:
            self.save_to_database()

        # Also save to JSON files for backup
        os.makedirs(output_dir, exist_ok=True)

        # Export main league data
        data_exports = {
            "league_info": self.get_league_info(),
            "rosters": self.get_rosters(),
            "users": self.get_users(),
            "players": self.get_players_data(),
            "trending_adds": self.get_trending_players(add_type="add"),
            "trending_drops": self.get_trending_players(add_type="drop"),
            "transactions": self.get_transactions(),
            "draft_info": self.get_draft_info(),
        }

        for filename, data in data_exports.items():
            filepath = os.path.join(output_dir, f"{filename}.json")
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            print(f"Exported {filename} to {filepath}")

        # Export weekly matchups
        current_week = self._get_current_week()
        for week in range(1, current_week + 1):
            matchups = self.get_matchups(week)
            filepath = os.path.join(output_dir, f"matchups_week_{week}.json")
            with open(filepath, "w") as f:
                json.dump(matchups, f, indent=2)
            print(f"Exported week {week} matchups to {filepath}")

    def save_to_database(self) -> None:
        """Save all league data to the database."""
        if not self.data_service:
            logger.warning("Database service not available")
            return

        logger.info("Saving league data to database...")

        try:
            # Save league info
            league_info = self.get_league_info()
            league_data = {
                "league_id": self.config.league_id,
                "name": league_info.get("name", ""),
                "season": self.config.season,
                "total_rosters": league_info.get("total_rosters", 0),
                "scoring_settings": league_info.get("scoring_settings"),
                "roster_positions": league_info.get("roster_positions"),
                "league_type": league_info.get("type"),
                "playoff_week_start": league_info.get("playoff_week_start"),
                "status": league_info.get("status"),
            }
            self.data_service.create_or_update_league(league_data)
            logger.info("✅ Saved league info")

            # Save users
            users_data = self.get_users()
            user_list = []
            for user in users_data:
                user_data = {
                    "user_id": user.get("user_id"),
                    "username": user.get("username"),
                    "display_name": user.get("display_name"),
                    "team_name": user.get("metadata", {}).get("team_name"),
                    "avatar": user.get("avatar"),
                    "is_owner": user.get("is_owner", False),
                }
                user_list.append(user_data)

            self.data_service.create_or_update_users(user_list, self.config.league_id)
            logger.info(f"✅ Saved {len(user_list)} users")

            # Save players
            players_data = self.get_players_data()
            self.data_service.create_or_update_players(players_data)
            logger.info("✅ Saved players data")

            # Save rosters
            rosters_data = self.get_rosters()
            self.data_service.create_or_update_rosters(
                rosters_data, self.config.league_id
            )
            logger.info(f"✅ Saved {len(rosters_data)} rosters")

            # Save transactions
            transactions_data = self.get_transactions()
            self.data_service.create_transactions(
                transactions_data, self.config.league_id
            )
            logger.info(f"✅ Saved {len(transactions_data)} transactions")

            # Save trending players
            trending_adds = self.get_trending_players(add_type="add")
            self.data_service.update_trending_players(trending_adds, "add")

            trending_drops = self.get_trending_players(add_type="drop")
            self.data_service.update_trending_players(trending_drops, "drop")
            logger.info("✅ Saved trending players")

            # Save matchups for current season
            current_week = self._get_current_week()
            for week in range(1, current_week + 1):
                try:
                    matchups = self.get_matchups(week)
                    if matchups:
                        self.data_service.create_matchups(
                            matchups, self.config.league_id, week, self.config.season
                        )
                except Exception as e:
                    logger.warning(f"Failed to save matchups for week {week}: {e}")

            logger.info(f"✅ Saved matchups for weeks 1-{current_week}")

        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            raise

    def _get_current_week(self) -> int:
        """Get current NFL week."""
        # Simple logic - can be enhanced with actual NFL schedule
        now = datetime.now()
        season_start = datetime(2024, 9, 5)  # Approximate 2024 season start
        if now < season_start:
            return 1
        days_since_start = (now - season_start).days
        return min(18, max(1, (days_since_start // 7) + 1))

    def create_player_dataframe(self) -> pd.DataFrame:
        """Create a pandas DataFrame of all players with relevant fantasy data."""
        if self.use_database and self.data_service:
            # Get data from database
            players = self.data_service.get_players()
            players_list = []
            for player in players:
                players_list.append(
                    {
                        "player_id": player.player_id,
                        "name": player.full_name
                        or f"{player.first_name} {player.last_name}".strip(),
                        "position": player.position,
                        "team": player.team,
                        "age": player.age,
                        "height": player.height,
                        "weight": player.weight,
                        "years_exp": player.years_exp,
                        "status": player.status,
                        "injury_status": player.injury_status,
                        "fantasy_positions": player.fantasy_positions or [],
                    }
                )
            return pd.DataFrame(players_list)
        else:
            # Get data from API
            players_data = self.get_players_data()

            players_list = []
            for player_id, player_info in players_data.items():
                if player_info is None:
                    continue

                players_list.append(
                    {
                        "player_id": player_id,
                        "name": f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip(),
                        "position": player_info.get("position", ""),
                        "team": player_info.get("team", ""),
                        "age": player_info.get("age", 0),
                        "height": player_info.get("height", ""),
                        "weight": player_info.get("weight", 0),
                        "years_exp": player_info.get("years_exp", 0),
                        "status": player_info.get("status", ""),
                        "injury_status": player_info.get("injury_status", ""),
                        "fantasy_positions": player_info.get("fantasy_positions", []),
                    }
                )

            return pd.DataFrame(players_list)

    def get_my_roster_from_db(self) -> Optional[Dict[str, Any]]:
        """Get current user's roster from database."""
        if not self.use_database or not self.data_service or not self.config.user_id:
            return None

        roster = self.data_service.get_user_roster(
            self.config.user_id, self.config.league_id
        )
        if not roster:
            return None

        player_ids = self.data_service.get_roster_players(roster.roster_id)

        return {
            "roster_id": roster.roster_id,
            "user_id": roster.user_id,
            "players": player_ids,
            "settings": {
                "wins": roster.wins,
                "losses": roster.losses,
                "ties": roster.ties,
                "fpts": float(roster.points_for),
                "fpts_against": float(roster.points_against),
                "waiver_position": roster.waiver_position,
                "waiver_budget_used": roster.waiver_budget_used,
            },
        }


def main():
    """Main function for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Sleeper API Client")
    parser.add_argument("--league-id", required=True, help="Sleeper league ID")
    parser.add_argument("--user-id", help="Your Sleeper user ID")
    parser.add_argument(
        "--output-dir", default="data/raw", help="Output directory for data"
    )
    parser.add_argument("--pull-all", action="store_true", help="Pull all league data")

    args = parser.parse_args()

    config = SleeperConfig(league_id=args.league_id, user_id=args.user_id)

    client = SleeperClient(config)

    if args.pull_all:
        print("Pulling all league data...")
        client.export_league_data(args.output_dir)
        print("Data export complete!")
    else:
        # Show basic league info
        league_info = client.get_league_info()
        print(f"League: {league_info.get('name', 'Unknown')}")
        print(f"Total Rosters: {league_info.get('total_rosters', 0)}")
        print(f"PPR League: {client.is_ppr_league()}")
        print(f"Flex Positions: {client.get_flex_positions()}")


if __name__ == "__main__":
    main()
