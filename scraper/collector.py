"""
Continuous Collector - runs scraper in batches, saves progress, resumes on crash.
Designed for long-running data collection (hours to days).
"""
import json
import time
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

from scraper.run_scraper import run_scraper, extract_reviews_from_df, check_docker, pull_image
from config import RAW_DIR, PROCESSED_DIR, SCRAPER_CONCURRENCY

STATE_FILE = Path(__file__).resolve().parent / "collector_state.json"


def load_state() -> dict:
    """Load collector state (which queries are done, in-progress, pending)."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "queries": [],        # all queries loaded
        "completed": {},      # query -> {"places": N, "reviews": N, "time": "..."}
        "failed": {},         # query -> error message
        "batch_size": 3,
        "delay_seconds": 60,
        "total_places": 0,
        "total_reviews": 0,
        "last_updated": None,
    }


def save_state(state: dict):
    """Save collector state to disk."""
    state["last_updated"] = datetime.now().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def load_queries(filepath: Path) -> List[str]:
    """Load queries from a text file (one per line)."""
    if not filepath.exists():
        return []
    with open(filepath) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def merge_reviews(output_dir: Path = PROCESSED_DIR) -> Optional[pd.DataFrame]:
    """Merge all collected reviews into a single DataFrame and export CSV."""
    parquet_files = sorted(output_dir.glob("batch_*_reviews.parquet"))
    if not parquet_files:
        print("[collector] No batch files found to merge.")
        return None

    dfs = []
    for f in parquet_files:
        try:
            df = pd.read_parquet(f)
            dfs.append(df)
        except Exception as e:
            print(f"[collector] Skipping {f.name}: {e}")

    if not dfs:
        return None

    merged = pd.concat(dfs, ignore_index=True)
    merged = merged.drop_duplicates(subset=["place_id", "review_text"])
    merged = merged[merged["review_text"].str.strip() != ""]

    merged_path = output_dir / "collected_all_reviews.parquet"
    merged.to_parquet(merged_path, index=False)

    # Also export CSV
    csv_path = output_dir / "collected_all_reviews.csv"
    merged.to_csv(csv_path, index=False, encoding="utf-8-sig")

    places_count = merged["place_name"].nunique()
    print(f"[collector] Merged: {len(merged)} reviews from {places_count} places "
          f"({len(parquet_files)} batches)")
    print(f"[collector] Saved: {merged_path} + {csv_path}")

    return merged


def export_all_csv():
    """Export all collected data as CSV files."""
    import pandas as pd

    # Reviews CSV - try multiple sources
    reviews_paths = [
        PROCESSED_DIR / "collected_all_reviews.parquet",
        PROCESSED_DIR / "results_full_reviews.parquet",
        PROCESSED_DIR / "scraped_results_reviews.parquet",
        PROCESSED_DIR / "results_reviews.parquet",
    ]

    reviews_df = None
    for rp in reviews_paths:
        if rp.exists():
            reviews_df = pd.read_parquet(rp)
            break

    if reviews_df is not None and not reviews_df.empty:
        csv_path = PROCESSED_DIR / "all_reviews.csv"
        reviews_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"[export] Reviews: {csv_path} ({len(reviews_df)} rows)")

        # Places summary
        places = reviews_df.groupby("place_name").agg(
            total_reviews=("review_text", "count"),
            avg_rating=("review_rating", "mean"),
            category=("place_category", "first"),
            address=("place_address", "first"),
        ).reset_index().round(2)
        places = places.sort_values("total_reviews", ascending=False)
        places_path = PROCESSED_DIR / "places_summary.csv"
        places.to_csv(places_path, index=False, encoding="utf-8-sig")
        print(f"[export] Places summary: {places_path} ({len(places)} places)")
    else:
        print("[export] No reviews found. Run scraper or collector first.")

    # Analysis results CSV (if exists)
    analysis_paths = list(PROCESSED_DIR.glob("*_results.json"))
    if analysis_paths:
        latest = max(analysis_paths, key=lambda p: p.stat().st_mtime)
        import json
        with open(latest) as f:
            data = json.load(f)

        # Sentiment summary CSV
        sent = data.get("sentiment_summary", {})
        if sent:
            rows = []
            for place, s in sent.items():
                rows.append({
                    "place_name": place,
                    "total_reviews": s.get("total_reviews", 0),
                    "positive_pct": s.get("positive_pct", 0),
                    "neutral_pct": s.get("neutral_pct", 0),
                    "negative_pct": s.get("negative_pct", 0),
                    "avg_sentiment_score": s.get("avg_sentiment_score", 0),
                    "avg_review_rating": s.get("avg_review_rating", 0),
                })
            sent_df = pd.DataFrame(rows).sort_values("positive_pct", ascending=False)
            sent_csv = PROCESSED_DIR / "sentiment_by_place.csv"
            sent_df.to_csv(sent_csv, index=False, encoding="utf-8-sig")
            print(f"[export] Sentiment: {sent_csv} ({len(rows)} places)")

        # Recommendations CSV
        recs = data.get("recommendations", [])
        if recs:
            rec_rows = []
            for r in recs:
                for action in r.get("actions", []):
                    rec_rows.append({
                        "severity": r.get("severity", ""),
                        "category": r.get("category", ""),
                        "title": r.get("title", ""),
                        "action": action,
                        "negative_review_count": r.get("negative_review_count", 0),
                    })
            rec_df = pd.DataFrame(rec_rows)
            rec_csv = PROCESSED_DIR / "recommendations.csv"
            rec_df.to_csv(rec_csv, index=False, encoding="utf-8-sig")
            print(f"[export] Recommendations: {rec_csv} ({len(rec_rows)} actions)")

        # Aspect summary CSV
        aspect = data.get("aspect_summary", {})
        if aspect:
            arows = []
            for name, a in aspect.items():
                if a.get("total_mentions", 0) > 0:
                    arows.append({
                        "aspect": name,
                        "total_mentions": a.get("total_mentions", 0),
                        "mention_rate_pct": a.get("mention_rate", 0),
                        "positive_pct": a.get("positive_pct", 0),
                        "negative_pct": a.get("negative_pct", 0),
                        "avg_sentiment": a.get("avg_sentiment_score", 0),
                    })
            adf = pd.DataFrame(arows).sort_values("total_mentions", ascending=False)
            acsv = PROCESSED_DIR / "aspect_summary.csv"
            adf.to_csv(acsv, index=False, encoding="utf-8-sig")
            print(f"[export] Aspect summary: {acsv}")

    # Comparison CSV
    comp = data.get("comparison_report", {}).get("rankings", {})
    if comp:
        crows = []
        for place, c in comp.items():
            crows.append({
                "place_name": place,
                "rank": c.get("rank", 0),
                "sentiment_health_score": c.get("sentiment_health_score", 0),
                "positive_pct": c.get("positive_pct", 0),
                "negative_pct": c.get("negative_pct", 0),
                "avg_rating": c.get("avg_rating", 0),
                "total_reviews": c.get("total_reviews", 0),
            })
        cdf = pd.DataFrame(crows).sort_values("rank")
        ccsv = PROCESSED_DIR / "comparison_ranking.csv"
        cdf.to_csv(ccsv, index=False, encoding="utf-8-sig")
        print(f"[export] Comparison: {ccsv}")

    print("[export] Done. All CSV files in data/processed/")


def run_batch(queries: List[str], batch_num: int, state: dict) -> bool:
    """
    Run a single batch of queries through the scraper.
    Returns True if successful.
    """
    batch_name = f"batch_{batch_num:04d}"
    print(f"\n{'='*60}")
    print(f"  COLLECTOR: Batch {batch_num} - {len(queries)} queries")
    for q in queries:
        print(f"    -> {q}")
    print(f"{'='*60}")

    start = time.time()

    try:
        df = run_scraper(queries, output_name=batch_name)
    except Exception as e:
        for q in queries:
            state["failed"][q] = str(e)
        save_state(state)
        print(f"[collector] Batch {batch_num} FAILED: {e}")
        return False

    if df is None or df.empty:
        for q in queries:
            state["failed"][q] = "No results returned"
        save_state(state)
        print(f"[collector] Batch {batch_num} returned no results.")
        return False

    # Extract reviews and save
    reviews_df = extract_reviews_from_df(df)
    if not reviews_df.empty:
        reviews_path = PROCESSED_DIR / f"{batch_name}_reviews.parquet"
        reviews_df.to_parquet(reviews_path, index=False)

        places_count = df["title"].nunique()
        reviews_count = len(reviews_df)

        state["total_places"] += places_count
        state["total_reviews"] += reviews_count

        for q in queries:
            state["completed"][q] = {
                "places": places_count,
                "reviews": reviews_count,
                "time": datetime.now().isoformat(),
                "batch": batch_num,
            }

        elapsed = time.time() - start
        print(f"[collector] Batch {batch_num} done: {places_count} places, "
              f"{reviews_count} reviews in {elapsed:.0f}s")
        print(f"[collector] Running total: {state['total_places']} places, "
              f"{state['total_reviews']} reviews")
        save_state(state)
        return True

    return False


def get_pending_queries(state: dict) -> List[str]:
    """Get queries that haven't been completed yet."""
    all_queries = set(state.get("queries", []))
    completed = set(state["completed"].keys())
    failed = set(state["failed"].keys())

    # Retry failed queries up to 3 times
    retry_keys = []
    for q in failed:
        fail_entry = state["failed"].get(q, "")
        if isinstance(fail_entry, dict):
            attempts = fail_entry.get("attempts", 1)
        else:
            attempts = 1
        if attempts < 3:
            retry_keys.append(q)

    pending = list(all_queries - completed) + retry_keys
    return pending


def run_collector(
    queries_file: Path,
    batch_size: int = 3,
    delay_seconds: int = 60,
    max_batches: int = 0,
    resume: bool = True,
    continuous: bool = False,
    cycle_delay_hours: float = 24.0,
):
    """
    Continuous collector - runs until all queries are done or max_batches reached.

    Args:
        queries_file: Path to file with one query per line
        batch_size: Queries per scraper run (more = faster but riskier)
        delay_seconds: Wait between batches (avoids Google rate limiting)
        max_batches: Stop after N batches (0 = unlimited)
        resume: Resume from previous state
        continuous: If True, re-runs all queries on a cycle (24/7 mode)
        cycle_delay_hours: Hours between cycles in continuous mode
    """
    state = load_state() if resume else {
        "queries": [], "completed": {}, "failed": {},
        "batch_size": batch_size, "delay_seconds": delay_seconds,
        "total_places": 0, "total_reviews": 0, "last_updated": None,
    }

    # Load queries
    all_queries = load_queries(queries_file)
    if not all_queries:
        print("[collector] No queries found!")
        return

    # Update state with any new queries
    existing = set(state["queries"])
    new_queries = [q for q in all_queries if q not in existing]
    if new_queries:
        state["queries"] = all_queries
        print(f"[collector] Loaded {len(all_queries)} total queries "
              f"({len(new_queries)} new)")
    else:
        print(f"[collector] Loaded {len(all_queries)} queries from state")

    state["batch_size"] = batch_size
    state["delay_seconds"] = delay_seconds
    save_state(state)

    # Check Docker
    if not check_docker():
        print("[collector] ERROR: Docker required. Start Docker first.")
        return

    pull_image()

    cycle = 1

    while True:
        print(f"\n{'#'*60}")
        print(f"  CYCLE {cycle}")
        print(f"{'#'*60}")

        batch_num = 1
        consecutive_failures = 0

        while True:
            pending = get_pending_queries(state)

            if not pending:
                print("\n[collector] ALL QUERIES COMPLETE!")
                break

            if max_batches > 0 and batch_num > max_batches:
                print(f"\n[collector] Reached max_batches={max_batches}. Stopping.")
                break

            # Take next batch
            batch_queries = pending[:batch_size]
            print(f"\n[collector] Pending: {len(pending)} queries, "
                  f"completed: {len(state['completed'])}, failed: {len(state['failed'])}")

            success = run_batch(batch_queries, batch_num, state)

            if success:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                for q in batch_queries:
                    state["failed"][q] = state["failed"].get(q, {"attempts": 0})
                    if isinstance(state["failed"][q], dict):
                        state["failed"][q]["attempts"] = state["failed"][q].get("attempts", 0) + 1
                    else:
                        state["failed"][q] = {"attempts": 1, "error": str(state["failed"][q])}
                save_state(state)

                if consecutive_failures >= 3:
                    print("[collector] 3 consecutive failures. Possible rate limit or network issue.")
                    print("[collector] Waiting 5 minutes before continuing...")
                    time.sleep(300)
                    consecutive_failures = 0

            batch_num += 1

            # Auto-merge every 10 batches
            if batch_num % 10 == 0:
                merge_reviews()

            # Delay between batches
            if pending:
                print(f"[collector] Waiting {delay_seconds}s before next batch...")
                time.sleep(delay_seconds)

        # Final merge for this cycle
        print("\n[collector] Merging all batches...")
        merge_reviews()

        # Export CSV
        export_all_csv()

        print(f"\n{'='*60}")
        print(f"  CYCLE {cycle} COMPLETE")
        print(f"  Places: {state['total_places']}")
        print(f"  Reviews: {state['total_reviews']}")
        print(f"  Completed queries: {len(state['completed'])}")
        print(f"  Failed queries: {len(state['failed'])}")
        print(f"{'='*60}\n")

        if not continuous:
            break

        # Reset completed for next cycle (re-scrape to get new reviews)
        print(f"[collector] Continuous mode: waiting {cycle_delay_hours}h before next cycle...")
        print(f"[collector] Next cycle will re-scrape all queries for fresh reviews.")
        time.sleep(cycle_delay_hours * 3600)
        state["completed"] = {}
        state["failed"] = {}
        save_state(state)
        cycle += 1


def reset_collector():
    """Reset collector state to start fresh."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("[collector] State reset.")
