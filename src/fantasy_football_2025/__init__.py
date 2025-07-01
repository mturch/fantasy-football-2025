"""Fantasy Football 2025 Analytics Package."""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Import main classes for easy access
from .sleeper_client import SleeperClient, SleeperConfig
from .lineup_optimizer import LineupOptimizer
from .trade_analyzer import TradeAnalyzer
from .waiver_analyzer import WaiverAnalyzer

__all__ = [
    "SleeperClient",
    "SleeperConfig", 
    "LineupOptimizer",
    "TradeAnalyzer",
    "WaiverAnalyzer",
]