# 🗺️ Google Maps Review Intelligence Platform

> **Scrape thousands of Google Maps reviews → NLP sentiment & topic analysis → 6-page interactive dashboard → Actionable business insights**
>
> *Bilingual ◆ Batch-collected 450K+ reviews across 12 cities ◆ 3,000+ places ◆ 3,200 lines of Python ◆ 1.1GB of real analytics data*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-required-2496ED?logo=docker)](https://docker.com)

---

## 🎯 What This System Does

| Stage | Tool | Output |
|-------|------|--------|
| **Collect** | Docker scraper engine, batch scheduler | 450K+ reviews from 3,000+ places |
| **Analyze** | XLM-RoBERTa sentiment, LDA topics, KeyBERT keywords | Sentiment scores, 9 aspect categories, topic clusters |
| **Visualize** | 6-page Streamlit dashboard | Rankings, trends, word clouds, comparison matrices |
| **Export** | CSV/Parquet/JSON | Excel-ready files for every analytical dimension |
| **Loop** | 24/7 continuous collector with auto-resume | Fresh data every N hours, forever |

### 📊 Real Data — Already Collected

```
 2,081 places  ·  17,463 reviews  —  Cyberjaya  +  Putrajaya
   419 places  ·  10,685 reviews  —  Dengkil  +  Bangi  +  Sepang
   220 places  ·   6,414 reviews  —  Kajang  +  Serdang
   163 places  ·   4,082 reviews  —  Seri Kembangan
   155 places  ·   3,399 reviews  —  Puchong
   108 places  ·   1,649 reviews  —  Bandar Baru Bangi
    39 places  ·     694 reviews  —  Subang Jaya
    11 places  ·     429 reviews  —  Putra Heights
───────       ──────────
 3,019 places · 454,956 reviews  —  and growing every cycle
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/ahmadafif5321/GoogleMapScrapper.git
cd GoogleMapScrapper
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### The One-Liner

```bash
python main.py full "clinic in Cyberjaya"
```

Scrapes reviews from Google Maps, runs sentiment analysis, generates insights. Ready for dashboard.

---

## 🧰 Command Arsenal

| Command | What it does | Example |
|---------|-------------|---------|
| `scrape` | Pull reviews from Google Maps | `python main.py scrape "clinic in KL" "klinik in PJ"` |
| `analyze` | Sentiment + topics + insights | `python main.py analyze reviews.parquet -s vader` |
| `full` | Scrape then analyze in one shot | `python main.py full "cafe in Bandung"` |
| `collect` | Batch collector — hours to days | `python main.py collect -q queries.txt -b 3 -d 120` |
| `dashboard` | Launch 6-page Streamlit UI | `python main.py dashboard -p 8080` |
| `export` | Dump everything as CSV | `python main.py export` |
| `generate-queries` | Auto-spawn 332 search terms | `python main.py generate-queries` |
| `stats` | Live collection progress | `python main.py stats` |

### `collect` — The Heavy Lifter

```bash
# One-shot: work through all queries once
python main.py collect -q scraper/queries_full.txt

# 24/7 mode: re-scrape every 6 hours indefinitely
python main.py collect --continuous --cycle-hours 6

# Conservative (safe, slower)
python main.py collect -b 2 -d 180

# Aggressive (fast, riskier)
python main.py collect -b 5 -d 60

# Resume from crash: just run the same command
python main.py collect -q scraper/queries_full.txt --continuous

# Start fresh
python main.py collect --reset
```

| Flag | Default | Description |
|------|---------|-------------|
| `-q` | `scraper/queries.txt` | Query file (one per line) |
| `-b` | `2` | Batch size — queries per Docker run |
| `-d` | `180` | Cooldown between batches (seconds) |
| `-m` | `0` (unlimited) | Stop after N batches |
| `--continuous` | off | Re-run all queries every cycle |
| `--cycle-hours` | `24` | Hours between cycles |
| `--reset` | off | Wipe progress, start fresh |

### `analyze` — Two Sentiment Engines

```bash
# VADER — instant, no GPU, English/Malay
python main.py analyze reviews.parquet -s vader

# XLM-RoBERTa Transformer — multilingual, higher accuracy
python main.py analyze reviews.parquet -s transformer
```

### `generate-queries` — Maximum Coverage

Generates 332 queries across 8+ cities × 25 medical categories (BM + EN), or 500+ queries for broader coverage. Pre-built files included:

| File | Queries | Target |
|------|---------|--------|
| `scraper/queries_100places.txt` | 50 | ~100-200 places, quick run |
| `scraper/queries_full.txt` | 332 | ~500-1,000+ places, comprehensive |
| `scraper/queries_expansion.txt` | 80+ | Additional cities, extra coverage |
| `scraper/queries_ondemand.txt` | Custom | Specific businesses / Google share links |

---

## 📈 The Dashboard — 6 Pages

Launch with `python main.py dashboard`. Opens at **http://localhost:8501**.

| Page | What You See |
|------|-------------|
| **📊 Overview** | Total reviews, place rankings, rating histograms, top/bottom performers |
| **😊 Sentiment** | Positive / negative / neutral breakdowns, per-place sentiment scores |
| **🔍 Aspect Analysis** | What people say about service, price, quality, ambiance, wait time, etc. |
| **🔑 Keywords** | TF-IDF word cloud, LDA topic clusters, top n-gram phrases |
| **⚔️ Comparison** | Side-by-side competitor benchmarking across all metrics |
| **💡 Insights** | Strengths, weaknesses, actionable improvement recommendations |

---

## 🔄 The Collector Engine

```
┌─ CYCLE ─────────────────────────────────────────────────┐
│                                                          │
│  ┌─ BATCH LOOP ──────────────────────────────────────┐  │
│  │                                                    │  │
│  │  1. Pull N queries from queue                      │  │
│  │  2. Spin up Docker scraper    ┌──────────────────┐ │  │
│  │  3. Google Maps → JSON        │  RESUME-ABLE     │ │  │
│  │  4. Parse → parquet           │  Every batch      │ │  │
│  │  5. Save state to JSON        │  saved to disk    │ │  │
│  │  6. Cooldown (120s default)   └──────────────────┘ │  │
│  │  7. Repeat until queue empty                       │  │
│  │                                                    │  │
│  │  Every 10 batches: MERGE + EXPORT CSV              │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  If --continuous: wait N hours → reset queue → repeat    │
└──────────────────────────────────────────────────────────┘
```

**Crash-proof**: progress saved after every single batch. Kill the process, reboot, Ctrl+C — re-run the exact same command and it picks up where it left off.

**State file**: `scraper/collector_state.json` — tracks every query status, timestamps, and counts.

---

## 📁 Architecture

```
GoogleMapScrapper/
│
├── main.py                ╸ CLI hub — 9 commands, argparse-driven
├── config.py              ╸ Settings: scraper limits, aspect cats, NLP models
│
├── scraper/
│   ├── run_scraper.py     ╸ Docker interface to gosom/google-maps-scraper
│   ├── collector.py       ╸ Batch scheduler, merge engine, CSV exporter
│   ├── query_generator.py ╸ Auto-generates 332+ queries across cities
│   ├── queries_*.txt      ╸ Pre-built query files (100 / full / expansion / ondemand)
│   └── collector_state.json ╸ Runtime: progress tracking (3K+ places, 450K+ reviews)
│
├── analytics/
│   ├── preprocess.py      ╸ Text cleaning, tokenization, filtering
│   ├── sentiment.py       ╸ VADER + XLM-RoBERTa, aspect-based scoring
│   ├── topics.py          ╸ TF-IDF, KeyBERT, LDA, n-gram extraction
│   ├── insights.py        ╸ Negative review mining, strengths, recommendations
│   ├── compare.py         ╸ Cross-entity competitor benchmarking
│   └── pipeline.py        ╸ Full orchestrator: raw → insights in one call
│
├── dashboard/
│   └── app.py             ╸ Streamlit 6-page interactive web UI
│
├── data/
│   ├── raw/               ╸ Docker scraper JSON output (745MB+)
│   └── processed/         ╸ Parquet + CSV + JSON analytics (370MB+)
│
├── docker-compose.yml     ╸ Scraper container definition
└── requirements.txt       ╸ Python deps
```

---

## ⚙️ Configuration — `config.py`

### Scraper Tuning

```python
SCRAPER_CONCURRENCY = 4        # Parallel browser tabs
SCRAPER_DEPTH = 15             # Scroll depth per search
SCRAPER_EXTRA_REVIEWS = True   # ~300 reviews per place
SCRAPER_TIMEOUT = 7200         # 2h max per run

# Geo-targeting (optional — set to activate)
SCRAPER_GEO = None             # "lat,lon"
SCRAPER_RADIUS = None          # meters
SCRAPER_GRID_BBOX = None       # "minLat,minLon,maxLat,maxLon"
```

### NLP Pipeline

```python
SENTIMENT_MODEL = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
MAX_REVIEWS_PER_PLACE = 300
```

### Aspect Categories — 9 Dimensions

`service` · `price` · `quality` · `ambiance` · `location` · `wait_time` · `menu_variety` · `portion` · `delivery`

Each with bilingual keywords (EN + BM/ID). Extensible: add your own in `config.py`.

---

## 🔧 Usage Recipes

### Scrape clinics across 10 cities

```bash
python main.py collect -q scraper/queries_full.txt -b 3 -d 120
python main.py analyze data/processed/collected_all_reviews.parquet -s vader
python main.py dashboard
```

### Run 24/7 collector in background

```bash
nohup python main.py collect -q scraper/queries_full.txt --continuous --cycle-hours 6 &
python main.py stats      # check progress
```

### Export everything for Excel / Power BI

```bash
python main.py export
# → data/processed/all_reviews.csv      (all reviews)
# → data/processed/places_summary.csv    (per-place stats)
# → data/processed/sentiment_by_place.csv
# → data/processed/recommendations.csv
# → data/processed/aspect_summary.csv
# → data/processed/comparison_ranking.csv
```

### Target specific competitors

```bash
echo "Klinik Utama Cyberjaya" > targets.txt
echo "Hospital Cyberjaya" >> targets.txt
python main.py full "Klinik Utama Cyberjaya" "Hospital Cyberjaya" "Qualitas SV Care Clinic Cyberjaya"
```

### Use Google Maps share links directly

The scraper now accepts Google Maps share URLs (e.g., `https://share.google/o7WIMNKjt6TIoNzne`) as queries — drop them in `scraper/queries_ondemand.txt` and run.

---

## 🖥️ Scale Guide

| Scale | Places | Reviews | CPU | RAM | Time |
|-------|--------|---------|-----|-----|------|
| **Small** | <30 | <10K | 2 cores | 4GB | 15 min |
| **Medium** | 30-200 | 10K-60K | 4 cores | 8GB | 1-3 hrs |
| **Large** | 200-1,000 | 60K-300K | 8 cores | 16GB | 6-24 hrs |
| **City-wide** | 1,000+ | 300K+ | 16 cores | 32GB | Days |

> **Sentiment**: VADER runs in seconds (even on 100K+ reviews). Transformer needs GPU for large datasets.

---

## 🐛 Troubleshooting

| Problem | Fix |
|---------|-----|
| Docker not running | `sudo systemctl start docker` |
| Only 8 reviews per place | Re-scrape with latest code (bug fixed) |
| Collector crashed | Re-run same command — auto-resumes |
| Google rate limiting | Increase delay: `-d 300`, reduce batch: `-b 2` |
| Memory errors | Close other apps, reduce `-b` to 1 |
| `ModuleNotFoundError` | `pip install sentencepiece tiktoken` (transformer mode) |
| Port 8501 taken | `python main.py dashboard -p 8080` |
| Empty results | Query might be too niche — broaden it |

---

## 📄 License

MIT — see [LICENSE](LICENSE)

## 🙏 Credits

- [gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper) — the Docker scraper engine
- [HuggingFace Transformers](https://huggingface.co/) — XLM-RoBERTa multilingual sentiment
- [Streamlit](https://streamlit.io/) — dashboard framework
- [KeyBERT](https://github.com/MaartenGr/KeyBERT) — keyword extraction
