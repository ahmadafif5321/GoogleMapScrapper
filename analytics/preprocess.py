"""
Phase 2: Text Preprocessing & Cleaning
Cleans and normalizes review text for downstream analysis.
"""
import re
import unicodedata
import pandas as pd
from typing import List

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

from config import PROCESSED_DIR, MIN_REVIEW_LENGTH

NLTK_RESOURCES = ["stopwords", "punkt", "punkt_tab", "averaged_perceptron_tagger", "wordnet"]

for resource in NLTK_RESOURCES:
    try:
        nltk.data.find(f"tokenizers/{resource}" if resource == "punkt" else
                       f"corpora/{resource}" if resource == "stopwords" else
                       f"taggers/{resource}" if resource == "averaged_perceptron_tagger" else
                       f"corpora/{resource}")
    except LookupError:
        nltk.download(resource, quiet=True)

STOP_WORDS = set(stopwords.words("english"))
try:
    STOP_WORDS.update(set(stopwords.words("indonesian")))
except LookupError:
    pass


def clean_text(text: str) -> str:
    """Clean a single review text."""
    if not isinstance(text, str) or not text.strip():
        return ""

    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"http\S+|www\S+|https\S+", "", text)
    text = re.sub(r"\S+@\S+", "", text)
    # Keep word chars, whitespace, common punctuation, and Arabic/Thai/CJK/
    # Japanese kana/Hangul ranges; strip everything else (emoji, symbols).
    text = re.sub(
        r"[^\w\s.,!?;:'\"\-()&%$#@"
        r"\u0600-\u06ff\u0e00-\u0e7f\u4e00-\u9fff"
        r"\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]",
        "", text,
    )
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text


def tokenize_text(text: str, remove_stopwords: bool = True) -> List[str]:
    """Tokenize and optionally remove stopwords."""
    try:
        tokens = word_tokenize(text.lower())
    except Exception:
        tokens = text.lower().split()

    tokens = [t for t in tokens if len(t) > 1]
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOP_WORDS and not t.isdigit()]

    return tokens


def preprocess_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess review DataFrame: clean, filter, tokenize.

    Expected columns: review_text, place_name, place_id, review_rating, etc.
    """
    if df.empty:
        return df

    df = df.copy()

    df["clean_text"] = df["review_text"].apply(clean_text)
    df = df[df["clean_text"].str.len() >= MIN_REVIEW_LENGTH].reset_index(drop=True)
    df["tokens"] = df["clean_text"].apply(lambda x: tokenize_text(x, remove_stopwords=True))
    df["token_count"] = df["tokens"].apply(len)
    df["word_count"] = df["clean_text"].apply(lambda x: len(x.split()))
    df["review_length_bucket"] = pd.cut(
        df["word_count"],
        bins=[0, 10, 30, 50, 100, 500, 10000],
        labels=["very_short", "short", "medium", "long", "very_long", "extremely_long"]
    )

    print(f"[preprocess] Cleaned {len(df)} reviews "
          f"(avg {df['word_count'].mean():.0f} words, {df['token_count'].mean():.0f} tokens)")

    return df


def load_and_preprocess(parquet_path: str) -> pd.DataFrame:
    """Load reviews from parquet and run full preprocessing."""
    df = pd.read_parquet(PROCESSED_DIR / parquet_path)
    return preprocess_reviews(df)


def get_review_stats(df: pd.DataFrame) -> dict:
    """Get summary statistics about the reviews."""
    stats = {
        "total_reviews": len(df),
        "total_places": df["place_name"].nunique(),
        "avg_rating": round(df["review_rating"].mean(), 2),
        "avg_word_count": round(df["word_count"].mean(), 1),
        "rating_distribution": df["review_rating"].value_counts().sort_index().to_dict(),
        "places_ranked": df.groupby("place_name").agg(
            reviews=("review_text", "count"),
            avg_rating=("review_rating", "mean"),
        ).sort_values("reviews", ascending=False).to_dict("index"),
    }
    return stats
