# 🗺️ Google Maps Review Analytics

> Scrape Google Maps reviews → Analyze sentiment → Compare competitors → Generate recommendations
>
> **Interactive dashboard + CLI + 24/7 continuous collector**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **Docker** (for scraping only)

### Install (3 steps)

```bash
git clone https://github.com/ahmadafif5321/GoogleMapScrapper.git
cd GoogleMapScrapper
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### First run

```bash
python main.py full "clinic in Cyberjaya"
```

---

## 📖 Command Reference

### `scrape` — Collect data from Google Maps

```bash
python main.py scrape "clinic in Cyberjaya" "klinik in Putrajaya"
python main.py scrape "restaurant in Bandung" -o my_results
```

| Flag | Default | Description |
|------|---------|-------------|
| `queries` | required | One or more search terms |
| `-o` | `results` | Output file name prefix |

### `analyze` — Run sentiment + insights pipeline

```bash
python main.py analyze data/processed/results_reviews.parquet
python main.py analyze data/processed/results_reviews.parquet -s vader      # fast (English)
python main.py analyze data/processed/results_reviews.parquet -s transformer  # multilingual
python main.py analyze data/processed/results_reviews.parquet -o my_report
```

| Flag | Default | Description |
|------|---------|-------------|
| `file` | required | Path to parquet reviews file |
| `-o` | `analysis` | Output prefix |
| `-s` | `transformer` | `vader` (fast) or `transformer` (multilingual) |

> **Which sentiment method?** Use `vader` for English/Malay reviews (instant, no GPU). Use `transformer` for pure non-English reviews (20min+ without GPU, needs `pip install sentencepiece tiktoken`).

### `collect` — Continuous data collection (hours/days)

```bash
# One-time: collect 50 queries once (~45 min)
python main.py collect -q scraper/queries_100places.txt

# Small batch, long delay (safe)
python main.py collect -b 2 -d 180

# Aggressive, faster
python main.py collect -b 5 -d 60

# Run 50 batches and stop
python main.py collect -m 50

# 24/7 mode: re-scrape every 6 hours
python main.py collect --continuous --cycle-hours 6

# 24/7 with full coverage (332 queries)
python main.py collect -q scraper/queries_full.txt --continuous --cycle-hours 24

# Start fresh (ignore previous progress)
python main.py collect --reset
```

| Flag | Default | Description |
|------|---------|-------------|
| `-q` | `scraper/queries.txt` | Queries file path |
| `-b` | `3` | Queries per batch (higher = faster, riskier) |
| `-d` | `120` | Seconds delay between batches |
| `-m` | `0` (unlimited) | Max batches, then stop |
| `--continuous` | off | Re-run all queries on every cycle |
| `--cycle-hours` | `24` | Hours between cycles in continuous mode |
| `--reset` | off | Delete progress, start fresh |

### `dashboard` — Launch interactive web UI

```bash
python main.py dashboard
python main.py dashboard -p 8080
```

Opens at **http://localhost:8501** with 6 pages:
- 📊 Overview — totals, rankings, rating distribution
- 😊 Sentiment — positive/negative/neutral breakdown
- 🔍 Aspect Analysis — what patients mention per category
- 🔑 Keywords & Topics — word cloud, LDA topics, phrases
- ⚔️ Comparison — side-by-side competitor benchmarking
- 💡 Insights — strengths, weaknesses, improvement roadmap

### `full` — Scrape + analyze in one command

```bash
python main.py full "clinic in Cyberjaya"
python main.py full "coffee shop in Jakarta" -s vader
```

### `generate-queries` — Auto-create query list

```bash
python main.py generate-queries                          # 332 queries (full coverage)
python main.py generate-queries -o my_queries.txt        # custom output file
```

Pre-built query files:
| File | Queries | Estimated places | Est. reviews |
|------|---------|-----------------|--------------|
| `scraper/queries_100places.txt` | 50 | ~100-200 | ~20K-50K |
| `scraper/queries_full.txt` | 332 | ~500-1000+ | ~100K-300K |

### `stats` — Check collection progress

```bash
python main.py stats
```

Shows: completed/failed queries, total places, total reviews, latest merged dataset.

### `export` — Export all data as CSV

```bash
python main.py export
```

Generates in `data/processed/`:

| File | Contents |
|------|----------|
| `all_reviews.csv` | Every review text + rating + place name |
| `places_summary.csv` | Per-place: review count, avg rating, address |
| `sentiment_by_place.csv` | Positive/negative % for each place |
| `recommendations.csv` | Prioritized improvement actions |
| `aspect_summary.csv` | What customers talk about most |
| `comparison_ranking.csv` | All places ranked by sentiment |

---

## 🔄 How Continuous Collection Works

```
CYCLE START
    │
    ├── Check Docker
    ├── Pull scraper image
    │
    ┌─────────────────────────────┐
    │  BATCH LOOP                 │
    │                             │
    │  1. Take 3 queries          │
    │  2. Run Docker scraper      │
    │  3. Save reviews to parquet │
    │  4. Save progress to state  │
    │  5. Wait 120 seconds        │
    │  6. Repeat until all done   │
    │                             │
    │  Every 10 batches:          │
    │    → Merge all data         │
    │    → Export CSV files       │
    └─────────────────────────────┘
    │
    ├── Merge all batch files
    ├── Export all CSVs
    │
    └── If --continuous:
        Wait <cycle-hours> hours
        Reset completed queries
        Go to CYCLE START
```

**Progress is saved after every batch.** If the collector crashes, the PC restarts, or you Ctrl+C — just run the same command again. It picks up where it left off.

**State file**: `scraper/collector_state.json` — tracks every query's status. Delete it to start fresh (`--reset` does this).

---

## 📁 Project Structure

```
GoogleMapScrapper/
│
├── main.py                     # CLI entry point (all commands)
├── config.py                   # Configuration & aspect categories
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Docker scraper config
│
├── scraper/
│   ├── run_scraper.py          # Runs gosom/google-maps-scraper via Docker
│   ├── collector.py            # Continuous batch collector with resume
│   ├── query_generator.py      # Auto-generates queries for max coverage
│   ├── queries.txt             # Input: search queries
│   ├── queries_100places.txt   # Pre-built: 50 queries for ~100 places
│   ├── queries_full.txt        # Pre-built: 332 queries for max coverage
│   └── collector_state.json    # Runtime: collector progress state
│
├── analytics/
│   ├── preprocess.py           # Text cleaning, tokenization, stats
│   ├── sentiment.py            # Multilingual sentiment + aspect-based analysis
│   ├── topics.py               # TF-IDF, KeyBERT, LDA topic modeling, n-grams
│   ├── insights.py             # Negative review analysis, strengths, recommendations
│   ├── compare.py              # Cross-place competitor comparison
│   └── pipeline.py             # Full analytics orchestrator
│
├── dashboard/
│   └── app.py                  # Streamlit 6-page interactive dashboard
│
└── data/
    ├── raw/                    # Raw scraper JSON output
    │   └── results.json
    └── processed/              # Processed parquet, JSON, CSV files
        ├── *reviews.parquet    # Extracted reviews
        ├── *analyzed.parquet   # Analyzed with sentiment
        ├── *results.json       # Full analysis results
        ├── all_reviews.csv     # All reviews as CSV
        ├── places_summary.csv  # Per-place summary
        ├── sentiment_by_place.csv
        ├── recommendations.csv
        ├── aspect_summary.csv
        └── comparison_ranking.csv
```

---

## ⚙️ Configuration (`config.py`)

### Scraper Settings

```python
SCRAPER_CONCURRENCY = 4       # Parallel browsers (max for 4-core CPU)
SCRAPER_DEPTH = 15            # Max scroll depth (more = more places per query)
SCRAPER_EXTRA_REVIEWS = True  # Get ~300 reviews per place (vs ~8 without)
SCRAPER_EXIT_TIMEOUT = "30m"  # Auto-stop after 30min of no new results
SCRAPER_TIMEOUT_SECONDS = 7200 # Max total time per scrape (2 hours)

# Geographic targeting (set to activate)
SCRAPER_GEO = None            # "lat,lon" e.g., "2.9221,101.6514"
SCRAPER_RADIUS = None         # meters, e.g., 50000
SCRAPER_ZOOM = None           # 1-21, e.g., 14
SCRAPER_GRID_BBOX = None      # "minLat,minLon,maxLat,maxLon"
SCRAPER_GRID_CELL = None      # cell size in km
```

### Analytics Settings

```python
SENTIMENT_MODEL = "cardiffnlp/twitter-xlm-roberta-base-sentiment"  # multilingual
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"          # keyword extraction
MAX_REVIEWS_PER_PLACE = 300   # Cap reviews for analysis
```

---

## 🔧 Common Tasks

### Collect reviews from 100+ clinics

```bash
python main.py collect -q scraper/queries_100places.txt -b 3 -d 120
python main.py analyze data/processed/collected_all_reviews.parquet -s vader
python main.py dashboard
```

### Run collector 24/7

```bash
# Run in background (Linux/Mac)
nohup python main.py collect -q scraper/queries_100places.txt --continuous --cycle-hours 6 &

# Check status
python main.py stats

# Stop
kill <PID>

# Resume (same command, auto-resumes)
python main.py collect -q scraper/queries_100places.txt --continuous --cycle-hours 6
```

### Export all data for Excel

```bash
python main.py export
# Files in data/processed/ — open all_reviews.csv in Excel
```

### Compare specific competitors

Edit `queries.txt` with exact business names:
```
Klinik Utama Cyberjaya
Hospital Cyberjaya
Qualitas SV Care Clinic Cyberjaya
```
```bash
python main.py full "Klinik Utama Cyberjaya" "Hospital Cyberjaya" "Qualitas SV Care Clinic Cyberjaya"
```

### Add new aspect categories

Edit `config.py` → `ASPECT_CATEGORIES`:
```python
ASPECT_CATEGORIES = {
    "cleanliness": ["clean", "dirty", "hygiene", "spotless", "bersih", "kotor"],
    "parking": ["parking", "parkir", "garage", "basement"],
    # ...
}
```

---

## 🖥️ Hardware Requirements

| Scale | Places | Reviews | CPU | RAM | Time |
|-------|--------|---------|-----|-----|------|
| **Small** | <30 | <10K | 2 cores | 4GB | 15 min |
| **Medium** | 30-200 | 10K-60K | 4 cores | 8GB | 1-3 hrs |
| **Large** | 200-1000 | 60K-300K | 8 cores | 16GB | 6-24 hrs |
| **Full city** | 1000+ | 300K+ | 16 cores | 32GB | Days |

> For analytics: **VADER** (instant, no GPU) vs **Transformer** (GPU recommended for large datasets).

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| **Docker not running** | `sudo systemctl start docker` |
| **No reviews in output** | Scraper needs `-extra-reviews` flag (enabled by default) |
| **Only 8 reviews per place** | Old data before bug fix. Re-scrape with latest code |
| **Google blocking/rate limit** | Increase `-d` (delay) to 180-300, reduce `-b` to 2 |
| **Collector crashes** | Just re-run same command — it resumes from state |
| **Memory errors** | Close Firefox/browser, reduce `-b` (batch size) |
| **ModuleNotFoundError** | `pip install sentencepiece tiktoken` (for transformer mode) |
| **Streamlit port in use** | `python main.py dashboard -p 8080` |
| **Want to start fresh** | `python main.py collect --reset` |

---

## 📊 Analytics Pipeline

```
Phase 1: Preprocessing
  ├── Clean text (remove URLs, normalize unicode)
  ├── Tokenize (NLTK)
  └── Filter short reviews

Phase 2: Sentiment Analysis
  ├── Multilingual transformer (xlm-roberta) OR VADER (English)
  ├── Aspect matching (service, price, quality, ambiance, etc.)
  └── Per-place sentiment summary

Phase 3: Topic & Keyword Extraction
  ├── TF-IDF keyword extraction
  ├── LDA topic modeling (5 topics)
  ├── N-gram phrase frequencies
  └── Keyword-sentiment correlation

Phase 4: Insights & Recommendations
  ├── Negative review deep-dive
  ├── Auto-generated improvement roadmap
  ├── Strength identification from positives
  └── Competitor comparison matrix

Output:
  ├── Interactive dashboard (6 pages)
  ├── JSON analysis results
  └── CSV exports for all data
```

---

## 📄 License

MIT — see [LICENSE](LICENSE)

## 🙏 Credits

- [gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper) — Google Maps scraper engine
- [HuggingFace Transformers](https://huggingface.co/) — Multilingual sentiment models
- [Streamlit](https://streamlit.io/) — Dashboard framework
