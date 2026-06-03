# 🗺️ Google Maps Review Analytics

> End-to-end system for scraping Google Maps reviews, performing multilingual sentiment analysis, aspect-based analytics, and generating actionable improvement recommendations — all with an interactive Streamlit dashboard.

## 📊 Features

### Phase 1 — Scraping
- Uses [gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper) via Docker
- Scrapes places and reviews (up to 300 per place with `-extra-reviews`)
- Outputs JSON/CSV → parsed into structured DataFrames

### Phase 2 — Analytics Engine
- Text preprocessing & cleaning (multilingual support)
- Keyword extraction (TF-IDF + KeyBERT)
- Topic modeling (LDA)
- N-gram phrase frequency analysis

### Phase 3 — Sentiment Analysis
- **Multilingual**: Transformer-based (`xlm-roberta-base-sentiment`) for 8+ languages
- **Fast mode**: VADER for English-only quick analysis
- **Aspect-based sentiment**: 9 predefined categories (service, price, quality, ambiance, location, wait_time, menu_variety, portion, delivery)

### Phase 4 — Insights & Recommendations
- Negative review deep-dive analysis
- Auto-generated improvement roadmap (critical/high/medium/low severity)
- Strength identification from positive reviews
- Competitor comparison & competitive advantage detection

### Dashboard (Streamlit)
- 📊 **Overview** — Summary stats, place rankings, rating distribution
- 😊 **Sentiment Analysis** — Sentiment pie charts, by-place breakdown, sample reviews
- 🔍 **Aspect Analysis** — What customers mention most, positive/negative per aspect
- 🔑 **Keywords & Topics** — Word cloud, topic modeling (LDA), keyword-sentiment correlation
- ⚔️ **Competitor Comparison** — Side-by-side benchmarking, competitive advantages
- 💡 **Insights & Recommendations** — Prioritized improvement roadmap, exportable as CSV

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Docker (for scraping)

### Install

```bash
git clone https://github.com/ahmadafif5321/GoogleMapScrapper.git
cd GoogleMapScrapper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Usage

```bash
# 1. Scrape Google Maps reviews (requires Docker)
python main.py scrape "coffee shop in Jakarta, Indonesia" "restaurant in Bandung, Indonesia"

# 2. Run analytics on scraped data
python main.py analyze data/processed/results_reviews.parquet

# With multilingual transformer sentiment (for non-English reviews):
python main.py analyze data/processed/results_reviews.parquet -s transformer

# 3. Launch interactive dashboard
python main.py dashboard

# 4. Or run everything in one command
python main.py full "restaurant in Kuala Lumpur, Malaysia"
```

Open **http://localhost:8501** for the dashboard.

## 📁 Project Structure

```
GoogleMapScrapper/
├── main.py                     # CLI entry point (scrape / analyze / dashboard / full)
├── config.py                   # All configuration & aspect categories
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Dockerized scraper config
├── scraper/
│   ├── run_scraper.py          # Docker-based Google Maps scraper wrapper
│   └── queries.txt             # Place search queries input
├── analytics/
│   ├── preprocess.py           # Text cleaning, tokenization, NLTK pipeline
│   ├── sentiment.py            # Multilingual sentiment + aspect-based analysis
│   ├── topics.py               # TF-IDF, KeyBERT, LDA topic modeling, n-grams
│   ├── insights.py             # Negative review analysis, strengths, recommendations
│   ├── compare.py              # Cross-place competitor comparison
│   └── pipeline.py             # Full analytics orchestrator
├── dashboard/
│   └── app.py                  # Streamlit 6-page interactive dashboard
└── data/
    ├── raw/                    # Raw scraper JSON output
    └── processed/              # Processed parquet files + analysis JSON
```

## 🔧 Configuration

Edit `config.py` to customize:

| Setting | Default | Description |
|---------|---------|-------------|
| `SCRAPER_CONCURRENCY` | 4 | Parallel scrape jobs |
| `SCRAPER_DEPTH` | 2 | Scroll depth for results |
| `SCRAPER_LANG` | `en` | Search language |
| `SENTIMENT_MODEL` | `xlm-roberta-base-sentiment` | Transformer model |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | KeyBERT embeddings |
| `ASPECT_CATEGORIES` | 9 categories | Customizable aspect keywords (English + Indonesian/Malay) |

## 📤 Output Files

| File | Description |
|------|-------------|
| `data/raw/results.json` | Raw scraper output (JSONL) |
| `data/processed/*_reviews.parquet` | Extracted reviews DataFrame |
| `data/processed/*_analyzed.parquet` | Fully analyzed reviews with sentiment |
| `data/processed/*_results.json` | Complete analysis (sentiment, topics, insights, comparison) |

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Phase 1   │────▶│   Phase 2 & 3    │────▶│    Phase 4      │
│  Scraping   │     │  NLTK + Sentiment│     │  Insights +     │
│  (Docker)   │     │  + Topic Models  │     │  Comparison     │
└─────────────┘     └──────────────────┘     └─────────────────┘
                                                      │
                                                      ▼
                                            ┌─────────────────┐
                                            │   Streamlit     │
                                            │   Dashboard     │
                                            └─────────────────┘
```

## 📋 Example Output

```
Total Reviews: 213
Total Places: 27
Avg Rating: 4.69

Top 3 Improvement Recommendations:
  [CRITICAL] Improve Staff Service Quality
  [CRITICAL] Reduce Wait Times
  [CRITICAL] Enhance Product/Service Quality
```

## 🛠️ Tech Stack

- **Scraping**: gosom/google-maps-scraper (Go/Docker)
- **NLP**: NLTK, spaCy, Transformers (HuggingFace)
- **Embeddings**: Sentence-Transformers
- **Topic Modeling**: scikit-learn LDA, KeyBERT
- **Dashboard**: Streamlit + Plotly
- **Data**: Pandas, NumPy, PyArrow (Parquet)

## 📄 License

MIT License

## 🙏 Credits

- [gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper) — The underlying Google Maps scraper
- [HuggingFace Transformers](https://huggingface.co/) — Multilingual sentiment models
