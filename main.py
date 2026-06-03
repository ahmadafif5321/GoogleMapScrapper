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


def main():
    parser = argparse.ArgumentParser(
        description="Google Maps Review Analytics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py scrape "coffee shop in Jakarta, Indonesia"
  python main.py analyze data/processed/results_reviews.parquet
  python main.py full "restaurant in Bandung, Indonesia"
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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
