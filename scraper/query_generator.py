"""
Query Generator - creates comprehensive query lists for maximum place coverage.
Supports grid-based area splitting, keyword variations, and multi-area coverage.
"""
from pathlib import Path

QUERIES_FILE = Path(__file__).resolve().parent / "queries.txt"


def generate_area_variations(
    keywords: list[str],
    areas: list[str],
    include_radius: bool = True,
) -> list[str]:
    """
    Generate query combinations: keyword + area.

    Example:
        keywords=["clinic", "hospital"], areas=["Cyberjaya", "Putrajaya"]
        -> ["clinic in Cyberjaya", "hospital in Cyberjaya", ...]
    """
    queries = []
    for area in areas:
        for kw in keywords:
            queries.append(f"{kw} in {area}")
    return queries


def generate_grid_queries(
    keyword: str,
    min_lat: float, min_lon: float,
    max_lat: float, max_lon: float,
    grid_size: float = 0.02,  # ~2km
) -> list[str]:
    """
    Generate queries for a grid of points covering a bounding box.
    Each grid point becomes a separate geo-targeted search.

    Args:
        grid_size: degrees between points (0.01 ≈ 1.1km, 0.02 ≈ 2.2km)
    """
    queries = []
    lat = min_lat
    while lat <= max_lat:
        lon = min_lon
        while lon <= max_lon:
            queries.append(f"{keyword} @{lat:.5f},{lon:.5f},14z")
            lon += grid_size
        lat += grid_size
    return queries


def generate_clinic_queries_cyberjaya() -> list[str]:
    """
    Generate ~100+ queries for clinics in Cyberjaya and surrounding areas.
    This maximizes coverage for the user's existing clinic comparison use case.
    """
    keywords = [
        "clinic",
        "klinik",
        "hospital",
        "medical clinic",
        "doctor",
        "dental clinic",
        "klinik gigi",
        "klinik kesihatan",
        "pharmacy",
        "health clinic",
        "klinik 24 jam",
        "specialist clinic",
        "klinik pakar",
        "family clinic",
        "klinik keluarga",
        "medical centre",
        "pusat perubatan",
        "child specialist clinic",
        "klinik kanak kanak",
        "women clinic",
        "klinik wanita",
        "physiotherapy",
        "fisioterapi",
        "diagnostic centre",
        "pusat diagnostik",
    ]

    areas = [
        "Cyberjaya",
        "Putrajaya",
        "Dengkil",
        "Bangi",
        "Kajang",
        "Seri Kembangan",
        "Puchong",
        "Serdang",
        "Bandar Baru Bangi",
        "Sepang",
        "Putra Heights",
        "Subang Jaya",
    ]

    queries = generate_area_variations(keywords, areas)
    return queries


def write_queries_file(queries: list[str], filepath: Path = QUERIES_FILE):
    """Write queries to file with comments."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        f.write("# Google Maps Scraper Queries\n")
        f.write(f"# Auto-generated: {len(queries)} queries\n")
        f.write("# Lines starting with # are ignored\n\n")
        for q in queries:
            f.write(q + "\n")
    print(f"[queries] Wrote {len(queries)} queries to {filepath}")


def generate_max_coverage(area_center: str = "Cyberjaya", radius_km: int = 30):
    """
    Generate maximum coverage queries for a given area.
    Combines keyword variations + area variations + geo-targeted searches.
    """
    queries = generate_clinic_queries_cyberjaya()

    # Add geo-targeted circular searches at different zoom levels
    geo_centers = [
        "2.9221,101.6514",  # Cyberjaya center
        "2.9313,101.6879",  # Putrajaya center
        "2.8730,101.6874",  # Dengkil
        "2.9031,101.7870",  # Bangi
        "2.9930,101.7890",  # Kajang
        "3.0063,101.7066",  # Seri Kembangan
        "3.0253,101.6178",  # Puchong
        "2.9761,101.7000",  # Serdang
    ]

    # One geo-targeted query per center using the Google Maps "@lat,lon,zoom" syntax
    # (the previous radius loop produced 4 identical strings per center).
    for geo in geo_centers:
        lat, lon = geo.split(",")
        queries.append(f"clinic @{lat},{lon},14z")

    # De-duplicate while preserving order
    seen = set()
    unique_queries = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique_queries.append(q)

    return unique_queries


NICHE_KEYWORDS = {
    "fnb": ["restaurant", "cafe", "kopitiam", "kedai makan", "mamak",
            "nasi kandar", "coffee shop", "bakery", "western food", "bubble tea"],
    "automotive": ["car workshop", "kedai kereta", "tyre shop", "car wash",
                   "car detailing", "motorcycle workshop", "car service centre",
                   "bengkel kereta", "car battery shop", "car aircond service"],
    "beauty": ["hair salon", "barbershop", "kedai gunting rambut", "spa",
               "massage", "beauty salon", "facial", "nail salon", "urut"],
    "hotel": ["hotel", "homestay", "budget hotel", "guest house", "resort"],
    "retail": ["mini market", "grocery store", "pharmacy", "hardware shop",
               "pet shop", "mobile phone shop"],
    "education": ["tuition centre", "tadika", "kindergarten", "daycare",
                  "driving school", "music school"],
    "fitness": ["gym", "fitness centre", "badminton court", "futsal court",
                "yoga studio"],
    "services": ["laundry", "dobi", "aircond service", "renovation contractor",
                 "printing shop", "photography studio"],
}

DEFAULT_AREAS = [
    "Cyberjaya", "Putrajaya", "Dengkil", "Bangi", "Kajang",
    "Seri Kembangan", "Puchong", "Serdang", "Bandar Baru Bangi",
    "Sepang", "Putra Heights", "Subang Jaya",
]


def generate_expansion_queries(niches: list[str] | None = None,
                               areas: list[str] | None = None) -> list[str]:
    """Multi-niche expansion pack: every niche keyword x every area."""
    niches = niches or list(NICHE_KEYWORDS.keys())
    areas = areas or DEFAULT_AREAS
    queries = []
    for niche in niches:
        queries.extend(generate_area_variations(NICHE_KEYWORDS[niche], areas))
    # de-dup preserving order
    seen, out = set(), []
    for q in queries:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "expansion":
        queries = generate_expansion_queries()
        write_queries_file(queries,
                           Path(__file__).resolve().parent / "queries_expansion.txt")
        print(f"Generated {len(queries)} expansion queries "
              f"({len(NICHE_KEYWORDS)} niches x {len(DEFAULT_AREAS)} areas).")
        sys.exit(0)
    queries = generate_max_coverage()
    write_queries_file(queries)
    print(f"Generated {len(queries)} queries.")
    print(f"Estimated coverage: {len(queries) * 20} places (min)")
    print(f"Estimated reviews: {len(queries) * 20 * 100} (avg)")
