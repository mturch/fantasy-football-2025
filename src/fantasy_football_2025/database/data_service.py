"""Data service layer for database operations."""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.exc import IntegrityError

from .connection import session_scope
from .models import (
    League, User, Player, Roster, RosterPlayer, PlayerStats, 
    PlayerProjection, Matchup, Transaction, TrendingPlayer, 
    TeamSchedule, AnalysisRun
)

logger = logging.getLogger(__name__)


class DataService:
    """Service layer for database operations."""
    
    def __init__(self):
        pass
    
    # League operations
    def create_or_update_league(self, league_data: Dict[str, Any]) -> League:
        """Create or update league information."""
        with session_scope() as session:
            league = session.query(League).filter_by(
                league_id=league_data['league_id']
            ).first()
            
            if league:
                # Update existing league
                for key, value in league_data.items():
                    if hasattr(league, key):
                        setattr(league, key, value)
                league.updated_at = datetime.utcnow()
            else:
                # Create new league
                league = League(**league_data)
                session.add(league)
            
            session.flush()
            return league
    
    def get_league(self, league_id: str) -> Optional[League]:
        """Get league by ID."""
        with session_scope() as session:
            return session.query(League).filter_by(league_id=league_id).first()
    
    # User operations
    def create_or_update_users(self, users_data: List[Dict[str, Any]], league_id: str) -> List[User]:
        """Create or update multiple users."""
        users = []
        with session_scope() as session:
            for user_data in users_data:
                user_data['league_id'] = league_id
                
                user = session.query(User).filter_by(
                    user_id=user_data['user_id']
                ).first()
                
                if user:
                    # Update existing user
                    for key, value in user_data.items():
                        if hasattr(user, key):
                            setattr(user, key, value)
                    user.updated_at = datetime.utcnow()
                else:
                    # Create new user
                    user = User(**user_data)
                    session.add(user)
                
                users.append(user)
            
            session.flush()
            return users
    
    # Player operations
    def create_or_update_players(self, players_data: Dict[str, Any]) -> int:
        """Create or update players from Sleeper data."""
        updated_count = 0
        
        with session_scope() as session:
            for player_id, player_info in players_data.items():
                if not player_info:
                    continue
                
                player = session.query(Player).filter_by(player_id=player_id).first()
                
                # Prepare player data
                player_data = {
                    'player_id': player_id,
                    'first_name': player_info.get('first_name'),
                    'last_name': player_info.get('last_name'),
                    'full_name': f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip(),
                    'position': player_info.get('position'),
                    'team': player_info.get('team'),
                    'age': player_info.get('age'),
                    'height': player_info.get('height'),
                    'weight': player_info.get('weight'),
                    'years_exp': player_info.get('years_exp'),
                    'college': player_info.get('college'),
                    'status': player_info.get('status'),
                    'injury_status': player_info.get('injury_status'),
                    'fantasy_positions': player_info.get('fantasy_positions'),
                }
                
                if player:
                    # Update existing player
                    for key, value in player_data.items():
                        if hasattr(player, key):
                            setattr(player, key, value)
                    player.updated_at = datetime.utcnow()
                else:
                    # Create new player
                    player = Player(**player_data)
                    session.add(player)
                
                updated_count += 1
                
                # Commit in batches to avoid memory issues
                if updated_count % 1000 == 0:
                    session.flush()
        
        logger.info(f"Updated {updated_count} players")
        return updated_count
    
    def get_players(self, position: str = None, team: str = None, active_only: bool = True) -> List[Player]:
        """Get players with optional filters."""
        with session_scope() as session:
            query = session.query(Player)
            
            if position:
                query = query.filter(Player.position == position)
            if team:
                query = query.filter(Player.team == team)
            if active_only:
                query = query.filter(Player.status == 'Active')
            
            return query.all()
    
    def get_player(self, player_id: str) -> Optional[Player]:
        """Get player by ID."""
        with session_scope() as session:
            return session.query(Player).filter_by(player_id=player_id).first()
    
    # Roster operations
    def create_or_update_rosters(self, rosters_data: List[Dict[str, Any]], league_id: str) -> List[Roster]:
        """Create or update rosters."""
        rosters = []
        
        with session_scope() as session:
            for roster_data in rosters_data:
                roster = session.query(Roster).filter_by(
                    roster_id=roster_data['roster_id'],
                    league_id=league_id
                ).first()
                
                # Prepare roster data
                settings = roster_data.get('settings', {})
                roster_info = {
                    'roster_id': roster_data['roster_id'],
                    'league_id': league_id,
                    'user_id': roster_data.get('owner_id'),  # Map owner_id to user_id
                    'owner_id': roster_data.get('owner_id'),
                    'wins': settings.get('wins', 0),
                    'losses': settings.get('losses', 0),
                    'ties': settings.get('ties', 0),
                    'points_for': Decimal(str(settings.get('fpts', 0))),
                    'points_against': Decimal(str(settings.get('fpts_against', 0))),
                    'waiver_position': settings.get('waiver_position'),
                    'waiver_budget_used': settings.get('waiver_budget_used', 0),
                    'settings': settings
                }
                
                if roster:
                    # Update existing roster
                    for key, value in roster_info.items():
                        if hasattr(roster, key):
                            setattr(roster, key, value)
                    roster.updated_at = datetime.utcnow()
                else:
                    # Create new roster
                    roster = Roster(**roster_info)
                    session.add(roster)
                
                session.flush()
                
                # Update roster players
                self._update_roster_players(session, roster.roster_id, roster_data.get('players', []))
                
                rosters.append(roster)
        
        return rosters
    
    def _update_roster_players(self, session: Session, roster_id: int, player_ids: List[str]) -> None:
        """Update players on a roster."""
        # Remove all current players
        session.query(RosterPlayer).filter_by(roster_id=roster_id).delete()
        
        # Add new players
        for player_id in player_ids:
            roster_player = RosterPlayer(
                roster_id=roster_id,
                player_id=player_id,
                added_date=datetime.utcnow()
            )
            session.add(roster_player)
    
    def get_roster_players(self, roster_id: int) -> List[str]:
        """Get player IDs for a roster."""
        with session_scope() as session:
            roster_players = session.query(RosterPlayer).filter_by(roster_id=roster_id).all()
            return [rp.player_id for rp in roster_players]
    
    def get_user_roster(self, user_id: str, league_id: str) -> Optional[Roster]:
        """Get roster for a specific user."""
        with session_scope() as session:
            return session.query(Roster).filter_by(
                user_id=user_id, 
                league_id=league_id
            ).first()
    
    # Statistics operations
    def create_or_update_player_stats(self, stats_data: List[Dict[str, Any]]) -> int:
        """Create or update player statistics."""
        updated_count = 0
        
        with session_scope() as session:
            for stat in stats_data:
                existing_stat = session.query(PlayerStats).filter_by(
                    player_id=stat['player_id'],
                    season=stat['season'],
                    week=stat.get('week')
                ).first()
                
                if existing_stat:
                    # Update existing stat
                    for key, value in stat.items():
                        if hasattr(existing_stat, key):
                            setattr(existing_stat, key, value)
                    existing_stat.updated_at = datetime.utcnow()
                else:
                    # Create new stat
                    player_stat = PlayerStats(**stat)
                    session.add(player_stat)
                
                updated_count += 1
        
        logger.info(f"Updated {updated_count} player stats")
        return updated_count
    
    def get_player_stats(self, player_id: str, season: str, week: int = None) -> List[PlayerStats]:
        """Get player statistics."""
        with session_scope() as session:
            query = session.query(PlayerStats).filter_by(
                player_id=player_id,
                season=season
            )
            
            if week is not None:
                query = query.filter_by(week=week)
            
            return query.all()
    
    # Projections operations
    def create_or_update_projections(self, projections_data: List[Dict[str, Any]]) -> int:
        """Create or update player projections."""
        updated_count = 0
        
        with session_scope() as session:
            for proj in projections_data:
                existing_proj = session.query(PlayerProjection).filter_by(
                    player_id=proj['player_id'],
                    season=proj['season'],
                    week=proj['week'],
                    model_version=proj.get('model_version', 'default')
                ).first()
                
                if existing_proj:
                    # Update existing projection
                    for key, value in proj.items():
                        if hasattr(existing_proj, key):
                            setattr(existing_proj, key, value)
                else:
                    # Create new projection
                    projection = PlayerProjection(**proj)
                    session.add(projection)
                
                updated_count += 1
        
        logger.info(f"Updated {updated_count} projections")
        return updated_count
    
    def get_projections(self, week: int, season: str = "2024", model_version: str = "default") -> List[PlayerProjection]:
        """Get projections for a specific week."""
        with session_scope() as session:
            return session.query(PlayerProjection).filter_by(
                week=week,
                season=season,
                model_version=model_version
            ).all()
    
    # Transaction operations
    def create_transactions(self, transactions_data: List[Dict[str, Any]], league_id: str) -> int:
        """Create transaction records."""
        created_count = 0
        
        with session_scope() as session:
            for trans in transactions_data:
                # Check if transaction already exists
                existing = session.query(Transaction).filter_by(
                    transaction_id=trans.get('transaction_id')
                ).first()
                
                if not existing:
                    transaction = Transaction(
                        transaction_id=trans.get('transaction_id'),
                        league_id=league_id,
                        type=trans.get('type'),
                        status=trans.get('status'),
                        week=trans.get('leg'),
                        created=trans.get('created'),
                        roster_ids=trans.get('roster_ids'),
                        adds=trans.get('adds'),
                        drops=trans.get('drops'),
                        draft_picks=trans.get('draft_picks'),
                        waiver_budget=trans.get('waiver_budget'),
                        settings=trans.get('settings'),
                        metadata=trans.get('metadata')
                    )
                    session.add(transaction)
                    created_count += 1
        
        logger.info(f"Created {created_count} transactions")
        return created_count
    
    # Trending players
    def update_trending_players(self, trending_data: List[Dict[str, Any]], trend_type: str) -> int:
        """Update trending players data."""
        today = date.today()
        updated_count = 0
        
        with session_scope() as session:
            # Delete existing trends for today
            session.query(TrendingPlayer).filter_by(
                trend_type=trend_type,
                date=today
            ).delete()
            
            # Insert new trends
            for player_data in trending_data:
                trending = TrendingPlayer(
                    player_id=player_data.get('player_id'),
                    trend_type=trend_type,
                    count=player_data.get('count', 1),
                    date=today
                )
                session.add(trending)
                updated_count += 1
        
        logger.info(f"Updated {updated_count} trending {trend_type} players")
        return updated_count
    
    # Matchups
    def create_matchups(self, matchups_data: List[Dict[str, Any]], league_id: str, week: int, season: str = "2024") -> int:
        """Create matchup records."""
        created_count = 0
        
        with session_scope() as session:
            for matchup in matchups_data:
                existing = session.query(Matchup).filter_by(
                    league_id=league_id,
                    week=week,
                    roster_id=matchup.get('roster_id')
                ).first()
                
                if not existing:
                    matchup_obj = Matchup(
                        league_id=league_id,
                        week=week,
                        season=season,
                        matchup_id=matchup.get('matchup_id'),
                        roster_id=matchup.get('roster_id'),
                        points=Decimal(str(matchup.get('points', 0))),
                        starters=matchup.get('starters'),
                        bench=matchup.get('players_bench')
                    )
                    session.add(matchup_obj)
                    created_count += 1
        
        logger.info(f"Created {created_count} matchups for week {week}")
        return created_count
    
    # Analysis runs
    def save_analysis_run(self, analysis_data: Dict[str, Any]) -> AnalysisRun:
        """Save analysis run results."""
        with session_scope() as session:
            analysis_run = AnalysisRun(**analysis_data)
            session.add(analysis_run)
            session.flush()
            return analysis_run
    
    def get_latest_analysis(self, league_id: str, run_type: str) -> Optional[AnalysisRun]:
        """Get the latest analysis run of a specific type."""
        with session_scope() as session:
            return session.query(AnalysisRun).filter_by(
                league_id=league_id,
                run_type=run_type,
                status='completed'
            ).order_by(desc(AnalysisRun.created_at)).first()
    
    # Utility methods
    def get_available_players(self, league_id: str, position: str = None) -> List[Player]:
        """Get players not on any roster in the league."""
        with session_scope() as session:
            # Subquery for players on rosters in this league
            rostered_players = session.query(RosterPlayer.player_id).join(
                Roster, RosterPlayer.roster_id == Roster.roster_id
            ).filter(Roster.league_id == league_id).subquery()
            
            # Query for players not in the subquery
            query = session.query(Player).filter(
                ~Player.player_id.in_(rostered_players),
                Player.status == 'Active'
            )
            
            if position:
                query = query.filter(Player.position == position)
            
            return query.all()
    
    def get_league_summary(self, league_id: str) -> Dict[str, Any]:
        """Get summary statistics for a league."""
        with session_scope() as session:
            league = session.query(League).filter_by(league_id=league_id).first()
            if not league:
                return {}
            
            roster_count = session.query(Roster).filter_by(league_id=league_id).count()
            player_count = session.query(RosterPlayer).join(
                Roster, RosterPlayer.roster_id == Roster.roster_id
            ).filter(Roster.league_id == league_id).count()
            
            transaction_count = session.query(Transaction).filter_by(league_id=league_id).count()
            
            return {
                'league_name': league.name,
                'total_rosters': roster_count,
                'total_players_rostered': player_count,
                'total_transactions': transaction_count,
                'last_updated': league.updated_at
            }