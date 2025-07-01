"""Trade analysis and recommendation system for fantasy football."""

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
from .database.data_service import DataService

logger = logging.getLogger(__name__)


@dataclass
class TradeProposal:
    """Represents a trade proposal."""
    giving_players: List[str]  # player IDs
    receiving_players: List[str]  # player IDs
    trade_partner: str  # user ID
    proposed_date: datetime
    trade_value: float
    confidence_score: float


@dataclass
class TradeAnalysis:
    """Analysis results for a trade."""
    trade_proposal: TradeProposal
    value_difference: float  # positive means favorable to you
    roster_improvement: float
    positional_needs_addressed: List[str]
    risk_assessment: Dict[str, float]
    recommendation: str  # 'accept', 'reject', 'counter'
    counter_suggestions: List[TradeProposal]


class TradeAnalyzer:
    """Analyze and recommend trades in fantasy football."""

    def __init__(self, sleeper_client: SleeperClient, lineup_optimizer: LineupOptimizer, use_database: bool = True):
        self.sleeper_client = sleeper_client
        self.lineup_optimizer = lineup_optimizer
        self.use_database = use_database
        self.data_service = DataService() if use_database else None
        self.trade_history = []
        self.player_values = {}
        self.positional_values = {}
        self.scarcity_index = {}

    def calculate_player_values(self, week: int = None) -> Dict[str, float]:
        """Calculate current market values for all players."""
        if not self.lineup_optimizer.projections:
            self.lineup_optimizer.generate_projections(week)
        
        projections = self.lineup_optimizer.projections
        
        # Calculate positional replacement values
        replacement_values = self._calculate_replacement_values(projections)
        
        # Calculate scarcity factors
        scarcity_factors = self._calculate_scarcity_factors(projections)
        
        player_values = {}
        
        for player_id, projection in projections.items():
            position = projection.position
            base_value = projection.projected_points
            
            # Adjust for replacement value
            replacement_value = replacement_values.get(position, 0)
            value_over_replacement = max(0, base_value - replacement_value)
            
            # Apply scarcity factor
            scarcity_factor = scarcity_factors.get(position, 1.0)
            
            # Calculate final value
            player_value = value_over_replacement * scarcity_factor
            
            # Adjust for injury risk and consistency
            injury_adjustment = 1.0 - (projection.injury_risk * 0.3)
            consistency_factor = self._calculate_consistency_factor(player_id)
            
            final_value = player_value * injury_adjustment * consistency_factor
            player_values[player_id] = final_value
        
        self.player_values = player_values
        return player_values

    def _calculate_replacement_values(self, projections: Dict[str, PlayerProjection]) -> Dict[str, float]:
        """Calculate replacement level values by position."""
        position_players = defaultdict(list)
        
        for projection in projections.values():
            position_players[projection.position].append(projection.projected_points)
        
        replacement_values = {}
        
        # Define replacement thresholds (e.g., 12th best RB in 12-team league)
        replacement_thresholds = {
            'QB': 12,  # 12th QB
            'RB': 24,  # 24th RB (RB1/RB2 for 12 teams)
            'WR': 30,  # 30th WR (WR1/WR2/WR3 for 12 teams)
            'TE': 12,  # 12th TE
            'K': 12,   # 12th K
            'DEF': 12  # 12th DEF
        }
        
        for position, players in position_players.items():
            players_sorted = sorted(players, reverse=True)
            threshold = replacement_thresholds.get(position, 12)
            
            if len(players_sorted) > threshold:
                replacement_values[position] = players_sorted[threshold - 1]
            else:
                replacement_values[position] = min(players_sorted) if players_sorted else 0
        
        return replacement_values

    def _calculate_scarcity_factors(self, projections: Dict[str, PlayerProjection]) -> Dict[str, float]:
        """Calculate position scarcity factors."""
        position_counts = defaultdict(int)
        position_top_tier = defaultdict(int)
        
        for projection in projections.values():
            position_counts[projection.position] += 1
            if projection.projected_points >= 15:  # Arbitrary top-tier threshold
                position_top_tier[projection.position] += 1
        
        scarcity_factors = {}
        for position in position_counts:
            # More scarce positions get higher multipliers
            total_players = position_counts[position]
            top_tier_players = position_top_tier[position]
            
            if total_players > 0:
                scarcity_ratio = top_tier_players / total_players
                # Invert the ratio so scarce positions have higher values
                scarcity_factors[position] = 1.0 + (1.0 - scarcity_ratio) * 0.5
            else:
                scarcity_factors[position] = 1.0
        
        return scarcity_factors

    def _calculate_consistency_factor(self, player_id: str) -> float:
        """Calculate player consistency factor based on historical performance."""
        # This would typically use historical game-by-game data
        # For now, use a simplified approach
        
        try:
            player_stats = self.sleeper_client.get_player_stats(player_id)
            # Simplified consistency calculation
            # In reality, you'd analyze week-to-week variance
            return 1.0  # Placeholder
        except:
            return 0.9  # Default slightly lower for unknown players

    def analyze_trade(self, trade_proposal: TradeProposal) -> TradeAnalysis:
        """Analyze a specific trade proposal."""
        if not self.player_values:
            self.calculate_player_values()
        
        # Calculate value difference
        giving_value = sum(
            self.player_values.get(player_id, 0) 
            for player_id in trade_proposal.giving_players
        )
        receiving_value = sum(
            self.player_values.get(player_id, 0) 
            for player_id in trade_proposal.receiving_players
        )
        
        value_difference = receiving_value - giving_value
        
        # Analyze roster impact
        current_roster = self.sleeper_client.get_my_roster()
        roster_improvement = self._calculate_roster_improvement(
            current_roster, trade_proposal
        )
        
        # Assess positional needs
        positional_needs = self._assess_positional_needs(current_roster, trade_proposal)
        
        # Risk assessment
        risk_assessment = self._assess_trade_risks(trade_proposal)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            value_difference, roster_improvement, risk_assessment
        )
        
        # Generate counter-offers if rejecting
        counter_suggestions = []
        if recommendation == 'reject':
            counter_suggestions = self._generate_counter_offers(trade_proposal)
        elif recommendation == 'counter':
            counter_suggestions = self._generate_counter_offers(trade_proposal, improve=True)
        
        return TradeAnalysis(
            trade_proposal=trade_proposal,
            value_difference=value_difference,
            roster_improvement=roster_improvement,
            positional_needs_addressed=positional_needs,
            risk_assessment=risk_assessment,
            recommendation=recommendation,
            counter_suggestions=counter_suggestions
        )

    def _calculate_roster_improvement(self, current_roster: Dict, trade_proposal: TradeProposal) -> float:
        """Calculate how much the trade improves overall roster strength."""
        # Get current roster from database if not provided
        if not current_roster and self.use_database and self.sleeper_client.config.user_id:
            current_roster = self.sleeper_client.get_my_roster_from_db()
        
        if not current_roster:
            return 0.0
        
        # Simulate roster before and after trade
        current_players = set(current_roster.get('players', []))
        
        # Remove giving players, add receiving players
        new_players = current_players.copy()
        for player_id in trade_proposal.giving_players:
            new_players.discard(player_id)
        for player_id in trade_proposal.receiving_players:
            new_players.add(player_id)
        
        # Calculate lineup scores before and after
        current_lineup_score = self._calculate_best_lineup_score(current_players)
        new_lineup_score = self._calculate_best_lineup_score(new_players)
        
        return new_lineup_score - current_lineup_score

    def _calculate_best_lineup_score(self, player_ids: set) -> float:
        """Calculate the best possible lineup score from available players."""
        # Simplified - would use lineup optimizer in practice
        total_value = sum(
            self.player_values.get(player_id, 0) 
            for player_id in player_ids
        )
        return total_value

    def _assess_positional_needs(self, current_roster: Dict, trade_proposal: TradeProposal) -> List[str]:
        """Assess which positional needs are addressed by the trade."""
        if not self.lineup_optimizer.projections:
            return []
        
        receiving_positions = []
        for player_id in trade_proposal.receiving_players:
            if player_id in self.lineup_optimizer.projections:
                pos = self.lineup_optimizer.projections[player_id].position
                receiving_positions.append(pos)
        
        # Simple logic - in practice, would analyze depth charts
        needs_addressed = list(set(receiving_positions))
        return needs_addressed

    def _assess_trade_risks(self, trade_proposal: TradeProposal) -> Dict[str, float]:
        """Assess various risks associated with the trade."""
        risks = {
            'injury_risk': 0.0,
            'schedule_risk': 0.0,
            'age_risk': 0.0,
            'team_dependency': 0.0
        }
        
        all_players = trade_proposal.giving_players + trade_proposal.receiving_players
        
        for player_id in all_players:
            if player_id in self.lineup_optimizer.projections:
                projection = self.lineup_optimizer.projections[player_id]
                risks['injury_risk'] += projection.injury_risk
        
        # Normalize risks
        num_players = len(all_players)
        if num_players > 0:
            for risk in risks:
                risks[risk] /= num_players
        
        return risks

    def _generate_recommendation(self, value_diff: float, roster_improvement: float, risks: Dict[str, float]) -> str:
        """Generate trade recommendation based on analysis."""
        # Simple decision logic
        risk_penalty = sum(risks.values()) * 0.1
        total_benefit = value_diff + roster_improvement - risk_penalty
        
        if total_benefit > 2.0:
            return 'accept'
        elif total_benefit > -1.0:
            return 'counter'
        else:
            return 'reject'

    def _generate_counter_offers(self, original_trade: TradeProposal, improve: bool = False) -> List[TradeProposal]:
        """Generate counter-offer suggestions."""
        counter_offers = []
        
        # This is a simplified implementation
        # In practice, would use more sophisticated algorithms
        
        # Example: Suggest removing/adding players to balance the trade
        if improve and len(original_trade.giving_players) > 1:
            # Suggest removing one of your players
            for i, player_id in enumerate(original_trade.giving_players):
                modified_giving = original_trade.giving_players.copy()
                modified_giving.pop(i)
                
                counter_offers.append(TradeProposal(
                    giving_players=modified_giving,
                    receiving_players=original_trade.receiving_players,
                    trade_partner=original_trade.trade_partner,
                    proposed_date=datetime.now(),
                    trade_value=0.0,  # Would calculate
                    confidence_score=0.0  # Would calculate
                ))
        
        return counter_offers[:3]  # Return top 3 suggestions

    def find_trade_opportunities(self, target_positions: List[str] = None) -> List[TradeProposal]:
        """Find potential trade opportunities across the league."""
        if not self.player_values:
            self.calculate_player_values()
        
        opportunities = []
        
        # Get my roster from database or API
        if self.use_database and self.sleeper_client.config.user_id:
            my_roster = self.sleeper_client.get_my_roster_from_db()
        else:
            my_roster = self.sleeper_client.get_my_roster()
        
        if not my_roster:
            return opportunities
        
        my_players = set(my_roster.get('players', []))
        
        # Get all rosters from database or API
        if self.use_database and self.data_service:
            all_rosters_db = self.data_service.data_service.get_rosters()
            all_rosters = []
            for roster in all_rosters_db:
                player_ids = self.data_service.get_roster_players(roster.roster_id)
                roster_dict = {
                    'roster_id': roster.roster_id,
                    'owner_id': roster.user_id,
                    'players': player_ids
                }
                all_rosters.append(roster_dict)
        else:
            all_rosters = self.sleeper_client.get_rosters()
        
        for roster in all_rosters:
            if roster.get('owner_id') == self.sleeper_client.config.user_id:
                continue  # Skip own roster
            
            their_players = set(roster.get('players', []))
            
            # Find mutually beneficial trades
            potential_trades = self._find_mutually_beneficial_trades(
                my_players, their_players, roster.get('owner_id', '')
            )
            opportunities.extend(potential_trades)
        
        # Sort by potential value
        opportunities.sort(key=lambda x: x.trade_value, reverse=True)
        return opportunities[:10]  # Return top 10

    def _find_mutually_beneficial_trades(self, my_players: set, their_players: set, owner_id: str) -> List[TradeProposal]:
        """Find trades that could benefit both teams."""
        trades = []
        
        # Simple 1-for-1 and 2-for-1 trade analysis
        for my_player in my_players:
            my_value = self.player_values.get(my_player, 0)
            
            for their_player in their_players:
                their_value = self.player_values.get(their_player, 0)
                
                # Look for roughly equal value trades
                value_diff = abs(my_value - their_value)
                if value_diff < 2.0 and their_value > my_value:  # Slight upgrade
                    trades.append(TradeProposal(
                        giving_players=[my_player],
                        receiving_players=[their_player],
                        trade_partner=owner_id,
                        proposed_date=datetime.now(),
                        trade_value=their_value - my_value,
                        confidence_score=0.8
                    ))
        
        return trades

    def track_trade_history(self, weeks_back: int = 4) -> List[Dict[str, Any]]:
        """Track recent trades in the league to understand market values."""
        trade_history = []
        
        if self.use_database and self.data_service:
            # Get transactions from database
            from .database.models import Transaction
            from .database.connection import session_scope
            
            with session_scope() as session:
                current_week = self._get_current_week()
                start_week = max(1, current_week - weeks_back)
                
                transactions = session.query(Transaction).filter(
                    Transaction.league_id == self.sleeper_client.config.league_id,
                    Transaction.type == 'trade',
                    Transaction.week >= start_week,
                    Transaction.week <= current_week
                ).all()
                
                for transaction in transactions:
                    trade_data = {
                        'transaction_id': transaction.transaction_id,
                        'week': transaction.week,
                        'roster_ids': transaction.roster_ids,
                        'adds': transaction.adds,
                        'drops': transaction.drops,
                        'created': transaction.created,
                        'processed_date': transaction.processed_date
                    }
                    trade_history.append(trade_data)
        else:
            # Get transactions from API
            for week in range(max(1, self._get_current_week() - weeks_back), self._get_current_week() + 1):
                transactions = self.sleeper_client.get_transactions(week)
                
                for transaction in transactions:
                    if transaction.get('type') == 'trade':
                        trade_data = self._parse_trade_transaction(transaction)
                        if trade_data:
                            trade_history.append(trade_data)
        
        self.trade_history = trade_history
        return trade_history

    def _parse_trade_transaction(self, transaction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a trade transaction from Sleeper API."""
        if not transaction.get('roster_ids') or len(transaction['roster_ids']) != 2:
            return None
        
        # Extract trade details
        adds = transaction.get('adds', {})
        drops = transaction.get('drops', {})
        
        roster1_id = transaction['roster_ids'][0]
        roster2_id = transaction['roster_ids'][1]
        
        roster1_gave = [pid for pid, rid in drops.items() if rid == roster1_id]
        roster1_got = [pid for pid, rid in adds.items() if rid == roster1_id]
        
        return {
            'transaction_id': transaction.get('transaction_id'),
            'week': transaction.get('leg', 0),
            'roster1_id': roster1_id,
            'roster1_gave': roster1_gave,
            'roster1_got': roster1_got,
            'roster2_id': roster2_id,
            'roster2_gave': roster1_got,  # What roster1 got, roster2 gave
            'roster2_got': roster1_gave,  # What roster1 gave, roster2 got
            'timestamp': transaction.get('created', 0)
        }

    def _get_current_week(self) -> int:
        """Get current NFL week."""
        # Simple logic - would use actual NFL schedule
        now = datetime.now()
        season_start = datetime(2024, 9, 5)
        if now < season_start:
            return 1
        days_since_start = (now - season_start).days
        return min(18, max(1, (days_since_start // 7) + 1))

    def export_trade_analysis(self, analyses: List[TradeAnalysis], output_file: str = "data/processed/trade_analysis.json"):
        """Export trade analyses to file."""
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Convert to serializable format
        export_data = []
        for analysis in analyses:
            export_data.append({
                'trade_proposal': {
                    'giving_players': analysis.trade_proposal.giving_players,
                    'receiving_players': analysis.trade_proposal.receiving_players,
                    'trade_partner': analysis.trade_proposal.trade_partner,
                    'proposed_date': analysis.trade_proposal.proposed_date.isoformat(),
                    'trade_value': analysis.trade_proposal.trade_value,
                    'confidence_score': analysis.trade_proposal.confidence_score
                },
                'value_difference': analysis.value_difference,
                'roster_improvement': analysis.roster_improvement,
                'positional_needs_addressed': analysis.positional_needs_addressed,
                'risk_assessment': analysis.risk_assessment,
                'recommendation': analysis.recommendation,
                'counter_suggestions': len(analysis.counter_suggestions)
            })
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Exported {len(analyses)} trade analyses to {output_file}")


def main():
    """Main function for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fantasy Football Trade Analyzer")
    parser.add_argument("--league-id", required=True, help="Sleeper league ID")
    parser.add_argument("--user-id", required=True, help="Your Sleeper user ID")
    parser.add_argument("--find-opportunities", action="store_true", help="Find trade opportunities")
    parser.add_argument("--track-history", action="store_true", help="Track recent trade history")
    parser.add_argument("--output", default="data/processed/trade_analysis.json")
    
    args = parser.parse_args()
    
    # Setup clients
    config = SleeperConfig(league_id=args.league_id, user_id=args.user_id)
    sleeper_client = SleeperClient(config)
    lineup_optimizer = LineupOptimizer(sleeper_client)
    
    trade_analyzer = TradeAnalyzer(sleeper_client, lineup_optimizer)
    
    if args.find_opportunities:
        print("Finding trade opportunities...")
        opportunities = trade_analyzer.find_trade_opportunities()
        
        if opportunities:
            print(f"\nFound {len(opportunities)} potential trades:")
            for i, trade in enumerate(opportunities[:5], 1):
                giving_names = [
                    lineup_optimizer.projections.get(pid, type('obj', (object,), {'name': 'Unknown'})).name 
                    for pid in trade.giving_players
                ]
                receiving_names = [
                    lineup_optimizer.projections.get(pid, type('obj', (object,), {'name': 'Unknown'})).name 
                    for pid in trade.receiving_players
                ]
                
                print(f"\n{i}. Give: {', '.join(giving_names)}")
                print(f"   Get: {', '.join(receiving_names)}")
                print(f"   Value: +{trade.trade_value:.1f}")
        else:
            print("No favorable trade opportunities found.")
    
    if args.track_history:
        print("Tracking recent trade history...")
        history = trade_analyzer.track_trade_history()
        print(f"Found {len(history)} recent trades in the league.")


if __name__ == "__main__":
    main()