"""Lineup optimization for fantasy football using linear programming."""

import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pulp import *
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

from .database.data_service import DataService
from .sleeper_client import SleeperClient, SleeperConfig

logger = logging.getLogger(__name__)


@dataclass
class PlayerProjection:
    """Player projection data."""

    player_id: str
    name: str
    position: str
    team: str
    projected_points: float
    projected_floor: float
    projected_ceiling: float
    ownership_pct: float
    salary: Optional[int] = None
    injury_risk: float = 0.0


@dataclass
class LineupConstraints:
    """Constraints for lineup optimization."""

    total_players: int = 9
    qb_count: int = 1
    rb_count: int = 2
    wr_count: int = 2
    te_count: int = 1
    flex_count: int = 2  # RB/WR/TE flex positions
    k_count: int = 1
    dst_count: int = 1
    max_players_per_team: int = 4
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None


class LineupOptimizer:
    """Optimize fantasy football lineups using linear programming."""

    def __init__(self, sleeper_client: SleeperClient, use_database: bool = True):
        self.sleeper_client = sleeper_client
        self.use_database = use_database
        self.data_service = DataService() if use_database else None
        self.players_df = None
        self.projections = {}
        self.scaler = StandardScaler()
        self.projection_model = RandomForestRegressor(n_estimators=100, random_state=42)

    def load_player_data(self) -> pd.DataFrame:
        """Load and prepare player data."""
        self.players_df = self.sleeper_client.create_player_dataframe()

        # Filter for relevant fantasy positions
        fantasy_positions = ["QB", "RB", "WR", "TE", "K", "DEF"]
        self.players_df = self.players_df[
            self.players_df["position"].isin(fantasy_positions)
        ].copy()

        # Add team mapping for defenses
        self.players_df.loc[self.players_df["position"] == "DEF", "name"] = (
            self.players_df.loc[self.players_df["position"] == "DEF", "team"]
            + " Defense"
        )

        return self.players_df

    def generate_projections(self, week: int = None) -> Dict[str, PlayerProjection]:
        """Generate player projections for the given week."""
        if self.players_df is None:
            self.load_player_data()

        projections = {}

        # Try to get projections from database first
        if self.use_database and self.data_service and week:
            db_projections = self.data_service.get_projections(week)
            if db_projections:
                logger.info(f"Using {len(db_projections)} projections from database")
                for proj in db_projections:
                    player = self.data_service.get_player(proj.player_id)
                    if player:
                        projections[proj.player_id] = PlayerProjection(
                            player_id=proj.player_id,
                            name=player.full_name
                            or f"{player.first_name} {player.last_name}".strip(),
                            position=player.position,
                            team=player.team,
                            projected_points=float(
                                proj.proj_fantasy_points_ppr
                                or proj.proj_fantasy_points
                                or 0
                            ),
                            projected_floor=float(proj.proj_floor or 0),
                            projected_ceiling=float(proj.proj_ceiling or 0),
                            ownership_pct=self._estimate_ownership_from_db(player),
                            injury_risk=self._calculate_injury_risk_from_db(player),
                        )

                if projections:
                    self.projections = projections
                    return projections

        # Generate projections if not in database
        logger.info("Generating projections from player data")
        for _, player in self.players_df.iterrows():
            # Get historical stats for projection
            if self.use_database and self.data_service:
                # Get stats from database
                player_stats = self.data_service.get_player_stats(
                    player["player_id"], self.sleeper_client.config.season
                )
                stats_dict = self._convert_stats_to_dict(player_stats)
            else:
                # Get stats from API
                stats_dict = self.sleeper_client.get_player_stats(player["player_id"])

            # Simple projection logic (can be enhanced with ML models)
            projected_points = self._calculate_projected_points(
                player, stats_dict, week
            )
            floor_multiplier = 0.7  # Conservative floor
            ceiling_multiplier = 1.4  # Optimistic ceiling

            projections[player["player_id"]] = PlayerProjection(
                player_id=player["player_id"],
                name=player["name"],
                position=player["position"],
                team=player["team"],
                projected_points=projected_points,
                projected_floor=projected_points * floor_multiplier,
                projected_ceiling=projected_points * ceiling_multiplier,
                ownership_pct=self._estimate_ownership(player),
                injury_risk=self._calculate_injury_risk(player),
            )

        # Save projections to database
        if self.use_database and self.data_service and week:
            self._save_projections_to_db(projections, week)

        self.projections = projections
        return projections

    def _convert_stats_to_dict(self, player_stats) -> Dict:
        """Convert database stats to dictionary format."""
        if not player_stats:
            return {}

        # Aggregate stats (simplified)
        total_stats = {
            "pass_yds": 0,
            "pass_td": 0,
            "pass_int": 0,
            "rush_yds": 0,
            "rush_td": 0,
            "rec": 0,
            "rec_yds": 0,
            "rec_td": 0,
            "fgm": 0,
            "xpm": 0,
            "def_st_td": 0,
            "def_st_int": 0,
            "def_st_sack": 0,
        }

        for stat in player_stats:
            for key in total_stats.keys():
                if hasattr(stat, key):
                    total_stats[key] += getattr(stat, key) or 0

        return total_stats

    def _estimate_ownership_from_db(self, player) -> float:
        """Estimate ownership from database data."""
        # Simplified ownership estimation
        position_ownership = {
            "QB": 15.0,
            "RB": 25.0,
            "WR": 20.0,
            "TE": 12.0,
            "K": 8.0,
            "DEF": 10.0,
        }
        return position_ownership.get(player.position, 10.0)

    def _calculate_injury_risk_from_db(self, player) -> float:
        """Calculate injury risk from database player data."""
        risk_factors = {
            "Active": 0.1,
            "Questionable": 0.4,
            "Doubtful": 0.7,
            "Out": 1.0,
            "IR": 1.0,
        }
        return risk_factors.get(player.injury_status or "Active", 0.1)

    def _save_projections_to_db(
        self, projections: Dict[str, PlayerProjection], week: int
    ) -> None:
        """Save projections to database."""
        try:
            projections_data = []
            for player_id, proj in projections.items():
                projection_data = {
                    "player_id": player_id,
                    "season": self.sleeper_client.config.season,
                    "week": week,
                    "proj_fantasy_points_ppr": proj.projected_points,
                    "proj_fantasy_points": proj.projected_points
                    * 0.9,  # Estimate non-PPR
                    "proj_floor": proj.projected_floor,
                    "proj_ceiling": proj.projected_ceiling,
                    "model_version": "lineup_optimizer_v1",
                    "confidence_score": 0.7,  # Default confidence
                }
                projections_data.append(projection_data)

            self.data_service.create_or_update_projections(projections_data)
            logger.info(f"Saved {len(projections_data)} projections to database")

        except Exception as e:
            logger.warning(f"Failed to save projections to database: {e}")

    def _calculate_projected_points(
        self, player: pd.Series, stats: Dict, week: int = None
    ) -> float:
        """Calculate projected fantasy points for a player."""
        position = player["position"]

        # PPR scoring settings from league
        league_settings = self.sleeper_client.get_league_settings()
        scoring = league_settings.get("scoring_settings", {})

        # Base projections by position (simplified)
        base_projections = {
            "QB": 18.0,
            "RB": 12.0,
            "WR": 11.0,
            "TE": 8.0,
            "K": 7.0,
            "DEF": 8.0,
        }

        base_points = base_projections.get(position, 5.0)

        # Adjust based on team quality and matchup (simplified)
        team_adjustments = self._get_team_adjustments()
        team_adj = team_adjustments.get(player["team"], 1.0)

        # Injury adjustment
        injury_adj = 1.0
        if player.get("injury_status") in ["Questionable", "Doubtful"]:
            injury_adj = 0.8
        elif player.get("injury_status") == "Out":
            injury_adj = 0.0

        return base_points * team_adj * injury_adj

    def _get_team_adjustments(self) -> Dict[str, float]:
        """Get team strength adjustments (simplified)."""
        # This would typically come from external rankings/data
        return {
            "BUF": 1.2,
            "KC": 1.15,
            "DAL": 1.1,
            "SF": 1.1,
            "MIA": 1.05,
            "CIN": 1.05,
            "PHI": 1.05,
            # ... other teams would have values between 0.8-1.2
        }

    def _estimate_ownership(self, player: pd.Series) -> float:
        """Estimate player ownership percentage."""
        # Simplified ownership estimation
        position_ownership = {
            "QB": 15.0,
            "RB": 25.0,
            "WR": 20.0,
            "TE": 12.0,
            "K": 8.0,
            "DEF": 10.0,
        }
        return position_ownership.get(player["position"], 10.0)

    def _calculate_injury_risk(self, player: pd.Series) -> float:
        """Calculate injury risk factor."""
        risk_factors = {
            "Active": 0.1,
            "Questionable": 0.4,
            "Doubtful": 0.7,
            "Out": 1.0,
            "IR": 1.0,
        }
        return risk_factors.get(player.get("injury_status", "Active"), 0.1)

    def optimize_lineup(
        self,
        constraints: LineupConstraints = None,
        objective: str = "points",
        num_lineups: int = 1,
    ) -> List[Dict[str, any]]:
        """Optimize lineup using linear programming."""
        if not self.projections:
            raise ValueError("Must generate projections first")

        if constraints is None:
            constraints = LineupConstraints()

        lineups = []
        used_players = set()

        for lineup_num in range(num_lineups):
            lineup = self._optimize_single_lineup(constraints, objective, used_players)
            if lineup:
                lineups.append(lineup)
                # Add players to used set to avoid duplicates in next lineup
                used_players.update([p["player_id"] for p in lineup["players"]])

        return lineups

    def _optimize_single_lineup(
        self,
        constraints: LineupConstraints,
        objective: str,
        exclude_players: set = None,
    ) -> Optional[Dict[str, any]]:
        """Optimize a single lineup."""
        if exclude_players is None:
            exclude_players = set()

        # Create the optimization problem
        prob = LpProblem("Fantasy_Lineup_Optimization", LpMaximize)

        # Decision variables
        player_vars = {}
        for player_id, projection in self.projections.items():
            if player_id not in exclude_players:
                player_vars[player_id] = LpVariable(f"player_{player_id}", cat="Binary")

        # Objective function
        if objective == "points":
            prob += lpSum(
                [
                    projection.projected_points * player_vars[player_id]
                    for player_id, projection in self.projections.items()
                    if player_id in player_vars
                ]
            )
        elif objective == "ceiling":
            prob += lpSum(
                [
                    projection.projected_ceiling * player_vars[player_id]
                    for player_id, projection in self.projections.items()
                    if player_id in player_vars
                ]
            )
        elif objective == "floor":
            prob += lpSum(
                [
                    projection.projected_floor * player_vars[player_id]
                    for player_id, projection in self.projections.items()
                    if player_id in player_vars
                ]
            )

        # Position constraints
        positions = ["QB", "RB", "WR", "TE", "K", "DEF"]
        for position in positions:
            position_players = [
                player_vars[pid]
                for pid, proj in self.projections.items()
                if proj.position == position and pid in player_vars
            ]

            if position == "QB":
                prob += lpSum(position_players) == constraints.qb_count
            elif position == "RB":
                prob += lpSum(position_players) >= constraints.rb_count
            elif position == "WR":
                prob += lpSum(position_players) >= constraints.wr_count
            elif position == "TE":
                prob += lpSum(position_players) >= constraints.te_count
            elif position == "K":
                prob += lpSum(position_players) == constraints.k_count
            elif position == "DEF":
                prob += lpSum(position_players) == constraints.dst_count

        # Flex constraint (RB/WR/TE can fill flex spots)
        flex_eligible = [
            player_vars[pid]
            for pid, proj in self.projections.items()
            if proj.position in ["RB", "WR", "TE"] and pid in player_vars
        ]
        total_rb_wr_te = (
            constraints.rb_count
            + constraints.wr_count
            + constraints.te_count
            + constraints.flex_count
        )
        prob += lpSum(flex_eligible) == total_rb_wr_te

        # Total players constraint
        prob += lpSum(player_vars.values()) == constraints.total_players

        # Team constraints
        if constraints.max_players_per_team:
            teams = set(proj.team for proj in self.projections.values())
            for team in teams:
                team_players = [
                    player_vars[pid]
                    for pid, proj in self.projections.items()
                    if proj.team == team and pid in player_vars
                ]
                if team_players:
                    prob += lpSum(team_players) <= constraints.max_players_per_team

        # Solve the problem
        prob.solve(PULP_CBC_CMD(msg=0))

        if prob.status != 1:  # Not optimal
            return None

        # Extract solution
        selected_players = []
        total_points = 0
        total_floor = 0
        total_ceiling = 0

        for player_id, var in player_vars.items():
            if var.varValue == 1:
                projection = self.projections[player_id]
                selected_players.append(
                    {
                        "player_id": player_id,
                        "name": projection.name,
                        "position": projection.position,
                        "team": projection.team,
                        "projected_points": projection.projected_points,
                        "projected_floor": projection.projected_floor,
                        "projected_ceiling": projection.projected_ceiling,
                        "ownership_pct": projection.ownership_pct,
                        "injury_risk": projection.injury_risk,
                    }
                )
                total_points += projection.projected_points
                total_floor += projection.projected_floor
                total_ceiling += projection.projected_ceiling

        return {
            "players": selected_players,
            "total_projected_points": total_points,
            "total_floor": total_floor,
            "total_ceiling": total_ceiling,
            "lineup_number": len(exclude_players) + 1,
        }

    def analyze_current_lineup(self, roster_data: Dict = None) -> Dict[str, any]:
        """Analyze current roster and suggest improvements."""
        if not self.projections:
            self.generate_projections()

        # Get roster data from database if not provided
        if roster_data is None:
            if self.use_database and self.sleeper_client.config.user_id:
                roster_data = self.sleeper_client.get_my_roster_from_db()
            else:
                roster_data = self.sleeper_client.get_my_roster()

        if not roster_data:
            return {"error": "No roster data available"}

        current_players = roster_data.get("players", [])
        current_projections = []

        for player_id in current_players:
            if player_id in self.projections:
                proj = self.projections[player_id]
                current_projections.append(
                    {
                        "player_id": player_id,
                        "name": proj.name,
                        "position": proj.position,
                        "projected_points": proj.projected_points,
                        "injury_risk": proj.injury_risk,
                    }
                )

        # Generate optimal lineup for comparison
        optimal_lineups = self.optimize_lineup(num_lineups=1)
        optimal_lineup = optimal_lineups[0] if optimal_lineups else None

        analysis = {
            "current_roster": current_projections,
            "current_total_points": sum(
                p["projected_points"] for p in current_projections
            ),
            "optimal_lineup": optimal_lineup,
            "improvement_potential": 0,
            "recommendations": [],
        }

        if optimal_lineup:
            analysis["improvement_potential"] = (
                optimal_lineup["total_projected_points"]
                - analysis["current_total_points"]
            )

            # Find players to consider dropping/adding
            current_player_ids = set(current_players)
            optimal_player_ids = set(p["player_id"] for p in optimal_lineup["players"])

            to_drop = current_player_ids - optimal_player_ids
            to_add = optimal_player_ids - current_player_ids

            for player_id in to_drop:
                if player_id in self.projections:
                    proj = self.projections[player_id]
                    analysis["recommendations"].append(
                        {
                            "action": "consider_dropping",
                            "player": {
                                "id": player_id,
                                "name": proj.name,
                                "position": proj.position,
                            },
                            "reason": "Underperforming projection",
                        }
                    )

            for player_id in to_add:
                if player_id in self.projections:
                    proj = self.projections[player_id]
                    analysis["recommendations"].append(
                        {
                            "action": "consider_adding",
                            "player": {
                                "id": player_id,
                                "name": proj.name,
                                "position": proj.position,
                            },
                            "reason": "Higher projection potential",
                        }
                    )

        return analysis

    def export_lineups(
        self,
        lineups: List[Dict],
        output_file: str = "data/processed/optimized_lineups.json",
    ):
        """Export optimized lineups to file."""
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(lineups, f, indent=2)

        print(f"Exported {len(lineups)} lineups to {output_file}")


def main():
    """Main function for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Fantasy Football Lineup Optimizer")
    parser.add_argument("--league-id", required=True, help="Sleeper league ID")
    parser.add_argument("--user-id", help="Your Sleeper user ID")
    parser.add_argument("--week", type=int, help="Week to optimize for")
    parser.add_argument(
        "--num-lineups", type=int, default=3, help="Number of lineups to generate"
    )
    parser.add_argument(
        "--objective", choices=["points", "ceiling", "floor"], default="points"
    )
    parser.add_argument("--output", default="data/processed/optimized_lineups.json")

    args = parser.parse_args()

    # Setup Sleeper client
    config = SleeperConfig(league_id=args.league_id, user_id=args.user_id)
    sleeper_client = SleeperClient(config)

    # Create optimizer
    optimizer = LineupOptimizer(sleeper_client)

    print("Loading player data...")
    optimizer.load_player_data()

    print(f"Generating projections for week {args.week or 'current'}...")
    optimizer.generate_projections(args.week)

    print(f"Optimizing {args.num_lineups} lineups...")
    lineups = optimizer.optimize_lineup(
        num_lineups=args.num_lineups, objective=args.objective
    )

    if lineups:
        print(f"\nGenerated {len(lineups)} optimal lineups:")
        for i, lineup in enumerate(lineups, 1):
            print(
                f"\nLineup {i} (Projected: {lineup['total_projected_points']:.1f} pts):"
            )
            for player in lineup["players"]:
                print(
                    f"  {player['position']}: {player['name']} ({player['projected_points']:.1f} pts)"
                )

        optimizer.export_lineups(lineups, args.output)
    else:
        print("No optimal lineups found. Check your constraints and projections.")


if __name__ == "__main__":
    main()
