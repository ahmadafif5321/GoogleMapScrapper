"""
Google Maps Scraper & Review Analytics - Configuration
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

for d in [DATA_DIR, RAW_DIR, PROCESSED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ---- Scraper Settings ----
SCRAPER_DOCKER_IMAGE = "gosom/google-maps-scraper:latest"
SCRAPER_CONCURRENCY = 4
SCRAPER_DEPTH = 2
SCRAPER_LANG = "en"
SCRAPER_EXTRA_REVIEWS = True
SCRAPER_EXIT_TIMEOUT = "5m"
SCRAPER_TIMEOUT_SECONDS = 600

# ---- Analytics Settings ----
SENTIMENT_MODEL = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
USE_GPU = False
BATCH_SIZE = 16
MAX_REVIEWS_PER_PLACE = 300
MIN_REVIEW_LENGTH = 5

# ---- Topic/Aspect Categories ----
ASPECT_CATEGORIES = {
    "service": ["service", "staff", "waiter", "waitress", "employee", "manager", "owner", "customer service",
                "hospitality", "friendly", "rude", "attentive", "helpful", "pelayanan", "pegawai", "karyawan"],
    "price": ["price", "expensive", "cheap", "affordable", "overpriced", "worth", "value", "cost", "murah",
              "mahal", "harga", "terjangkau"],
    "quality": ["quality", "taste", "delicious", "tasty", "fresh", "good", "excellent", "terrible", "bad",
                "amazing", "wonderful", "perfect", "enak", "lezat", "segar", "buruk", "bagus"],
    "ambiance": ["ambiance", "atmosphere", "decor", "interior", "design", "vibe", "music", "noise", "noisy",
                 "quiet", "clean", "dirty", "crowded", "cozy", "comfortable", "suasana", "tempat", "bersih",
                 "kotor", "ramai", "nyaman"],
    "location": ["location", "parking", "access", "traffic", "distance", "area", "neighborhood",
                 "lokasi", "parkir", "akses", "dekat", "jauh"],
    "wait_time": ["wait", "waiting", "queue", "line", "slow", "fast", "quick", "long", "minutes", "hours",
                  "tunggu", "lama", "cepat", "antri", "antrian"],
    "menu_variety": ["menu", "variety", "choice", "options", "selection", "options", "vegan", "vegetarian",
                     "halal", "pilihan", "variasi", "menu makanan"],
    "portion": ["portion", "size", "small", "large", "big", "porsi", "besar", "kecil"],
    "delivery": ["delivery", "takeout", "takeaway", "pickup", "online", "order", "grab", "gojek",
                 "pesan", "antar", "bungkus"],
}

# ---- Dashboard Settings ----
DASHBOARD_TITLE = "Google Maps Review Analytics"
DASHBOARD_PORT = 8501
