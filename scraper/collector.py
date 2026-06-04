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
    """Merge all collected reviews into a single DataFrame."""
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

    places_count = merged["place_name"].nunique()
    print(f"[collector] Merged: {len(merged)} reviews from {places_count} places "
          f"({len(parquet_files)} batches)")
    print(f"[collector] Saved to {merged_path}")

    return merged


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
):
    """
    Continuous collector - runs until all queries are done or max_batches reached.

    Args:
        queries_file: Path to file with one query per line
        batch_size: Queries per scraper run (more = faster but riskier)
        delay_seconds: Wait between batches (avoids Google rate limiting)
        max_batches: Stop after N batches (0 = unlimited)
        resume: Resume from previous state
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

    # Final merge
    print("\n[collector] Merging all batches...")
    merge_reviews()

    print(f"\n{'='*60}")
    print(f"  COLLECTOR FINISHED")
    print(f"  Places: {state['total_places']}")
    print(f"  Reviews: {state['total_reviews']}")
    print(f"  Completed queries: {len(state['completed'])}")
    print(f"  Failed queries: {len(state['failed'])}")
    print(f"{'='*60}\n")


def reset_collector():
    """Reset collector state to start fresh."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("[collector] State reset.")
