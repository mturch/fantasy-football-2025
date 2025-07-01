"""Command-line interface for Fantasy Football 2025 Analytics."""

import click

from .main import main as main_func


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Fantasy Football 2025 Analytics - Data-driven fantasy football tools"""
    pass


@cli.command()
@click.option("--league-id", required=True, help="Sleeper league ID")
@click.option("--user-id", required=True, help="Your Sleeper user ID")
@click.option("--week", type=int, help="Specific week to analyze")
@click.option(
    "--output-dir", default="data/processed", help="Output directory for results"
)
@click.option("--pull-data", is_flag=True, help="Pull all league data from Sleeper")
@click.option("--optimize-lineup", is_flag=True, help="Generate optimal lineups")
@click.option("--analyze-trades", is_flag=True, help="Find trade opportunities")
@click.option("--waiver-wire", is_flag=True, help="Get waiver wire recommendations")
@click.option("--full-analysis", is_flag=True, help="Run complete analysis")
@click.option(
    "--num-lineups", type=int, default=3, help="Number of lineups to generate"
)
@click.option(
    "--objective",
    type=click.Choice(["points", "ceiling", "floor"]),
    default="points",
    help="Optimization objective",
)
def analyze(
    league_id,
    user_id,
    week,
    output_dir,
    pull_data,
    optimize_lineup,
    analyze_trades,
    waiver_wire,
    full_analysis,
    num_lineups,
    objective,
):
    """Run fantasy football analysis"""
    import sys

    # Build arguments list for main function
    args = [
        "--league-id",
        league_id,
        "--user-id",
        user_id,
        "--output-dir",
        output_dir,
        "--num-lineups",
        str(num_lineups),
        "--objective",
        objective,
    ]

    if week:
        args.extend(["--week", str(week)])
    if pull_data:
        args.append("--pull-data")
    if optimize_lineup:
        args.append("--optimize-lineup")
    if analyze_trades:
        args.append("--analyze-trades")
    if waiver_wire:
        args.append("--waiver-wire")
    if full_analysis:
        args.append("--full-analysis")

    # Save original sys.argv and replace
    original_argv = sys.argv
    sys.argv = ["ff-analyze"] + args

    try:
        main_func()
    finally:
        # Restore original sys.argv
        sys.argv = original_argv


@cli.command()
@click.option("--league-id", required=True, help="Sleeper league ID")
@click.option("--user-id", required=True, help="Your Sleeper user ID")
@click.option("--week", type=int, help="Week to optimize for")
@click.option(
    "--num-lineups", type=int, default=3, help="Number of lineups to generate"
)
@click.option(
    "--objective",
    type=click.Choice(["points", "ceiling", "floor"]),
    default="points",
    help="Optimization objective",
)
@click.option(
    "--output", default="data/processed/optimized_lineups.json", help="Output file"
)
def optimize(league_id, user_id, week, num_lineups, objective, output):
    """Generate optimal lineups"""
    import sys

    from .lineup_optimizer import main as optimizer_main

    args = [
        "--league-id",
        league_id,
        "--user-id",
        user_id,
        "--num-lineups",
        str(num_lineups),
        "--objective",
        objective,
        "--output",
        output,
    ]

    if week:
        args.extend(["--week", str(week)])

    original_argv = sys.argv
    sys.argv = ["ff-optimize"] + args

    try:
        optimizer_main()
    finally:
        sys.argv = original_argv


@cli.command()
@click.option("--league-id", required=True, help="Sleeper league ID")
@click.option("--user-id", required=True, help="Your Sleeper user ID")
@click.option("--find-opportunities", is_flag=True, help="Find trade opportunities")
@click.option("--track-history", is_flag=True, help="Track recent trade history")
@click.option(
    "--output", default="data/processed/trade_analysis.json", help="Output file"
)
def trades(league_id, user_id, find_opportunities, track_history, output):
    """Analyze trade opportunities"""
    import sys

    from .trade_analyzer import main as trades_main

    args = ["--league-id", league_id, "--user-id", user_id, "--output", output]

    if find_opportunities:
        args.append("--find-opportunities")
    if track_history:
        args.append("--track-history")

    original_argv = sys.argv
    sys.argv = ["ff-trades"] + args

    try:
        trades_main()
    finally:
        sys.argv = original_argv


@cli.command()
@click.option("--league-id", required=True, help="Sleeper league ID")
@click.option("--user-id", required=True, help="Your Sleeper user ID")
@click.option("--week", type=int, help="Week to analyze for")
@click.option(
    "--output", default="data/processed/waiver_analysis.json", help="Output file"
)
def waiver(league_id, user_id, week, output):
    """Get waiver wire recommendations"""
    import sys

    from .waiver_analyzer import main as waiver_main

    args = ["--league-id", league_id, "--user-id", user_id, "--output", output]

    if week:
        args.extend(["--week", str(week)])

    original_argv = sys.argv
    sys.argv = ["ff-waiver"] + args

    try:
        waiver_main()
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    cli()
