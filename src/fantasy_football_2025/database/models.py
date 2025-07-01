"""Database models for fantasy football data."""

from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Date, Boolean, 
    Float, JSON, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.dialects.mysql import DECIMAL, BIGINT, MEDIUMTEXT

Base = declarative_base()


class League(Base):
    """Fantasy league information."""
    __tablename__ = 'leagues'
    
    league_id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    season = Column(String(4), nullable=False, default='2024')
    total_rosters = Column(Integer, nullable=False)
    scoring_settings = Column(JSON)
    roster_positions = Column(JSON)
    league_type = Column(String(50))  # redraft, dynasty, etc.
    playoff_week_start = Column(Integer)
    status = Column(String(50))  # pre_draft, drafting, in_season, complete
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    rosters = relationship("Roster", back_populates="league", cascade="all, delete-orphan")
    users = relationship("User", back_populates="league", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="league", cascade="all, delete-orphan")
    matchups = relationship("Matchup", back_populates="league", cascade="all, delete-orphan")


class User(Base):
    """League users/managers."""
    __tablename__ = 'users'
    
    user_id = Column(String(50), primary_key=True)
    league_id = Column(String(50), ForeignKey('leagues.league_id'), nullable=False)
    username = Column(String(100))
    display_name = Column(String(100))
    team_name = Column(String(100))
    avatar = Column(String(255))
    is_owner = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    league = relationship("League", back_populates="users")
    roster = relationship("Roster", back_populates="user", uselist=False)
    
    __table_args__ = (
        Index('idx_users_league', 'league_id'),
    )


class Player(Base):
    """NFL players master table."""
    __tablename__ = 'players'
    
    player_id = Column(String(50), primary_key=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    full_name = Column(String(200))
    position = Column(String(10), nullable=False)
    team = Column(String(10))
    age = Column(Integer)
    height = Column(String(10))
    weight = Column(Integer)
    years_exp = Column(Integer)
    college = Column(String(100))
    status = Column(String(50))  # Active, Inactive, IR, etc.
    injury_status = Column(String(50))
    fantasy_positions = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    roster_players = relationship("RosterPlayer", back_populates="player")
    stats = relationship("PlayerStats", back_populates="player", cascade="all, delete-orphan")
    projections = relationship("PlayerProjection", back_populates="player", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_players_position', 'position'),
        Index('idx_players_team', 'team'),
        Index('idx_players_status', 'status'),
    )


class Roster(Base):
    """League rosters."""
    __tablename__ = 'rosters'
    
    roster_id = Column(Integer, primary_key=True)
    league_id = Column(String(50), ForeignKey('leagues.league_id'), nullable=False)
    user_id = Column(String(50), ForeignKey('users.user_id'), nullable=False)
    owner_id = Column(String(50))  # Sleeper owner ID
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    ties = Column(Integer, default=0)
    points_for = Column(DECIMAL(10, 2), default=0)
    points_against = Column(DECIMAL(10, 2), default=0)
    waiver_position = Column(Integer)
    waiver_budget_used = Column(Integer, default=0)
    settings = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    league = relationship("League", back_populates="rosters")
    user = relationship("User", back_populates="roster")
    players = relationship("RosterPlayer", back_populates="roster", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('league_id', 'user_id'),
        Index('idx_rosters_league', 'league_id'),
    )


class RosterPlayer(Base):
    """Players on rosters (many-to-many)."""
    __tablename__ = 'roster_players'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    roster_id = Column(Integer, ForeignKey('rosters.roster_id'), nullable=False)
    player_id = Column(String(50), ForeignKey('players.player_id'), nullable=False)
    added_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    roster = relationship("Roster", back_populates="players")
    player = relationship("Player", back_populates="roster_players")
    
    __table_args__ = (
        UniqueConstraint('roster_id', 'player_id'),
        Index('idx_roster_players_roster', 'roster_id'),
        Index('idx_roster_players_player', 'player_id'),
    )


class PlayerStats(Base):
    """Weekly player statistics."""
    __tablename__ = 'player_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String(50), ForeignKey('players.player_id'), nullable=False)
    season = Column(String(4), nullable=False)
    week = Column(Integer)  # NULL for season totals
    game_date = Column(Date)
    opponent = Column(String(10))
    is_home = Column(Boolean)
    
    # Passing stats
    pass_att = Column(Integer, default=0)
    pass_comp = Column(Integer, default=0)
    pass_yds = Column(Integer, default=0)
    pass_td = Column(Integer, default=0)
    pass_int = Column(Integer, default=0)
    pass_2pt = Column(Integer, default=0)
    
    # Rushing stats
    rush_att = Column(Integer, default=0)
    rush_yds = Column(Integer, default=0)
    rush_td = Column(Integer, default=0)
    rush_2pt = Column(Integer, default=0)
    
    # Receiving stats
    rec = Column(Integer, default=0)
    rec_tgt = Column(Integer, default=0)
    rec_yds = Column(Integer, default=0)
    rec_td = Column(Integer, default=0)
    rec_2pt = Column(Integer, default=0)
    
    # Kicking stats
    fgm = Column(Integer, default=0)
    fga = Column(Integer, default=0)
    fgm_0_19 = Column(Integer, default=0)
    fgm_20_29 = Column(Integer, default=0)
    fgm_30_39 = Column(Integer, default=0)
    fgm_40_49 = Column(Integer, default=0)
    fgm_50p = Column(Integer, default=0)
    xpm = Column(Integer, default=0)
    xpa = Column(Integer, default=0)
    
    # Defense stats
    def_st_td = Column(Integer, default=0)
    def_st_ff = Column(Integer, default=0)
    def_st_fum_rec = Column(Integer, default=0)
    def_st_int = Column(Integer, default=0)
    def_st_safety = Column(Integer, default=0)
    def_st_sack = Column(Integer, default=0)
    def_st_blk_kick = Column(Integer, default=0)
    pts_allow = Column(Integer, default=0)
    
    # Fantasy points
    fantasy_points = Column(DECIMAL(10, 2))
    fantasy_points_ppr = Column(DECIMAL(10, 2))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    player = relationship("Player", back_populates="stats")
    
    __table_args__ = (
        UniqueConstraint('player_id', 'season', 'week'),
        Index('idx_player_stats_player_season', 'player_id', 'season'),
        Index('idx_player_stats_week', 'week'),
    )


class PlayerProjection(Base):
    """Player projections for upcoming weeks."""
    __tablename__ = 'player_projections'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String(50), ForeignKey('players.player_id'), nullable=False)
    season = Column(String(4), nullable=False)
    week = Column(Integer, nullable=False)
    projection_date = Column(DateTime, default=datetime.utcnow)
    
    # Projected stats (similar structure to PlayerStats)
    proj_pass_att = Column(DECIMAL(8, 2), default=0)
    proj_pass_comp = Column(DECIMAL(8, 2), default=0)
    proj_pass_yds = Column(DECIMAL(8, 2), default=0)
    proj_pass_td = Column(DECIMAL(8, 2), default=0)
    proj_pass_int = Column(DECIMAL(8, 2), default=0)
    
    proj_rush_att = Column(DECIMAL(8, 2), default=0)
    proj_rush_yds = Column(DECIMAL(8, 2), default=0)
    proj_rush_td = Column(DECIMAL(8, 2), default=0)
    
    proj_rec = Column(DECIMAL(8, 2), default=0)
    proj_rec_tgt = Column(DECIMAL(8, 2), default=0)
    proj_rec_yds = Column(DECIMAL(8, 2), default=0)
    proj_rec_td = Column(DECIMAL(8, 2), default=0)
    
    # Projected fantasy points
    proj_fantasy_points = Column(DECIMAL(8, 2))
    proj_fantasy_points_ppr = Column(DECIMAL(8, 2))
    proj_floor = Column(DECIMAL(8, 2))
    proj_ceiling = Column(DECIMAL(8, 2))
    
    # Model metadata
    model_version = Column(String(50))
    confidence_score = Column(DECIMAL(4, 3))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    player = relationship("Player", back_populates="projections")
    
    __table_args__ = (
        UniqueConstraint('player_id', 'season', 'week', 'model_version'),
        Index('idx_projections_player_week', 'player_id', 'week'),
        Index('idx_projections_week', 'week'),
    )


class Matchup(Base):
    """Weekly matchups."""
    __tablename__ = 'matchups'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(String(50), ForeignKey('leagues.league_id'), nullable=False)
    week = Column(Integer, nullable=False)
    season = Column(String(4), nullable=False)
    matchup_id = Column(Integer)  # Sleeper matchup ID
    roster_id = Column(Integer, ForeignKey('rosters.roster_id'), nullable=False)
    points = Column(DECIMAL(10, 2))
    starters = Column(JSON)  # List of player IDs
    bench = Column(JSON)     # List of player IDs
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    league = relationship("League", back_populates="matchups")
    
    __table_args__ = (
        UniqueConstraint('league_id', 'week', 'roster_id'),
        Index('idx_matchups_league_week', 'league_id', 'week'),
    )


class Transaction(Base):
    """League transactions (trades, waivers, free agents)."""
    __tablename__ = 'transactions'
    
    transaction_id = Column(String(50), primary_key=True)
    league_id = Column(String(50), ForeignKey('leagues.league_id'), nullable=False)
    type = Column(String(50), nullable=False)  # trade, waiver, free_agent
    status = Column(String(50))  # complete, pending, failed
    week = Column(Integer)
    created = Column(BIGINT)  # Unix timestamp
    processed_date = Column(DateTime)
    
    # Transaction details
    roster_ids = Column(JSON)  # List of involved roster IDs
    adds = Column(JSON)        # Dict of player_id: roster_id
    drops = Column(JSON)       # Dict of player_id: roster_id
    draft_picks = Column(JSON) # Draft pick trades
    
    # Waiver specific
    waiver_budget = Column(JSON)  # Waiver budget used
    settings = Column(JSON)
    
    # Additional metadata
    metadata = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    league = relationship("League", back_populates="transactions")
    
    __table_args__ = (
        Index('idx_transactions_league', 'league_id'),
        Index('idx_transactions_type', 'type'),
        Index('idx_transactions_week', 'week'),
    )


class TrendingPlayer(Base):
    """Trending players (adds/drops)."""
    __tablename__ = 'trending_players'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String(50), ForeignKey('players.player_id'), nullable=False)
    trend_type = Column(String(10), nullable=False)  # add, drop
    count = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('player_id', 'trend_type', 'date'),
        Index('idx_trending_date', 'date'),
        Index('idx_trending_type', 'trend_type'),
    )


class WaiverClaim(Base):
    """Waiver wire claims tracking."""
    __tablename__ = 'waiver_claims'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(String(50), ForeignKey('leagues.league_id'), nullable=False)
    roster_id = Column(Integer, ForeignKey('rosters.roster_id'), nullable=False)
    player_id = Column(String(50), ForeignKey('players.player_id'), nullable=False)
    week = Column(Integer, nullable=False)
    priority = Column(Integer)
    budget_used = Column(Integer)
    status = Column(String(20))  # pending, successful, failed
    claim_date = Column(DateTime, default=datetime.utcnow)
    process_date = Column(DateTime)
    
    __table_args__ = (
        Index('idx_waiver_claims_league_week', 'league_id', 'week'),
        Index('idx_waiver_claims_roster', 'roster_id'),
    )


class TeamSchedule(Base):
    """NFL team schedules and game information."""
    __tablename__ = 'team_schedule'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    season = Column(String(4), nullable=False)
    week = Column(Integer, nullable=False)
    game_date = Column(DateTime)
    home_team = Column(String(10), nullable=False)
    away_team = Column(String(10), nullable=False)
    home_score = Column(Integer)
    away_score = Column(Integer)
    game_status = Column(String(20))  # scheduled, in_progress, final
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('season', 'week', 'home_team', 'away_team'),
        Index('idx_schedule_week', 'week'),
        Index('idx_schedule_team', 'home_team', 'away_team'),
    )


class AnalysisRun(Base):
    """Track analysis runs and their results."""
    __tablename__ = 'analysis_runs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(String(50), ForeignKey('leagues.league_id'), nullable=False)
    run_type = Column(String(50), nullable=False)  # lineup_optimization, trade_analysis, waiver_analysis
    week = Column(Integer)
    parameters = Column(JSON)
    results = Column(MEDIUMTEXT)  # JSON results
    execution_time = Column(DECIMAL(8, 3))  # seconds
    status = Column(String(20))  # running, completed, failed
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    __table_args__ = (
        Index('idx_analysis_runs_league_type', 'league_id', 'run_type'),
        Index('idx_analysis_runs_created', 'created_at'),
    )