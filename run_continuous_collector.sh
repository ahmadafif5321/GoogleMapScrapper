#!/usr/bin/env bash
# Always-on background collector (Lane 2).
#
# Two-lane scraping model:
#   Lane 1 (PRIORITY): a paid/on-demand customer capture. The Megu app calls
#           scraper.scrape_coord.priority_scrape(), which raises a flag and
#           takes the exclusive scrape lock. The collector finishes its current
#           batch, then waits (wait_if_yield) until the capture is done — so the
#           paying customer always gets scraped + their report FIRST.
#   Lane 2 (THIS SCRIPT): the all-day background collector. Runs continuously,
#           cycling through every query in queries_all.txt to keep the dataset
#           fresh, and automatically yields to Lane 1 whenever a customer arrives.
#
# Usage:  nohup ./run_continuous_collector.sh >> storage/collector.log 2>&1 &
# Stop:   pkill -f "main.py collect"
#
# It self-restarts if the collector exits (crash / docker hiccup), so it truly
# runs all day. Conservative pacing (small batches, delays) keeps Google happy.

cd "$(dirname "$0")" || exit 1
QUERIES="scraper/queries_all.txt"
BATCH=2
DELAY=180          # seconds between batches
CYCLE_HOURS=12     # re-scrape everything every 12h to stay fresh

mkdir -p storage
echo "[$(date)] continuous collector starting (queries=$QUERIES)"

while true; do
  .venv/bin/python main.py collect \
      -q "$QUERIES" -b "$BATCH" -d "$DELAY" \
      --continuous --cycle-hours "$CYCLE_HOURS"
  code=$?
  echo "[$(date)] collector exited (code $code) — restarting in 60s"
  sleep 60
done
