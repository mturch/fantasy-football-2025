"""Main entry point for Fantasy Football 2025 Analytics."""

import argparse
import os
import sys
from datetime import datetime
from typing import Optional

from .lineup_optimizer import LineupOptimizer
from .sleeper_client import SleeperClient, SleeperConfig
from .trade_analyzer import TradeAnalyzer
from .waiver_analyzer import WaiverAnalyzer


def main():
    """Main CLI interface for fantasy football analytics."""
    parser = argparse.ArgumentParser(
        description="Fantasy Football 2025 Analytics - Data-driven fantasy football tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Pull all league data
  python -m src.main --league-id 123456 --user-id abc123 --pull-data

  # Optimize lineup
  python -m src.main --league-id 123456 --user-id abc123 --optimize-lineup

  # Find trade opportunities
  python -m src.main --league-id 123456 --user-id abc123 --analyze-trades

  # Get waiver wire recommendations
  python -m src.main --league-id 123456 --user-id abc123 --waiver-wire

  # Run full analysis
  python -m src.main --league-id 123456 --user-id abc123 --full-analysis
        """,
    )

    # Required arguments
    parser.add_argument("--league-id", required=True, help="Sleeper league ID")
    parser.add_argument("--user-id", required=True, help="Your Sleeper user ID")

    # Optional arguments
    parser.add_argument("--week", type=int, help="Specific week to analyze")
    parser.add_argument(
        "--output-dir", default="data/processed", help="Output directory for results"
    )

    # Action arguments
    parser.add_argument(
        "--pull-data", action="store_true", help="Pull all league data from Sleeper"
    )
    parser.add_argument(
        "--optimize-lineup", action="store_true", help="Generate optimal lineups"
    )
    parser.add_argument(
        "--analyze-trades", action="store_true", help="Find trade opportunities"
    )
    parser.add_argument(
        "--waiver-wire", action="store_true", help="Get waiver wire recommendations"
    )
    parser.add_argument(
        "--full-analysis", action="store_true", help="Run complete analysis"
    )

    # Lineup optimization options
    parser.add_argument(
        "--num-lineups", type=int, default=3, help="Number of lineups to generate"
    )
    parser.add_argument(
        "--objective",
        choices=["points", "ceiling", "floor"],
        default="points",
        help="Optimization objective",
    )

    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Setup Sleeper client
    print(f"🏈 Fantasy Football 2025 Analytics")
    print(f"League ID: {args.league_id}")
    print(f"User ID: {args.user_id}")
    print(f"Week: {args.week or 'Current'}")
    print("-" * 50)

    config = SleeperConfig(
        league_id=args.league_id, user_id=args.user_id, season="2024"
    )

    sleeper_client = SleeperClient(config)

    # Validate league connection
    try:
        league_info = sleeper_client.get_league_info()
        print(f"✅ Connected to league: {league_info.get('name', 'Unknown')}")
        print(
            f"   League type: {'PPR' if sleeper_client.is_ppr_league() else 'Standard'}"
        )
        print(f"   Total teams: {league_info.get('total_rosters', 0)}")
        print(f"   Flex positions: {len(sleeper_client.get_flex_positions())}")
    except Exception as e:
        print(f"❌ Error connecting to league: {e}")
        sys.exit(1)

    # Execute requested actions
    if args.pull_data or args.full_analysis:
        pull_league_data(sleeper_client, args.output_dir)

    if args.optimize_lineup or args.full_analysis:
        optimize_lineup(sleeper_client, args)

    if args.analyze_trades or args.full_analysis:
        analyze_trades(sleeper_client, args)

    if args.waiver_wire or args.full_analysis:
        analyze_waiver_wire(sleeper_client, args)

    if not any(
        [
            args.pull_data,
            args.optimize_lineup,
            args.analyze_trades,
            args.waiver_wire,
            args.full_analysis,
        ]
    ):
        print("No action specified. Use --help to see available options.")
        show_quick_stats(sleeper_client)


def pull_league_data(sleeper_client: SleeperClient, output_dir: str):
    """Pull and export all league data."""
    print("\n📥 Pulling league data...")

    try:
        data_dir = os.path.join(output_dir, "raw")
        sleeper_client.export_league_data(data_dir)
        print("✅ League data exported successfully")
    except Exception as e:
        print(f"❌ Error pulling data: {e}")


def optimize_lineup(sleeper_client: SleeperClient, args):
    """Generate optimal lineup recommendations."""
    print(f"\n🔄 Optimizing lineup (generating {args.num_lineups} lineups)...")

    try:
        optimizer = LineupOptimizer(sleeper_client)

        print("   Loading player data...")
        optimizer.load_player_data()

        print(f"   Generating projections for week {args.week or 'current'}...")
        optimizer.generate_projections(args.week)

        print(f"   Optimizing lineups (objective: {args.objective})...")
        lineups = optimizer.optimize_lineup(
            num_lineups=args.num_lineups, objective=args.objective
        )

        if lineups:
            print(f"\n✅ Generated {len(lineups)} optimal lineups:")

            for i, lineup in enumerate(lineups, 1):
                print(
                    f"\n📋 Lineup {i} - Projected: {lineup['total_projected_points']:.1f} pts"
                )
                print(
                    f"   Floor: {lineup['total_floor']:.1f} | Ceiling: {lineup['total_ceiling']:.1f}"
                )

                # Group players by position
                positions = {}
                for player in lineup["players"]:
                    pos = player["position"]
                    if pos not in positions:
                        positions[pos] = []
                    positions[pos].append(player)

                # Display by position
                for pos in ["QB", "RB", "WR", "TE", "K", "DEF"]:
                    if pos in positions:
                        for player in positions[pos]:
                            print(
                                f"   {pos}: {player['name']} ({player['projected_points']:.1f} pts)"
                            )

            # Export lineups
            output_file = os.path.join(args.output_dir, "optimized_lineups.json")
            optimizer.export_lineups(lineups, output_file)

            # Analyze current roster if possible
            current_roster = sleeper_client.get_my_roster()
            if current_roster:
                print("\n📊 Current roster analysis:")
                analysis = optimizer.analyze_current_lineup(current_roster)

                current_total = analysis.get("current_total_points", 0)
                improvement = analysis.get("improvement_potential", 0)

                print(f"   Current projected total: {current_total:.1f} pts")
                if improvement > 0:
                    print(f"   Potential improvement: +{improvement:.1f} pts")

                    recommendations = analysis.get("recommendations", [])
                    if recommendations:
                        print("   Recommendations:")
                        for rec in recommendations[:3]:
                            action = rec["action"].replace("_", " ").title()
                            player_name = rec["player"]["name"]
                            print(f"   • {action}: {player_name}")
                else:
                    print("   ✅ Your lineup is already optimized!")
        else:
            print("❌ No optimal lineups found. Check constraints and projections.")

    except Exception as e:
        print(f"❌ Error optimizing lineup: {e}")


def analyze_trades(sleeper_client: SleeperClient, args):
    """Find and analyze trade opportunities."""
    print("\n🔄 Analyzing trade opportunities...")

    try:
        optimizer = LineupOptimizer(sleeper_client)
        optimizer.load_player_data()
        optimizer.generate_projections(args.week)

        trade_analyzer = TradeAnalyzer(sleeper_client, optimizer)

        print("   Calculating player values...")
        trade_analyzer.calculate_player_values(args.week)

        print("   Finding trade opportunities...")
        opportunities = trade_analyzer.find_trade_opportunities()

        if opportunities:
            print(f"\n✅ Found {len(opportunities)} potential trades:")

            for i, trade in enumerate(opportunities[:5], 1):
                # Get player names
                giving_names = []
                receiving_names = []

                for pid in trade.giving_players:
                    if pid in optimizer.projections:
                        giving_names.append(optimizer.projections[pid].name)

                for pid in trade.receiving_players:
                    if pid in optimizer.projections:
                        receiving_names.append(optimizer.projections[pid].name)

                print(f"\n💼 Trade {i} (Value: +{trade.trade_value:.1f})")
                print(f"   Give: {', '.join(giving_names)}")
                print(f"   Get:  {', '.join(receiving_names)}")
                print(f"   Confidence: {trade.confidence_score:.2f}")
        else:
            print("❌ No favorable trade opportunities found at this time.")

        # Track recent trade history
        print("\n📈 Analyzing recent trade market...")
        history = trade_analyzer.track_trade_history()
        if history:
            print(f"   Found {len(history)} recent trades in your league")

    except Exception as e:
        print(f"❌ Error analyzing trades: {e}")


def analyze_waiver_wire(sleeper_client: SleeperClient, args):
    """Analyze waiver wire and generate pickup recommendations."""
    print("\n🔄 Analyzing waiver wire...")

    try:
        optimizer = LineupOptimizer(sleeper_client)
        optimizer.load_player_data()
        optimizer.generate_projections(args.week)

        waiver_analyzer = WaiverAnalyzer(sleeper_client, optimizer)
        analysis = waiver_analyzer.analyze_waiver_wire(args.week)

        # Display recommendations
        if analysis.recommendations:
            print(f"\n✅ Top waiver wire recommendations:")

            for i, rec in enumerate(analysis.recommendations[:5], 1):
                print(f"\n📈 {i}. {rec.player_name} ({rec.position} - {rec.team})")
                print(
                    f"   Priority: {rec.pickup_priority} | Projected: {rec.projected_points:.1f} pts"
                )
                print(f"   Reason: {rec.pickup_reason}")
                print(
                    f"   Matchup: {rec.matchup_rating:.2f} | Confidence: {rec.confidence_score:.2f}"
                )
                print(f"   Trend: {rec.ownership_trend}")

                if rec.drop_candidates:
                    drop_names = [d["name"] for d in rec.drop_candidates[:2]]
                    print(f"   💡 Consider dropping: {', '.join(drop_names)}")

        # Emergency pickups
        if analysis.emergency_pickups:
            print(f"\n🚨 Emergency pickups (injury replacements):")
            for rec in analysis.emergency_pickups[:3]:
                print(f"   • {rec.player_name} ({rec.position}) - {rec.pickup_reason}")

        # Streaming options
        if analysis.streaming_options.get("DEF"):
            print(f"\n🛡️  Defense streaming options:")
            for rec in analysis.streaming_options["DEF"][:3]:
                print(f"   • {rec.player_name} (Matchup: {rec.matchup_rating:.2f})")

        if analysis.streaming_options.get("K"):
            print(f"\n🦵 Kicker streaming options:")
            for rec in analysis.streaming_options["K"][:3]:
                print(f"   • {rec.player_name} (Projected: {rec.projected_points:.1f})")

        # Stash candidates
        if analysis.stash_candidates:
            print(f"\n💎 Stash candidates (high upside):")
            for rec in analysis.stash_candidates[:3]:
                print(f"   • {rec.player_name} ({rec.position}) - {rec.pickup_reason}")

        # Drop candidates
        if analysis.drop_candidates:
            print(f"\n⬇️  Consider dropping:")
            for player in analysis.drop_candidates[:3]:
                print(
                    f"   • {player['name']} ({player['position']}) - {player['drop_reason']}"
                )

        # Export analysis
        output_file = os.path.join(args.output_dir, "waiver_analysis.json")
        waiver_analyzer.export_waiver_analysis(analysis, output_file)

    except Exception as e:
        print(f"❌ Error analyzing waiver wire: {e}")


def show_quick_stats(sleeper_client: SleeperClient):
    """Show quick league and roster stats."""
    print("\n📊 Quick Stats:")

    try:
        # League info
        league_info = sleeper_client.get_league_info()
        settings = sleeper_client.get_league_settings()

        print(f"   League: {league_info.get('name', 'Unknown')}")
        print(f"   Scoring: {'PPR' if sleeper_client.is_ppr_league() else 'Standard'}")
        print(f"   Teams: {league_info.get('total_rosters', 0)}")

        # My roster
        my_roster = sleeper_client.get_my_roster()
        if my_roster:
            players = my_roster.get("players", [])
            print(f"   Your roster: {len(players)} players")

            wins = my_roster.get("settings", {}).get("wins", 0)
            losses = my_roster.get("settings", {}).get("losses", 0)
            print(f"   Record: {wins}-{losses}")

        # Recent transactions
        transactions = sleeper_client.get_transactions()
        recent_adds = [
            t
            for t in transactions
            if t.get("type") == "waiver"
            and t.get("settings", {}).get("waiver_budget_used", 0) > 0
        ]

        if recent_adds:
            print(f"   Recent waiver activity: {len(recent_adds)} claims")

    except Exception as e:
        print(f"   Error loading stats: {e}")

    print("\nUse --help to see all available commands.")


if __name__ == "__main__":
    main()
