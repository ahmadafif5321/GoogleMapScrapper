#!/usr/bin/env python3
"""
Google Maps Review Analytics - Main CLI
Full pipeline: Scrape → Analyze → Dashboard

Usage:
    python main.py scrape "coffee shop in Jakarta, indonesia" "restaurant in Jakarta, indonesia"
    python main.py analyze results_reviews.parquet
    python main.py dashboard
    python main.py full "coffee shop in Jakarta, indonesia" "restaurant in Jakarta, indonesia"
"""
import sys
import argparse
from pathlib import Path

from config import PROCESSED_DIR


def cmd_scrape(args):
    """Phase 1: Scrape reviews from Google Maps."""
    from scraper.run_scraper import scrape_and_get_reviews

    queries = args.queries
    if not queries:
        print("ERROR: At least one search query is required.")
        print('Example: python main.py scrape "coffee shop in Jakarta" "restaurant in Bandung"')
        sys.exit(1)

    output_name = args.output or "results"
    print(f"\n{'='*60}")
    print(f"  PHASE 1: Google Maps Scraping")
    print(f"  Queries: {queries}")
    print(f"{'='*60}\n")

    df = scrape_and_get_reviews(queries, output_name)

    if df is not None and not df.empty:
        print(f"\n✅ Scraping complete! {len(df)} reviews collected.")
        print(f"Data saved to: {PROCESSED_DIR / f'{output_name}_reviews.parquet'}")
    else:
        print("\n❌ Scraping failed or returned no results.")
        sys.exit(1)


def cmd_analyze(args):
    """Phase 2-4: Run analytics pipeline on scraped data."""
    from analytics.pipeline import run_pipeline_from_parquet

    parquet_file = args.file
    output_prefix = args.output or "analysis"
    method = args.sentiment_method or "transformer"

    if method not in ("transformer", "vader"):
        print(f"ERROR: Unknown sentiment method '{method}'. Use 'transformer' or 'vader'.")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  PHASE 2-4: Analytics Pipeline")
    print(f"  Input: {parquet_file}")
    print(f"  Sentiment Method: {method}")
    print(f"{'='*60}\n")

    try:
        results = run_pipeline_from_parquet(parquet_file, output_prefix, method)
        print(f"\n✅ Analysis complete!")
        print(f"Results saved to: {PROCESSED_DIR / f'{output_prefix}_results.json'}")
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Analysis error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def cmd_dashboard(args):
    """Launch the Streamlit dashboard."""
    import subprocess
    import os

    dashboard_path = Path(__file__).resolve().parent / "dashboard" / "app.py"

    if not dashboard_path.exists():
        print(f"ERROR: Dashboard file not found: {dashboard_path}")
        sys.exit(1)

    port = args.port or 8501

    print(f"\n{'='*60}")
    print(f"  Launching Streamlit Dashboard")
    print(f"  URL: http://localhost:{port}")
    print(f"{'='*60}\n")

    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(dashboard_path),
        "--server.port", str(port),
        "--browser.serverAddress", "localhost",
    ]

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


def cmd_full(args):
    """Run the complete pipeline: scrape + analyze."""
    from scraper.run_scraper import scrape_and_get_reviews
    from analytics.pipeline import AnalyticsPipeline

    queries = args.queries
    if not queries:
        print("ERROR: At least one search query is required.")
        sys.exit(1)

    output_name = args.output or "results"
    method = args.sentiment_method or "transformer"

    print(f"\n{'='*60}")
    print(f"  FULL PIPELINE: Scrape + Analyze")
    print(f"  Queries: {queries}")
    print(f"  Sentiment: {method}")
    print(f"{'='*60}\n")

    reviews_df = scrape_and_get_reviews(queries, output_name)

    if reviews_df is None or reviews_df.empty:
        print("\n❌ Scraping failed. Stopping.")
        sys.exit(1)

    print("\n✅ Scraping done. Running analytics...\n")
    pipeline = AnalyticsPipeline(reviews_df, output_prefix=output_name)
    pipeline.run(sentiment_method=method)

    print(f"\n✅ Full pipeline complete!")
    print(f"Launch dashboard with: python main.py dashboard")


def cmd_collect(args):
    """Run the continuous collector for long-running data collection."""
    from scraper.collector import run_collector, reset_collector, merge_reviews
    from pathlib import Path

    queries_file = Path(args.queries_file or "scraper/queries.txt")
    if not queries_file.exists():
        # Auto-generate queries if file doesn't exist
        print(f"[collect] Queries file not found: {queries_file}")
        print("[collect] Generating queries for max coverage...")
        from scraper.query_generator import generate_max_coverage, write_queries_file
        queries = generate_max_coverage()
        write_queries_file(queries, queries_file)

    if args.reset:
        reset_collector()

    batch_size = args.batch_size or 3
    delay = args.delay or 120
    max_batches = args.max_batches or 0

    print(f"\n{'='*60}")
    print(f"  CONTINUOUS COLLECTOR")
    print(f"  Queries file: {queries_file}")
    print(f"  Batch size: {batch_size}")
    print(f"  Delay: {delay}s between batches")
    print(f"  Max batches: {max_batches if max_batches > 0 else 'unlimited'}")
    print(f"  RAM needed: ~{batch_size * 500}MB (free: check 'free -h')")
    print(f"  Press Ctrl+C to stop safely (progress is saved)")
    print(f"{'='*60}\n")

    try:
        run_collector(
            queries_file=queries_file,
            batch_size=batch_size,
            delay_seconds=delay,
            max_batches=max_batches,
            resume=not args.reset,
        )
    except KeyboardInterrupt:
        print("\n[collect] Stopped by user. Progress saved. Resume with:")
        print(f"  python main.py collect -q {queries_file}")


def cmd_generate_queries(args):
    """Generate a comprehensive query list for maximum coverage."""
    from scraper.query_generator import generate_max_coverage, write_queries_file
    from pathlib import Path

    output = Path(args.output or "scraper/queries.txt")
    queries = generate_max_coverage()
    write_queries_file(queries, output)

    print(f"\n[queries] Generated {len(queries)} queries.")
    print(f"[queries] Estimated: {len(queries) * 20}+ places, {len(queries) * 20 * 100}+ reviews")
    print(f"[queries] Run collector: python main.py collect -q {output}")


def cmd_stats(args):
    """Show collector statistics and progress."""
    import json
    from scraper.collector import STATE_FILE, merge_reviews

    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            state = json.load(f)
        print(f"\n=== Collector State ===")
        print(f"Total queries: {len(state.get('queries', []))}")
        print(f"Completed: {len(state.get('completed', {}))}")
        print(f"Failed: {len(state.get('failed', {}))}")
        print(f"Places collected: {state.get('total_places', 0)}")
        print(f"Reviews collected: {state.get('total_reviews', 0)}")
        print(f"Last updated: {state.get('last_updated', 'never')}")
    else:
        print("[stats] No collector state found. Run 'python main.py collect' first.")

    # Show merged data stats
    import pandas as pd
    merged_path = Path("data/processed/collected_all_reviews.parquet")
    if merged_path.exists():
        df = pd.read_parquet(merged_path)
        print(f"\n=== Merged Dataset ===")
        print(f"Reviews: {len(df)}")
        print(f"Places: {df['place_name'].nunique()}")
        print(f"Avg rating: {df['review_rating'].mean():.2f}")
        print(f"Places with most reviews:")
        for place, cnt in df['place_name'].value_counts().head(10).items():
            print(f"  {place}: {cnt}")
    else:
        print("\n[stats] No merged dataset yet. It merges automatically every 10 batches.")
    """Run the complete pipeline: scrape + analyze."""
    from scraper.run_scraper import scrape_and_get_reviews
    from analytics.pipeline import AnalyticsPipeline

    queries = args.queries
    if not queries:
        print("ERROR: At least one search query is required.")
        sys.exit(1)

    output_name = args.output or "results"
    method = args.sentiment_method or "transformer"

    print(f"\n{'='*60}")
    print(f"  FULL PIPELINE: Scrape + Analyze")
    print(f"  Queries: {queries}")
    print(f"  Sentiment: {method}")
    print(f"{'='*60}\n")

    reviews_df = scrape_and_get_reviews(queries, output_name)

    if reviews_df is None or reviews_df.empty:
        print("\n❌ Scraping failed. Stopping.")
        sys.exit(1)

    print("\n✅ Scraping done. Running analytics...\n")
    pipeline = AnalyticsPipeline(reviews_df, output_prefix=output_name)
    pipeline.run(sentiment_method=method)

    print(f"\n✅ Full pipeline complete!")
    print(f"Launch dashboard with: python main.py dashboard")


def main():
    parser = argparse.ArgumentParser(
        description="Google Maps Review Analytics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py scrape "coffee shop in Jakarta, Indonesia"
  python main.py analyze data/processed/results_reviews.parquet
  python main.py full "restaurant in Bandung, Indonesia"
  python main.py generate-queries        # auto-generate 100+ queries
  python main.py collect                 # run continuous collector (hours/days)
  python main.py stats                   # check collection progress
  python main.py dashboard
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    scrape_parser = subparsers.add_parser("scrape", help="Scrape Google Maps reviews")
    scrape_parser.add_argument("queries", nargs="+", help="Search queries (e.g., 'coffee shop in Jakarta')")
    scrape_parser.add_argument("-o", "--output", default="results", help="Output file prefix")
    scrape_parser.set_defaults(func=cmd_scrape)

    analyze_parser = subparsers.add_parser("analyze", help="Run analytics pipeline")
    analyze_parser.add_argument("file", help="Path to reviews parquet file")
    analyze_parser.add_argument("-o", "--output", default="analysis", help="Output prefix")
    analyze_parser.add_argument("-s", "--sentiment-method", default="transformer",
                                choices=["transformer", "vader"],
                                help="Sentiment method: transformer (multilingual) or vader (English only)")
    analyze_parser.set_defaults(func=cmd_analyze)

    dashboard_parser = subparsers.add_parser("dashboard", help="Launch Streamlit dashboard")
    dashboard_parser.add_argument("-p", "--port", type=int, default=8501, help="Dashboard port")
    dashboard_parser.set_defaults(func=cmd_dashboard)

    full_parser = subparsers.add_parser("full", help="Run full pipeline (scrape + analyze)")
    full_parser.add_argument("queries", nargs="+", help="Search queries")
    full_parser.add_argument("-o", "--output", default="results", help="Output prefix")
    full_parser.add_argument("-s", "--sentiment-method", default="transformer",
                             choices=["transformer", "vader"],
                             help="Sentiment method")
    full_parser.set_defaults(func=cmd_full)

    collect_parser = subparsers.add_parser("collect", help="Run continuous collector (hours/days)")
    collect_parser.add_argument("-q", "--queries-file", default="scraper/queries.txt",
                                help="Path to queries file (one per line)")
    collect_parser.add_argument("-b", "--batch-size", type=int, default=3,
                                help="Queries per batch (default: 3)")
    collect_parser.add_argument("-d", "--delay", type=int, default=120,
                                help="Seconds between batches (default: 120)")
    collect_parser.add_argument("-m", "--max-batches", type=int, default=0,
                                help="Max batches to run (0=unlimited)")
    collect_parser.add_argument("--reset", action="store_true",
                                help="Reset progress and start fresh")
    collect_parser.set_defaults(func=cmd_collect)

    generate_parser = subparsers.add_parser("generate-queries",
                                             help="Auto-generate queries for max coverage")
    generate_parser.add_argument("-o", "--output", default="scraper/queries.txt",
                                 help="Output file path")
    generate_parser.set_defaults(func=cmd_generate_queries)

    stats_parser = subparsers.add_parser("stats", help="Show collector progress and stats")
    stats_parser.set_defaults(func=cmd_stats)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
