# 📚 Data Collection Guide — How to Get More (and Better) Data

This guide explains how the collector actually works, what limits exist,
and exactly how to grow the dataset for better Megu ReviewScore reports.

---

## 1. How the scraper works (the mental model)

```
QUERY ("dental clinic in Putrajaya")
  └─> Google Maps search results (places)        ← controlled by -depth
        └─> for each place: details + reviews    ← controlled by -extra-reviews
              └─> JSON line per place in data/raw/batch_XXXX.json
```

- **`-depth 15`** = how far the scraper scrolls the search results.
  More depth = more places per query (roughly 20 places per depth unit,
  diminishing after ~100-120 places per query).
- **`-extra-reviews`** = fetch the full review feed per place
  (without it you get only ~8 reviews!). In practice this captures
  **up to ~1,000 reviews per place** in one pass.
- One query costs ~3-10 minutes depending on how many places it finds.

## 2. What we measured on the current dataset (audited)

| Fact | Value | Meaning |
|---|---|---|
| Capture rate vs Google's claimed counts | **97.9% average** | Per-place capture is nearly complete |
| Exception | Mega-places (mall: 14k reviews, we got ~1k) | Google feeds cap out — acceptable, those aren't clinics |
| Reviews with exact timestamps | 100% | Time-series & decline detection work |
| Owner replies captured | 38% of reviews | Response-health analysis works |
| Original Malay text | preserved ✅ | Even with `-lang en`, `Description` keeps the original |

**Conclusion: per-place depth is NOT the bottleneck. Coverage (queries) and
freshness (cycles) are.**

## 3. The 3 ways to get more data — in priority order

### A. More queries = more businesses (breadth) — biggest win
You have run only **50 of 336** prepared queries. Each new query ≈ 20-100
new places ≈ 2,000-20,000 reviews.

```bash
# everything prepared (clinic-focused, 336 queries — runs ~1-2 days)
python main.py collect -q scraper/queries_full.txt -b 2 -d 120

# NEW: multi-niche expansion pack (F&B, automotive, beauty, hotel…)
python main.py collect -q scraper/queries_expansion.txt -b 2 -d 120
```

Rule of thumb: **(keywords per niche) × (areas)**. 10 keywords × 12 areas
= 120 queries ≈ 1,500+ unique places after dedup.

### B. Continuous cycles = freshness (the storytelling fuel)
Reports answer "did it improve LAST month?" only if you re-scrape.
Re-running the same queries picks up **new reviews** (old ones dedup away).

```bash
# weekly refresh of everything, forever:
nohup python main.py collect -q scraper/queries_full.txt \
      --continuous --cycle-hours 168 &
```

Each cycle adds only the delta (new reviews since last cycle), and the
Megu ingest is dedup-safe — run the sync as often as you like.

### C. Targeted re-scrape = heal thin spots
35 businesses have zero reviews, 79 have <10. Put their **exact names**
in a file and run them as queries — exact-name queries resolve directly
to the place:

```bash
python main.py scrape "Klinik XYZ Cyberjaya" "Klinik ABC Dengkil" -o heal_batch
```

## 4. Feeding Megu ReviewScore (the sync)

After any collection run:

```bash
cd ~/megu-reviewscore
.venv/bin/python -m scripts.sync_from_collector        # only new/changed files
```

Or automate it — cron example (daily 4am):
```cron
0 4 * * * cd /home/ahmadafif5321/megu-reviewscore && .venv/bin/python -m scripts.sync_from_collector >> storage/sync.log 2>&1
```

The sync is incremental: it remembers which raw files it has seen
(by modification time) and dedups review-by-review. Safe to run anytime.

## 5. Scaling rules & anti-blocking

| Setting | Safe | Aggressive | Notes |
|---|---|---|---|
| `-b` batch size | 2 | 5 | bigger = faster but riskier + worse attribution |
| `-d` delay (s) | 180 | 60 | increase if you see empty results |
| Time of day | night MYT | any | less contention |
| `-b 1` | — | — | use for NEW niches: perfect per-query attribution |

If batches start returning nothing: stop, wait 1-2 hours, increase `-d`.
The collector already auto-pauses 5 minutes after 3 consecutive failures
and retries failed queries up to 3×.

## 6. When do you need MORE than this?

| Goal | What to do |
|---|---|
| Another city (e.g. JB, Penang) | New area list in `query_generator.py`, new queries file |
| A customer's business not in DB | Their exact name as a query (Section C) — 5 minutes |
| >1,000 reviews for a mega-place | Run periodic cycles; each cycle catches the newest ~1k — over months you build the full history |
| Other platforms later | Megu's source-connector layer accepts CSV today; new connectors plug in without touching scoring |
