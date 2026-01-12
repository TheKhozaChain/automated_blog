"""Command-line interface for daily_ai_timeline.

Usage:
    python -m daily_ai_timeline run --mode daily
    python -m daily_ai_timeline run --mode realtime
    python -m daily_ai_timeline run --niche ai_jobs_au --mode daily
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from .config import Config, NicheConfig
from .dedupe import process_items
from .generator import run_generation_pipeline
from .ingest import fetch_all_sources
from .utils import get_current_time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_command(args: argparse.Namespace) -> int:
    """Execute the run command to generate AI timeline posts.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Load configuration
    config = Config.from_env()

    # Load niche configuration
    niche_name = getattr(args, "niche", None) or "ai_news"
    try:
        niche = NicheConfig.load(niche_name)
        logger.info(f"Loaded niche: {niche.name}")
    except FileNotFoundError as e:
        logger.error(str(e))
        return 1

    # Override config with CLI arguments (CLI takes precedence over niche)
    if args.top:
        config.top_n_items = args.top
    if args.output:
        config.output_dir = Path(args.output)
    else:
        # Use niche's default output directory
        config.output_dir = Path(niche.output_dir)

    # Validate configuration
    errors = config.validate()
    if errors:
        for error in errors:
            logger.error(error)
        return 1

    # Get current time in configured timezone
    current_time = get_current_time(config.timezone)
    logger.info(f"Running in {args.mode} mode at {current_time}")

    try:
        # Step 1: Fetch from all sources
        logger.info("Step 1/3: Fetching sources...")
        items = fetch_all_sources(
            config=config,
            mode=args.mode,
            show_progress=not args.quiet,
            fetch_content=args.fetch_content,
            niche=niche,
        )

        if not items:
            logger.warning("No items fetched from sources. Exiting.")
            return 1

        # Step 2: Deduplicate and score
        logger.info("Step 2/3: Processing and ranking items...")
        # Get lookback hours based on mode for proper recency scoring
        if args.mode == "weekly":
            lookback_hours = config.lookback_hours_weekly
        elif args.mode == "realtime":
            lookback_hours = config.lookback_hours_realtime
        else:
            lookback_hours = config.lookback_hours_daily
        top_items = process_items(
            items,
            top_n=config.top_n_items,
            lookback_hours=lookback_hours,
            niche=niche,
        )

        if not top_items:
            logger.warning("No items after processing. Exiting.")
            return 1

        logger.info(f"Selected {len(top_items)} items for post generation:")
        for i, item in enumerate(top_items, 1):
            logger.info(f"  {i}. [{item.source}] {item.title[:60]}... (score: {item.score:.1f})")

        # Step 3: Generate article
        logger.info("Step 3/3: Generating article...")
        result, saved_files = run_generation_pipeline(
            items=top_items,
            config=config,
            date=current_time,
            niche=niche,
        )

        # Report success
        logger.info("Generation complete!")
        logger.info("Saved files:")
        for output_type, filepath in saved_files.items():
            logger.info(f"  - {output_type}: {filepath}")

        # Print preview if not quiet
        if not args.quiet:
            print("\n" + "=" * 60)
            print("ARTICLE PREVIEW (first 800 chars)")
            print("=" * 60)
            print(result.article[:800] + "..." if len(result.article) > 800 else result.article)
            print("\n" + "=" * 60)
            print(f"Full article saved to: {saved_files.get('article', 'out/today.md')}")

        return 0

    except Exception as e:
        logger.exception(f"Error during generation: {e}")
        return 1


def serve_command(args: argparse.Namespace) -> int:
    """Serve the blog on localhost.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code
    """
    from .server import serve_blog

    serve_blog(port=args.port, open_browser=not args.no_browser, output_dir=args.dir)
    return 0


def sources_command(args: argparse.Namespace) -> int:
    """List configured sources for a niche.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code
    """
    niche_name = getattr(args, "niche", None) or "ai_news"
    try:
        niche = NicheConfig.load(niche_name)
    except FileNotFoundError as e:
        print(str(e))
        return 1

    print(f"Sources for niche: {niche.name}")
    print("=" * 50)

    print("\nRSS Feeds:")
    for name, url in niche.rss_feeds.items():
        print(f"  - {name}")
        print(f"    {url}")

    if niche.arxiv_categories:
        print(f"\narXiv Categories: {', '.join(niche.arxiv_categories)}")

    if niche.hn_keywords:
        print(f"\nHacker News Keywords: {', '.join(niche.hn_keywords)}")

    if niche.reddit_subreddits:
        print(f"\nReddit Subreddits: {', '.join(niche.reddit_subreddits)}")

    print(f"\nScoring Keywords: {', '.join(niche.scoring_keywords[:10])}...")

    return 0


def niches_command(args: argparse.Namespace) -> int:
    """List available niche configurations.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code
    """
    available = NicheConfig.list_available()

    if not available:
        print("No niches found. Create YAML files in the niches/ directory.")
        return 1

    print("Available Niches")
    print("=" * 50)

    for niche_name in sorted(available):
        try:
            niche = NicheConfig.load(niche_name)
            print(f"\n  {niche_name}")
            print(f"    Name: {niche.name}")
            print(f"    Description: {niche.description}")
            print(f"    Output: {niche.output_dir}")
        except Exception as e:
            print(f"\n  {niche_name} (error loading: {e})")

    print("\n" + "=" * 50)
    print("Usage: python -m daily_ai_timeline run --niche <name>")

    return 0


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="daily_ai_timeline",
        description="Generate daily AI timeline posts from aggregated news sources",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Fetch sources and generate posts",
    )
    run_parser.add_argument(
        "--niche",
        "-n",
        type=str,
        default="ai_news",
        help="Niche configuration to use (default: ai_news)",
    )
    run_parser.add_argument(
        "--mode",
        choices=["daily", "realtime", "weekly"],
        default="daily",
        help="Run mode: 'daily' (24h), 'realtime' (1h), or 'weekly' (7 days)",
    )
    run_parser.add_argument(
        "--top",
        type=int,
        help="Number of top items to include (default: 10)",
    )
    run_parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output directory (default: from niche config)",
    )
    run_parser.add_argument(
        "--fetch-content",
        action="store_true",
        help="Fetch full article content (slower but more context)",
    )
    run_parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress bars and previews",
    )
    run_parser.set_defaults(func=run_command)

    # Sources command
    sources_parser = subparsers.add_parser(
        "sources",
        help="List configured news sources for a niche",
    )
    sources_parser.add_argument(
        "--niche",
        "-n",
        type=str,
        default="ai_news",
        help="Niche to show sources for (default: ai_news)",
    )
    sources_parser.set_defaults(func=sources_command)

    # Niches command
    niches_parser = subparsers.add_parser(
        "niches",
        help="List available niche configurations",
    )
    niches_parser.set_defaults(func=niches_command)

    # Serve command
    serve_parser = subparsers.add_parser(
        "serve",
        help="Preview the blog on localhost",
    )
    serve_parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8000,
        help="Port to serve on (default: 8000)",
    )
    serve_parser.add_argument(
        "--dir",
        "-d",
        type=str,
        default="out",
        help="Output directory to serve (default: out)",
    )
    serve_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically",
    )
    serve_parser.set_defaults(func=serve_command)

    return parser


def main() -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
