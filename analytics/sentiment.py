"""
Phase 3: Multilingual Sentiment Analysis
Uses transformer models for cross-lingual sentiment.
"""
import pandas as pd
import numpy as np
from typing import Tuple, List
from collections import defaultdict

from config import SENTIMENT_MODEL, BATCH_SIZE, USE_GPU, ASPECT_CATEGORIES

_SENTIMENT_PIPELINE = None
_ENGLISH_SENTIMENT = None


def _get_multilingual_pipeline():
    """Lazy-load the multilingual sentiment pipeline."""
    global _SENTIMENT_PIPELINE
    if _SENTIMENT_PIPELINE is None:
        from transformers import pipeline
        device = 0 if USE_GPU else -1
        print(f"[sentiment] Loading multilingual model: {SENTIMENT_MODEL} ...")
        _SENTIMENT_PIPELINE = pipeline(
            "sentiment-analysis",
            model=SENTIMENT_MODEL,
            tokenizer=SENTIMENT_MODEL,
            device=device,
            max_length=512,
            truncation=True,
        )
        print("[sentiment] Model loaded.")
    return _SENTIMENT_PIPELINE


def _get_english_sentiment():
    """Lazy-load VADER for fast English-only sentiment."""
    global _ENGLISH_SENTIMENT
    if _ENGLISH_SENTIMENT is None:
        from nltk.sentiment import SentimentIntensityAnalyzer
        import nltk
        try:
            nltk.data.find("sentiment/vader_lexicon.zip")
        except LookupError:
            nltk.download("vader_lexicon", quiet=True)
        _ENGLISH_SENTIMENT = SentimentIntensityAnalyzer()
    return _ENGLISH_SENTIMENT


def analyze_sentiment_transformer(texts: List[str]) -> List[dict]:
    """Run multilingual transformer sentiment on a list of texts."""
    pipe = _get_multilingual_pipeline()
    results = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        batch_results = pipe(batch)
        results.extend(batch_results)
    return results


def analyze_sentiment_vader(texts: List[str]) -> List[dict]:
    """Run VADER sentiment (English only, fast)."""
    sia = _get_english_sentiment()
    results = []
    for text in texts:
        scores = sia.polarity_scores(str(text))
        compound = scores["compound"]
        if compound >= 0.05:
            label, score = "positive", compound
        elif compound <= -0.05:
            label, score = "negative", abs(compound)
        else:
            label, score = "neutral", compound
        results.append({"label": label, "score": float(score)})
    return results


def run_sentiment_analysis(df: pd.DataFrame, method: str = "transformer") -> pd.DataFrame:
    """
    Add sentiment columns to the review DataFrame.

    Args:
        df: DataFrame with 'clean_text' column
        method: 'transformer' (multilingual, slower) or 'vader' (English, fast)

    Returns:
        DataFrame with added columns: sentiment, sentiment_score, sentiment_label_num
    """
    if df.empty:
        return df

    df = df.copy()
    texts = df["clean_text"].tolist()

    if method == "transformer":
        results = analyze_sentiment_transformer(texts)
    else:
        results = analyze_sentiment_vader(texts)

    df["sentiment"] = [r["label"] for r in results]
    df["sentiment_score"] = [r["score"] for r in results]

    label_map = {"positive": 1, "neutral": 0, "negative": -1}
    df["sentiment_label_num"] = df["sentiment"].map(label_map).fillna(0).astype(int)

    sentiment_counts = df["sentiment"].value_counts().to_dict()
    print(f"[sentiment] Analysis complete: {sentiment_counts}")

    return df


def get_sentiment_summary(df: pd.DataFrame) -> dict:
    """Get summary sentiment statistics grouped by place."""
    if "sentiment" not in df.columns:
        return {}

    summary = df.groupby("place_name").agg(
        total_reviews=("sentiment", "count"),
        positive_pct=("sentiment", lambda x: (x == "positive").mean() * 100),
        neutral_pct=("sentiment", lambda x: (x == "neutral").mean() * 100),
        negative_pct=("sentiment", lambda x: (x == "negative").mean() * 100),
        avg_sentiment_score=("sentiment_score", "mean"),
        avg_review_rating=("review_rating", "mean"),
    ).round(2).sort_values("positive_pct", ascending=False)

    return summary.to_dict("index")


def analyze_aspect_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aspect-Based Sentiment Analysis.
    Matches review keywords against predefined aspect categories and assigns
    sentiment to each aspect mentioned.
    """
    if df.empty or "tokens" not in df.columns:
        return df

    df = df.copy()

    for aspect, keywords in ASPECT_CATEGORIES.items():
        keyword_set = set(keywords)
        df[f"aspect_{aspect}"] = df["tokens"].apply(
            lambda tokens: len(set(tokens) & keyword_set) > 0 if tokens else False
        )

    aspect_cols = [f"aspect_{c}" for c in ASPECT_CATEGORIES]
    df["aspects_mentioned"] = df[aspect_cols].sum(axis=1)

    return df


def get_aspect_summary(df: pd.DataFrame) -> dict:
    """Summarize which aspects are mentioned most and their sentiment."""
    if df.empty:
        return {}

    summary = {}
    for aspect in ASPECT_CATEGORIES:
        col = f"aspect_{aspect}"
        if col not in df.columns:
            continue

        mentioned = df[df[col]]
        if mentioned.empty:
            summary[aspect] = {
                "total_mentions": 0,
                "positive_pct": 0,
                "negative_pct": 0,
                "avg_sentiment": 0,
                "sample_reviews": [],
            }
            continue

        sentiments = mentioned["sentiment"].value_counts(normalize=True) * 100

        sample_neg = mentioned[mentioned["sentiment"] == "negative"]["clean_text"].head(3).tolist()
        sample_pos = mentioned[mentioned["sentiment"] == "positive"]["clean_text"].head(3).tolist()

        summary[aspect] = {
            "total_mentions": len(mentioned),
            "mention_rate": round(len(mentioned) / len(df) * 100, 1),
            "positive_pct": round(sentiments.get("positive", 0), 1),
            "negative_pct": round(sentiments.get("negative", 0), 1),
            "neutral_pct": round(sentiments.get("neutral", 0), 1),
            "avg_sentiment_score": round(mentioned["sentiment_score"].mean(), 3),
            "avg_rating": round(mentioned["review_rating"].mean(), 2),
            "sample_negative": sample_neg,
            "sample_positive": sample_pos,
        }

    return summary


def get_place_aspect_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Compare aspects across different places."""
    rows = []
    aspect_cols = [f"aspect_{c}" for c in ASPECT_CATEGORIES]

    for place in df["place_name"].unique():
        place_df = df[df["place_name"] == place]
        for aspect in ASPECT_CATEGORIES:
            col = f"aspect_{aspect}"
            if col not in place_df.columns:
                continue
            mentioned = place_df[place_df[col]]
            rows.append({
                "place_name": place,
                "aspect": aspect,
                "mentions": len(mentioned),
                "mention_rate": round(len(mentioned) / len(place_df) * 100, 1),
                "positive_pct": round((mentioned["sentiment"] == "positive").mean() * 100, 1) if len(mentioned) > 0 else 0,
                "negative_pct": round((mentioned["sentiment"] == "negative").mean() * 100, 1) if len(mentioned) > 0 else 0,
                "avg_sentiment": round(mentioned["sentiment_score"].mean(), 3) if len(mentioned) > 0 else 0,
            })

    return pd.DataFrame(rows)
