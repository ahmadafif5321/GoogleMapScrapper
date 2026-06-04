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
SCRAPER_DEPTH = 15
SCRAPER_LANG = "en"
SCRAPER_EXTRA_REVIEWS = True
SCRAPER_EXIT_TIMEOUT = "30m"
SCRAPER_TIMEOUT_SECONDS = 7200

# Scraper: geographic targeting (set to None to disable)
SCRAPER_GEO = None           # "lat,lon" e.g., "2.9221,101.6514" (Cyberjaya)
SCRAPER_RADIUS = None        # meters, e.g., 50000 for 50km radius
SCRAPER_ZOOM = None          # 1-21, e.g., 14 for city-level
SCRAPER_GRID_BBOX = None     # "minLat,minLon,maxLat,maxLon" for grid mode
SCRAPER_GRID_CELL = None     # grid cell size in km (used with grid-bbox)
SCRAPER_FAST_MODE = False    # quick mode: 21 results per query, basic fields only


# ---- Maximum Data Collection Presets ----
# Uncomment and set these to max out data:
#
# For a city-wide scan (grid mode - MOST data):
#   SCRAPER_GRID_BBOX = "minLat,minLon,maxLat,maxLon"
#   SCRAPER_GRID_CELL = 1.0  # 1km cells
#   SCRAPER_ZOOM = 16        # high zoom per cell
#   SCRAPER_DEPTH = 5        # depth per cell
#
# For a radius scan (simpler):
#   SCRAPER_GEO = "2.9221,101.6514"     # center point
#   SCRAPER_RADIUS = 50000              # 50km radius
#   SCRAPER_ZOOM = 14                   # city zoom
#   SCRAPER_DEPTH = 10                  # max scroll depth
#
# For multiple keywords in same area:
#   Add more queries: "clinic in Cyberjaya", "doctor in Cyberjaya",
#   "hospital in Cyberjaya", "medical center in Cyberjaya", etc.

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
