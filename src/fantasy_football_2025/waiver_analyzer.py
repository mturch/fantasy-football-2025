"""Waiver wire analysis and recommendation system for fantasy football."""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from scipy.stats import percentileofscore

from .sleeper_client import SleeperClient, SleeperConfig
from .lineup_optimizer import LineupOptimizer, PlayerProjection
from .trade_analyzer import TradeAnalyzer
from .database.data_service import DataService

logger = logging.getLogger(__name__)


@dataclass
class WaiverRecommendation:
    """Waiver wire pickup recommendation."""
    player_id: str
    player_name: str
    position: str
    team: str
    pickup_priority: int
    projected_points: float
    pickup_reason: str
    drop_candidates: List[Dict[str, Any]]
    confidence_score: float
    ownership_trend: str  # 'rising', 'falling', 'stable'
    matchup_rating: float
    injury_replacement: bool = False


@dataclass
class WaiverAnalysis:
    """Complete waiver wire analysis."""
    recommendations: List[WaiverRecommendation]
    drop_candidates: List[Dict[str, Any]]
    emergency_pickups: List[WaiverRecommendation]
    stash_candidates: List[WaiverRecommendation]
    streaming_options: Dict[str, List[WaiverRecommendation]]


class WaiverAnalyzer:
    """Analyze waiver wire and generate pickup recommendations."""

    def __init__(self, sleeper_client: SleeperClient, lineup_optimizer: LineupOptimizer, use_database: bool = True):
        self.sleeper_client = sleeper_client
        self.lineup_optimizer = lineup_optimizer
        self.use_database = use_database
        self.data_service = DataService() if use_database else None
        self.available_players = {}
        self.owned_players = set()
        self.positional_needs = {}
        self.upcoming_matchups = {}

    def analyze_waiver_wire(self, week: int = None) -> WaiverAnalysis:
        """Perform comprehensive waiver wire analysis."""
        print("Analyzing waiver wire...")
        
        # Get current data
        self._load_available_players()
        self._identify_positional_needs()
        self._analyze_upcoming_matchups(week)
        
        # Generate different types of recommendations
        immediate_needs = self._find_immediate_needs()
        emergency_pickups = self._find_emergency_pickups()
        stash_candidates = self._find_stash_candidates()
        streaming_options = self._find_streaming_options()
        drop_candidates = self._identify_drop_candidates()
        
        return WaiverAnalysis(
            recommendations=immediate_needs,
            drop_candidates=drop_candidates,
            emergency_pickups=emergency_pickups,
            stash_candidates=stash_candidates,
            streaming_options=streaming_options
        )

    def _load_available_players(self) -> None:
        """Load all available players (not on any roster)."""
        print("Loading available players...")
        
        if self.use_database and self.data_service:
            # Get available players from database
            available_players_db = self.data_service.get_available_players(
                self.sleeper_client.config.league_id
            )
            
            self.available_players = {}
            for player in available_players_db:
                self.available_players[player.player_id] = {
                    'player_id': player.player_id,
                    'first_name': player.first_name,
                    'last_name': player.last_name,
                    'position': player.position,
                    'team': player.team,
                    'status': player.status,
                    'injury_status': player.injury_status,
                    'fantasy_positions': player.fantasy_positions
                }
            
            # Get owned players from database
            if self.data_service:
                from .database.models import RosterPlayer, Roster
                from .database.connection import session_scope
                
                with session_scope() as session:
                    owned_players_query = session.query(RosterPlayer.player_id).join(
                        Roster, RosterPlayer.roster_id == Roster.roster_id
                    ).filter(Roster.league_id == self.sleeper_client.config.league_id)
                    
                    self.owned_players = set(row[0] for row in owned_players_query.all())
            
            print(f"Found {len(self.available_players)} available players from database")
        else:
            # Get all players and rosters from API
            all_players = self.sleeper_client.get_players_data()
            all_rosters = self.sleeper_client.get_rosters()
            
            # Create set of owned players
            owned_players = set()
            for roster in all_rosters:
                if roster.get('players'):
                    owned_players.update(roster['players'])
            
            self.owned_players = owned_players
            
            # Filter for available fantasy-relevant players
            available_players = {}
            fantasy_positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']
            
            for player_id, player_data in all_players.items():
                if (player_data and 
                    player_id not in owned_players and
                    player_data.get('position') in fantasy_positions and
                    player_data.get('status') == 'Active'):
                    
                    available_players[player_id] = player_data
            
            self.available_players = available_players
            print(f"Found {len(available_players)} available players from API")

    def _identify_positional_needs(self) -> None:
        """Identify roster weaknesses and positional needs."""
        # Get my roster from database or API
        if self.use_database and self.sleeper_client.config.user_id:
            my_roster = self.sleeper_client.get_my_roster_from_db()
        else:
            my_roster = self.sleeper_client.get_my_roster()
        
        if not my_roster:
            self.positional_needs = {}
            return
        
        my_players = my_roster.get('players', [])
        position_counts = defaultdict(int)
        position_quality = defaultdict(list)
        
        # Ensure projections are available
        if not self.lineup_optimizer.projections:
            self.lineup_optimizer.generate_projections()
        
        # Analyze current roster composition
        for player_id in my_players:
            if player_id in self.lineup_optimizer.projections:
                proj = self.lineup_optimizer.projections[player_id]
                position_counts[proj.position] += 1
                position_quality[proj.position].append(proj.projected_points)
        
        # Identify needs based on depth and quality
        needs = {}
        league_settings = self.sleeper_client.get_league_settings()
        roster_positions = league_settings.get('roster_positions', [])
        
        # Calculate minimum requirements
        min_requirements = {
            'QB': 1,
            'RB': 2,
            'WR': 2,
            'TE': 1,
            'K': 1,
            'DEF': 1
        }
        
        # Add flex requirements (additional RB/WR/TE)
        flex_positions = self.sleeper_client.get_flex_positions()
        flex_count = len([pos for pos in roster_positions if 'FLEX' in pos])
        
        for position, min_count in min_requirements.items():
            current_count = position_counts.get(position, 0)
            current_quality = position_quality.get(position, [0])
            avg_quality = np.mean(current_quality)
            
            # Determine need level
            if current_count < min_count:
                need_level = 'critical'
            elif position in ['RB', 'WR', 'TE'] and current_count < min_count + (flex_count // 2):
                need_level = 'high'
            elif avg_quality < 10:  # Below average projection
                need_level = 'moderate'
            else:
                need_level = 'low'
            
            needs[position] = {
                'level': need_level,
                'current_count': current_count,
                'min_required': min_count,
                'avg_quality': avg_quality,
                'priority_score': self._calculate_position_priority(position, need_level, current_count)
            }
        
        self.positional_needs = needs

    def _calculate_position_priority(self, position: str, need_level: str, current_count: int) -> float:
        """Calculate priority score for position needs."""
        base_scores = {
            'critical': 10.0,
            'high': 7.0,
            'moderate': 4.0,
            'low': 1.0
        }
        
        # Position multipliers based on importance and scarcity
        position_multipliers = {
            'QB': 0.8,  # Less critical due to streaming options
            'RB': 1.2,  # High priority due to scarcity
            'WR': 1.0,  # Standard priority
            'TE': 0.9,  # Moderate priority
            'K': 0.3,   # Low priority
            'DEF': 0.4  # Low priority
        }
        
        base_score = base_scores.get(need_level, 1.0)
        multiplier = position_multipliers.get(position, 1.0)
        
        # Penalty for having too few players
        depth_penalty = max(0, 2 - current_count) * 2
        
        return base_score * multiplier + depth_penalty

    def _analyze_upcoming_matchups(self, week: int = None) -> None:
        """Analyze upcoming matchups for available players."""
        if week is None:
            week = self._get_current_week()
        
        # This would typically integrate with external matchup data
        # For now, implement basic team strength analysis
        
        team_strengths = self._get_team_strength_ratings()
        team_matchups = self._get_team_matchups(week)
        
        matchup_ratings = {}
        
        for player_id, player_data in self.available_players.items():
            team = player_data.get('team', '')
            position = player_data.get('position', '')
            
            # Get opponent and calculate matchup rating
            opponent = team_matchups.get(team, '')
            if opponent:
                team_strength = team_strengths.get(team, 0.5)
                opponent_strength = team_strengths.get(opponent, 0.5)
                
                # Higher rating means better matchup
                matchup_rating = self._calculate_matchup_rating(
                    position, team_strength, opponent_strength
                )
                matchup_ratings[player_id] = matchup_rating
            else:
                matchup_ratings[player_id] = 0.5  # Neutral
        
        self.upcoming_matchups = matchup_ratings

    def _get_team_strength_ratings(self) -> Dict[str, float]:
        """Get team strength ratings (0.0 to 1.0)."""
        # Simplified team ratings - would use external data in practice
        return {
            'BUF': 0.9, 'KC': 0.85, 'DAL': 0.8, 'SF': 0.8,
            'MIA': 0.75, 'CIN': 0.75, 'PHI': 0.75, 'BAL': 0.7,
            # ... would include all 32 teams
        }

    def _get_team_matchups(self, week: int) -> Dict[str, str]:
        """Get team matchups for the given week."""
        # This would typically come from NFL schedule data
        # Simplified example matchups
        return {
            'BUF': 'NYJ', 'NYJ': 'BUF',
            'KC': 'DEN', 'DEN': 'KC',
            # ... would include all games for the week
        }

    def _calculate_matchup_rating(self, position: str, team_strength: float, opponent_strength: float) -> float:
        """Calculate matchup rating for a player."""
        # Basic matchup logic
        strength_diff = team_strength - opponent_strength
        
        # Position-specific adjustments
        position_factors = {
            'QB': 1.0,
            'RB': 1.1,  # RBs benefit more from good teams
            'WR': 0.9,  # WRs can perform well even on bad teams
            'TE': 0.8,
            'K': 1.2,   # Kickers benefit from good offenses
            'DEF': 1.3  # Defenses benefit greatly from facing bad offenses
        }
        
        factor = position_factors.get(position, 1.0)
        rating = 0.5 + (strength_diff * factor * 0.3)
        
        return max(0.0, min(1.0, rating))

    def _find_immediate_needs(self) -> List[WaiverRecommendation]:
        """Find players to address immediate roster needs."""
        recommendations = []
        
        # Sort positions by priority
        sorted_positions = sorted(
            self.positional_needs.items(),
            key=lambda x: x[1]['priority_score'],
            reverse=True
        )
        
        for position, needs in sorted_positions:
            if needs['level'] in ['critical', 'high']:
                position_recommendations = self._find_position_recommendations(
                    position, needs, max_players=3
                )
                recommendations.extend(position_recommendations)
        
        # Sort by overall priority
        recommendations.sort(key=lambda x: x.pickup_priority, reverse=True)
        return recommendations[:10]  # Top 10 recommendations

    def _find_position_recommendations(self, position: str, needs: Dict, max_players: int = 3) -> List[WaiverRecommendation]:
        """Find recommendations for a specific position."""
        recommendations = []
        
        # Filter available players by position
        position_players = [
            (pid, pdata) for pid, pdata in self.available_players.items()
            if pdata.get('position') == position
        ]
        
        # Generate projections if not available
        if not self.lineup_optimizer.projections:
            self.lineup_optimizer.generate_projections()
        
        # Score each player
        player_scores = []
        for player_id, player_data in position_players:
            if player_id in self.lineup_optimizer.projections:
                projection = self.lineup_optimizer.projections[player_id]
                
                # Calculate pickup score
                base_score = projection.projected_points
                matchup_bonus = self.upcoming_matchups.get(player_id, 0.5) * 5
                ownership_trend_bonus = self._get_ownership_trend_bonus(player_id)
                
                total_score = base_score + matchup_bonus + ownership_trend_bonus
                
                player_scores.append((player_id, player_data, projection, total_score))
        
        # Sort by score and take top players
        player_scores.sort(key=lambda x: x[3], reverse=True)
        
        for i, (player_id, player_data, projection, score) in enumerate(player_scores[:max_players]):
            priority = int(score * 10) + (needs['priority_score'] * 10)
            
            # Find drop candidates
            drop_candidates = self._find_drop_candidates_for_position(position)
            
            # Determine pickup reason
            reason = self._determine_pickup_reason(position, needs, projection)
            
            recommendation = WaiverRecommendation(
                player_id=player_id,
                player_name=projection.name,
                position=position,
                team=projection.team,
                pickup_priority=priority,
                projected_points=projection.projected_points,
                pickup_reason=reason,
                drop_candidates=drop_candidates,
                confidence_score=min(1.0, score / 20),
                ownership_trend=self._get_ownership_trend(player_id),
                matchup_rating=self.upcoming_matchups.get(player_id, 0.5),
                injury_replacement=False
            )
            
            recommendations.append(recommendation)
        
        return recommendations

    def _get_ownership_trend_bonus(self, player_id: str) -> float:
        """Get bonus points based on ownership trend."""
        # Would analyze trending data from Sleeper
        trending_adds = self.sleeper_client.get_trending_players(add_type='add')
        
        for player in trending_adds:
            if player.get('player_id') == player_id:
                return 2.0  # Bonus for trending up
        
        return 0.0

    def _get_ownership_trend(self, player_id: str) -> str:
        """Determine ownership trend for a player."""
        trending_adds = self.sleeper_client.get_trending_players(add_type='add')
        trending_drops = self.sleeper_client.get_trending_players(add_type='drop')
        
        add_ids = [p.get('player_id') for p in trending_adds]
        drop_ids = [p.get('player_id') for p in trending_drops]
        
        if player_id in add_ids:
            return 'rising'
        elif player_id in drop_ids:
            return 'falling'
        else:
            return 'stable'

    def _find_drop_candidates_for_position(self, position: str) -> List[Dict[str, Any]]:
        """Find players on your roster who could be dropped."""
        my_roster = self.sleeper_client.get_my_roster()
        if not my_roster:
            return []
        
        drop_candidates = []
        my_players = my_roster.get('players', [])
        
        for player_id in my_players:
            if player_id in self.lineup_optimizer.projections:
                proj = self.lineup_optimizer.projections[player_id]
                
                # Consider players in the same position or lower-value players
                if (proj.position == position or 
                    proj.projected_points < 5 or 
                    proj.injury_risk > 0.7):
                    
                    drop_candidates.append({
                        'player_id': player_id,
                        'name': proj.name,
                        'position': proj.position,
                        'projected_points': proj.projected_points,
                        'drop_reason': self._get_drop_reason(proj)
                    })
        
        # Sort by least valuable first
        drop_candidates.sort(key=lambda x: x['projected_points'])
        return drop_candidates[:3]

    def _get_drop_reason(self, projection: PlayerProjection) -> str:
        """Get reason for considering dropping a player."""
        if projection.injury_risk > 0.7:
            return 'Injury concern'
        elif projection.projected_points < 5:
            return 'Low production'
        else:
            return 'Roster upgrade'

    def _determine_pickup_reason(self, position: str, needs: Dict, projection: PlayerProjection) -> str:
        """Determine the reason for picking up a player."""
        if needs['level'] == 'critical':
            return f"Fill critical {position} need"
        elif needs['level'] == 'high':
            return f"Add {position} depth"
        elif projection.projected_points > 15:
            return "High upside play"
        elif self.upcoming_matchups.get(projection.player_id, 0.5) > 0.7:
            return "Favorable matchup"
        else:
            return "Roster improvement"

    def _find_emergency_pickups(self) -> List[WaiverRecommendation]:
        """Find emergency pickups for injured/unavailable players."""
        emergency_picks = []
        
        my_roster = self.sleeper_client.get_my_roster()
        if not my_roster:
            return emergency_picks
        
        my_players = my_roster.get('players', [])
        
        # Check for injured/questionable players
        for player_id in my_players:
            if player_id in self.lineup_optimizer.projections:
                proj = self.lineup_optimizer.projections[player_id]
                
                if proj.injury_risk > 0.5:  # Injured/questionable
                    # Find replacement options
                    replacements = self._find_position_recommendations(
                        proj.position, 
                        {'level': 'high', 'priority_score': 8.0},
                        max_players=2
                    )
                    
                    for replacement in replacements:
                        replacement.injury_replacement = True
                        replacement.pickup_reason = f"Replace injured {proj.name}"
                        emergency_picks.append(replacement)
        
        return emergency_picks

    def _find_stash_candidates(self) -> List[WaiverRecommendation]:
        """Find players worth stashing for future weeks."""
        stash_candidates = []
        
        # Look for players with high upside but currently low ownership
        for player_id, player_data in self.available_players.items():
            if player_id in self.lineup_optimizer.projections:
                projection = self.lineup_optimizer.projections[player_id]
                
                # Criteria for stash candidates
                if (projection.projected_ceiling > 20 and  # High ceiling
                    projection.ownership_pct < 15 and      # Low ownership
                    projection.injury_risk < 0.3):         # Healthy
                    
                    stash_rec = WaiverRecommendation(
                        player_id=player_id,
                        player_name=projection.name,
                        position=projection.position,
                        team=projection.team,
                        pickup_priority=int(projection.projected_ceiling * 2),
                        projected_points=projection.projected_points,
                        pickup_reason="High upside stash",
                        drop_candidates=self._find_drop_candidates_for_position(projection.position),
                        confidence_score=0.6,
                        ownership_trend=self._get_ownership_trend(player_id),
                        matchup_rating=self.upcoming_matchups.get(player_id, 0.5),
                        injury_replacement=False
                    )
                    
                    stash_candidates.append(stash_rec)
        
        stash_candidates.sort(key=lambda x: x.pickup_priority, reverse=True)
        return stash_candidates[:5]

    def _find_streaming_options(self) -> Dict[str, List[WaiverRecommendation]]:
        """Find streaming options for K and DEF positions."""
        streaming = {
            'K': [],
            'DEF': []
        }
        
        for position in ['K', 'DEF']:
            position_players = [
                (pid, pdata) for pid, pdata in self.available_players.items()
                if pdata.get('position') == position
            ]
            
            # Score based heavily on matchups for streaming
            streaming_scores = []
            for player_id, player_data in position_players:
                matchup_rating = self.upcoming_matchups.get(player_id, 0.5)
                
                if player_id in self.lineup_optimizer.projections:
                    projection = self.lineup_optimizer.projections[player_id]
                    score = projection.projected_points + (matchup_rating * 10)
                    streaming_scores.append((player_id, player_data, projection, score))
            
            # Sort and create recommendations
            streaming_scores.sort(key=lambda x: x[3], reverse=True)
            
            for player_id, player_data, projection, score in streaming_scores[:3]:
                rec = WaiverRecommendation(
                    player_id=player_id,
                    player_name=projection.name,
                    position=position,
                    team=projection.team,
                    pickup_priority=int(score),
                    projected_points=projection.projected_points,
                    pickup_reason=f"Streaming option - good matchup",
                    drop_candidates=self._find_drop_candidates_for_position(position),
                    confidence_score=matchup_rating,
                    ownership_trend='stable',
                    matchup_rating=self.upcoming_matchups.get(player_id, 0.5),
                    injury_replacement=False
                )
                
                streaming[position].append(rec)
        
        return streaming

    def _identify_drop_candidates(self) -> List[Dict[str, Any]]:
        """Identify players on roster who could be dropped."""
        my_roster = self.sleeper_client.get_my_roster()
        if not my_roster:
            return []
        
        drop_candidates = []
        my_players = my_roster.get('players', [])
        
        for player_id in my_players:
            if player_id in self.lineup_optimizer.projections:
                proj = self.lineup_optimizer.projections[player_id]
                
                # Calculate drop score (higher = more droppable)
                drop_score = 0
                
                if proj.projected_points < 5:
                    drop_score += 5
                if proj.injury_risk > 0.5:
                    drop_score += 3
                if proj.ownership_pct < 10:
                    drop_score += 2
                
                if drop_score > 3:
                    drop_candidates.append({
                        'player_id': player_id,
                        'name': proj.name,
                        'position': proj.position,
                        'projected_points': proj.projected_points,
                        'drop_score': drop_score,
                        'drop_reason': self._get_drop_reason(proj)
                    })
        
        drop_candidates.sort(key=lambda x: x['drop_score'], reverse=True)
        return drop_candidates

    def _get_current_week(self) -> int:
        """Get current NFL week."""
        now = datetime.now()
        season_start = datetime(2024, 9, 5)
        if now < season_start:
            return 1
        days_since_start = (now - season_start).days
        return min(18, max(1, (days_since_start // 7) + 1))

    def export_waiver_analysis(self, analysis: WaiverAnalysis, output_file: str = "data/processed/waiver_analysis.json"):
        """Export waiver analysis to file."""
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        def recommendation_to_dict(rec: WaiverRecommendation) -> Dict:
            return {
                'player_id': rec.player_id,
                'player_name': rec.player_name,
                'position': rec.position,
                'team': rec.team,
                'pickup_priority': rec.pickup_priority,
                'projected_points': rec.projected_points,
                'pickup_reason': rec.pickup_reason,
                'drop_candidates': rec.drop_candidates,
                'confidence_score': rec.confidence_score,
                'ownership_trend': rec.ownership_trend,
                'matchup_rating': rec.matchup_rating,
                'injury_replacement': rec.injury_replacement
            }
        
        export_data = {
            'analysis_date': datetime.now().isoformat(),
            'recommendations': [recommendation_to_dict(rec) for rec in analysis.recommendations],
            'drop_candidates': analysis.drop_candidates,
            'emergency_pickups': [recommendation_to_dict(rec) for rec in analysis.emergency_pickups],
            'stash_candidates': [recommendation_to_dict(rec) for rec in analysis.stash_candidates],
            'streaming_options': {
                pos: [recommendation_to_dict(rec) for rec in recs]
                for pos, recs in analysis.streaming_options.items()
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Exported waiver analysis to {output_file}")


def main():
    """Main function for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fantasy Football Waiver Wire Analyzer")
    parser.add_argument("--league-id", required=True, help="Sleeper league ID")
    parser.add_argument("--user-id", required=True, help="Your Sleeper user ID")
    parser.add_argument("--week", type=int, help="Week to analyze for")
    parser.add_argument("--output", default="data/processed/waiver_analysis.json")
    
    args = parser.parse_args()
    
    # Setup clients
    config = SleeperConfig(league_id=args.league_id, user_id=args.user_id)
    sleeper_client = SleeperClient(config)
    lineup_optimizer = LineupOptimizer(sleeper_client)
    
    waiver_analyzer = WaiverAnalyzer(sleeper_client, lineup_optimizer)
    
    print("Performing waiver wire analysis...")
    analysis = waiver_analyzer.analyze_waiver_wire(args.week)
    
    print(f"\n=== WAIVER WIRE RECOMMENDATIONS ===")
    print(f"Found {len(analysis.recommendations)} immediate recommendations:")
    
    for i, rec in enumerate(analysis.recommendations[:5], 1):
        print(f"\n{i}. {rec.player_name} ({rec.position} - {rec.team})")
        print(f"   Priority: {rec.pickup_priority} | Projected: {rec.projected_points:.1f} pts")
        print(f"   Reason: {rec.pickup_reason}")
        print(f"   Matchup Rating: {rec.matchup_rating:.2f}")
        
        if rec.drop_candidates:
            drops = [d['name'] for d in rec.drop_candidates[:2]]
            print(f"   Consider dropping: {', '.join(drops)}")
    
    if analysis.emergency_pickups:
        print(f"\n=== EMERGENCY PICKUPS ===")
        for rec in analysis.emergency_pickups[:3]:
            print(f"• {rec.player_name} ({rec.position}) - {rec.pickup_reason}")
    
    if analysis.streaming_options.get('DEF'):
        print(f"\n=== DEFENSE STREAMING ===")
        for rec in analysis.streaming_options['DEF'][:3]:
            print(f"• {rec.player_name} (Matchup: {rec.matchup_rating:.2f})")
    
    # Export results
    waiver_analyzer.export_waiver_analysis(analysis, args.output)


if __name__ == "__main__":
    main()