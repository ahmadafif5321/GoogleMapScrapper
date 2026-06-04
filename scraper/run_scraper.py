"""
Phase 1: Google Maps Scraper
Runs gosom/google-maps-scraper via Docker and parses the output JSON.
"""
import json
import subprocess
import time
import shutil
from pathlib import Path
from typing import Optional
import pandas as pd

from config import (
    RAW_DIR, SCRAPER_DOCKER_IMAGE, SCRAPER_CONCURRENCY,
    SCRAPER_DEPTH, SCRAPER_LANG, SCRAPER_EXTRA_REVIEWS,
    SCRAPER_EXIT_TIMEOUT, SCRAPER_TIMEOUT_SECONDS,
    SCRAPER_GEO, SCRAPER_RADIUS, SCRAPER_ZOOM,
    SCRAPER_GRID_BBOX, SCRAPER_GRID_CELL, SCRAPER_FAST_MODE,
)

QUERIES_FILE = Path(__file__).resolve().parent / "queries.txt"


def write_queries(places: list[str], filepath: Path = QUERIES_FILE):
    """Write place queries to input file for the scraper."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        for place in places:
            f.write(place.strip() + "\n")
    print(f"[scraper] Wrote {len(places)} queries to {filepath}")


def check_docker() -> bool:
    """Check if Docker is installed and running."""
    if not shutil.which("docker"):
        print("[scraper] ERROR: Docker is not installed. Install Docker first.")
        return False
    result = subprocess.run(["docker", "info"], capture_output=True, text=True)
    if result.returncode != 0:
        print("[scraper] ERROR: Docker is not running. Start Docker first.")
        return False
    return True


def pull_image() -> bool:
    """Pull the latest scraper Docker image."""
    print(f"[scraper] Pulling Docker image: {SCRAPER_DOCKER_IMAGE} ...")
    result = subprocess.run(
        ["docker", "pull", SCRAPER_DOCKER_IMAGE],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[scraper] Failed to pull image: {result.stderr}")
        return False
    print("[scraper] Image pulled successfully.")
    return True


def run_scraper(queries: list[str], output_name: str = "results") -> Optional[pd.DataFrame]:
    """
    Run the Google Maps scraper via Docker.

    Args:
        queries: List of search queries (e.g., ["coffee shop in Jakarta", ...])
        output_name: Name prefix for output files

    Returns:
        DataFrame with scraped place data, or None if failed.
    """
    if not check_docker():
        return None

    write_queries(queries)

    json_path = RAW_DIR / f"{output_name}.json"
    if json_path.exists():
        json_path.unlink()

    cmd = [
        "docker", "run", "--rm",
        "-v", "gmaps-playwright-cache:/opt",
        "-v", f"{QUERIES_FILE.resolve()}:/queries.txt:ro",
        "-v", f"{RAW_DIR.resolve()}:/out",
        SCRAPER_DOCKER_IMAGE,
        "-input", "/queries.txt",
        "-results", f"/out/{output_name}.json",
        "-json",
        "-depth", str(SCRAPER_DEPTH),
        "-c", str(SCRAPER_CONCURRENCY),
        "-exit-on-inactivity", SCRAPER_EXIT_TIMEOUT,
        "-lang", SCRAPER_LANG,
    ]

    if SCRAPER_EXTRA_REVIEWS:
        cmd.append("-extra-reviews")

    if SCRAPER_GEO:
        cmd.extend(["-geo", SCRAPER_GEO])
    if SCRAPER_RADIUS:
        cmd.extend(["-radius", str(SCRAPER_RADIUS)])
    if SCRAPER_ZOOM:
        cmd.extend(["-zoom", str(SCRAPER_ZOOM)])
    if SCRAPER_GRID_BBOX:
        cmd.extend(["-grid-bbox", SCRAPER_GRID_BBOX])
    if SCRAPER_GRID_CELL:
        cmd.extend(["-grid-cell", str(SCRAPER_GRID_CELL)])
    if SCRAPER_FAST_MODE:
        cmd.append("-fast-mode")

    print(f"[scraper] Running: {' '.join(cmd)}")
    print(f"[scraper] This may take several minutes...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=SCRAPER_TIMEOUT_SECONDS)
        if result.returncode != 0:
            print(f"[scraper] Scraper error (exit code {result.returncode}):")
            print(result.stderr[-2000:])
            return None

        print("[scraper] Scraping completed.")
        if result.stdout:
            print(result.stdout[-1000:])

    except subprocess.TimeoutExpired:
        print(f"[scraper] Timeout after {SCRAPER_TIMEOUT_SECONDS}s. Partial results may be available.")

    return parse_results(json_path)


def parse_results(json_path: Path) -> Optional[pd.DataFrame]:
    """Parse the JSON/JSONL output from the scraper into a DataFrame."""
    json_path = Path(json_path)
    if not json_path.exists():
        print(f"[scraper] Output file not found: {json_path}")
        return None

    with open(json_path, "r") as f:
        raw = f.read().strip()

    if raw.startswith("["):
        data = json.loads(raw)
    else:
        data = [json.loads(line) for line in raw.split("\n") if line.strip()]

    if not data:
        print("[scraper] No results found. Check your queries and try again.")
        return None

    df = pd.json_normalize(data, max_level=1)
    print(f"[scraper] Parsed {len(df)} places from {json_path}")

    processed_path = RAW_DIR.parent / "processed" / f"{json_path.stem}_parsed.parquet"
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(processed_path, index=False)
    print(f"[scraper] Saved parsed data to {processed_path}")

    return df


def extract_reviews_from_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract and flatten reviews from the scraped DataFrame.
    Merges user_reviews + user_reviews_extended, deduplicates.
    Each row becomes one review.
    """
    reviews_list = []
    seen = set()

    for _, row in df.iterrows():
        place_name = row.get("title", "Unknown")
        place_id = row.get("place_id", row.get("data_id", ""))
        place_rating = row.get("review_rating", 0)
        place_category = row.get("category", "")
        place_address = row.get("address", "")

        # Merge both review sources
        all_reviews = []
        for field in ["user_reviews", "user_reviews_extended"]:
            raw = row.get(field)
            if raw is None:
                continue
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    continue
            if isinstance(raw, list):
                all_reviews.extend(raw)

        if not all_reviews:
            continue

        for review in all_reviews:
            if not isinstance(review, dict):
                continue
            desc = (review.get("Description", "") or review.get("text", "")
                    or review.get("text_original", "") or review.get("text_translated", ""))
            if not desc or not desc.strip():
                continue

            # Deduplicate by place_id + first 100 chars of review
            dedup_key = (str(place_id), desc[:100].strip().lower())
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            rating = review.get("Rating", 0) or review.get("stars", 0) or review.get("rating_float", 0)
            reviews_list.append({
                "place_name": place_name,
                "place_id": str(place_id),
                "place_rating": place_rating,
                "place_category": place_category,
                "place_address": place_address,
                "review_text": desc,
                "review_rating": rating,
                "review_date": review.get("When", "") or review.get("published_at", ""),
                "reviewer_name": review.get("Name", "") or review.get("name", ""),
                "reviewer_photos": review.get("photos_count", 0),
                "review_likes": review.get("likes_count", 0),
            })

    if not reviews_list:
        print("[scraper] No reviews found in data.")
        return pd.DataFrame()

    reviews_df = pd.DataFrame(reviews_list)
    reviews_df = reviews_df[reviews_df["review_text"].str.strip() != ""]

    print(f"[scraper] Extracted {len(reviews_df)} reviews from {df['title'].nunique()} places "
          f"(avg {len(reviews_df)/max(df['title'].nunique(),1):.0f} per place).")

    return reviews_df


def scrape_and_get_reviews(queries: list[str], output_name: str = "results") -> Optional[pd.DataFrame]:
    """
    Full pipeline: scrape places and extract reviews into a flat DataFrame.

    Returns:
        DataFrame with one review per row, or None if failed.
    """
    df = run_scraper(queries, output_name)
    if df is None or df.empty:
        return None

    reviews_df = extract_reviews_from_df(df)

    if not reviews_df.empty:
        path = RAW_DIR.parent / "processed" / f"{output_name}_reviews.parquet"
        reviews_df.to_parquet(path, index=False)
        print(f"[scraper] Saved {len(reviews_df)} reviews to {path}")

    return reviews_df
