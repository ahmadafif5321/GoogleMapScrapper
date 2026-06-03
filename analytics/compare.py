"""
Competitor Comparison Module
Compares multiple places side-by-side on sentiment, aspects, keywords, and ratings.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class PlaceComparison:
    place_name: str
    total_reviews: int = 0
    avg_rating: float = 0.0
    positive_pct: float = 0.0
    neutral_pct: float = 0.0
    negative_pct: float = 0.0
    avg_sentiment_score: float = 0.0
    top_keywords: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    aspect_scores: Dict[str, float] = field(default_factory=dict)


def compare_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare sentiment metrics across all places.
    """
    if "sentiment" not in df.columns:
        return pd.DataFrame()

    comparison = df.groupby("place_name").agg(
        total_reviews=("sentiment", "count"),
        positive_pct=("sentiment", lambda x: (x == "positive").mean() * 100),
        neutral_pct=("sentiment", lambda x: (x == "neutral").mean() * 100),
        negative_pct=("sentiment", lambda x: (x == "negative").mean() * 100),
        avg_sentiment_score=("sentiment_score", "mean"),
        avg_review_rating=("review_rating", "mean"),
        sentiment_label_avg=("sentiment_label_num", "mean"),
    ).round(2)

    comparison["sentiment_health_score"] = (
        comparison["positive_pct"] * 0.6 +
        (100 - comparison["negative_pct"]) * 0.4
    ).round(1)

    comparison = comparison.sort_values("sentiment_health_score", ascending=False)

    return comparison


def compare_aspects(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare aspect-based metrics across places.
    Shows what each place is good/bad at.
    """
    from config import ASPECT_CATEGORIES

    rows = []
    for place in df["place_name"].unique():
        place_df = df[df["place_name"] == place]
        for aspect in ASPECT_CATEGORIES:
            col = f"aspect_{aspect}"
            if col not in place_df.columns:
                continue
            mentioned = place_df[place_df[col]]
            if "sentiment" in place_df.columns:
                pos_pct = (mentioned["sentiment"] == "positive").mean() * 100 if len(mentioned) > 0 else 0
                neg_pct = (mentioned["sentiment"] == "negative").mean() * 100 if len(mentioned) > 0 else 0
            else:
                pos_pct = 0
                neg_pct = 0

            rows.append({
                "place_name": place,
                "aspect": aspect,
                "mentions": len(mentioned),
                "mention_rate_pct": round(len(mentioned) / max(len(place_df), 1) * 100, 1),
                "positive_pct": round(pos_pct, 1),
                "negative_pct": round(neg_pct, 1),
                "net_sentiment": round(pos_pct - neg_pct, 1),
            })

    return pd.DataFrame(rows)


def compare_keywords(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Compare top keywords unique to each place.
    """
    from analytics.topics import extract_keywords_per_place

    place_keywords = extract_keywords_per_place(df, method="tfidf")

    rows = []
    for place, keywords in place_keywords.items():
        for kw, score in keywords[:top_n]:
            rows.append({
                "place_name": place,
                "keyword": kw,
                "score": round(score, 3),
            })

    return pd.DataFrame(rows)


def compute_competitive_advantages(df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Identify what each place does better than competitors.
    """
    aspect_comparison = compare_aspects(df)

    if aspect_comparison.empty:
        return {}

    advantages = {}
    for aspect in aspect_comparison["aspect"].unique():
        aspect_df = aspect_comparison[aspect_comparison["aspect"] == aspect]
        if aspect_df.empty or aspect_df["net_sentiment"].std() == 0:
            continue

        best_place = aspect_df.loc[aspect_df["net_sentiment"].idxmax()]
        if best_place["net_sentiment"] > 10 and best_place["mentions"] >= 3:
            place_name = best_place["place_name"]
            if place_name not in advantages:
                advantages[place_name] = []
            advantages[place_name].append(aspect)

    return advantages


def generate_comparison_report(df: pd.DataFrame) -> Dict:
    """
    Generate a full comparison report.
    """
    sentiment_comp = compare_sentiment(df)
    aspect_comp = compare_aspects(df)
    advantages = compute_competitive_advantages(df)

    rankings = {}
    if not sentiment_comp.empty:
        for idx, (place, row) in enumerate(sentiment_comp.iterrows()):
            rankings[place] = {
                "rank": idx + 1,
                "sentiment_health_score": row["sentiment_health_score"],
                "positive_pct": row["positive_pct"],
                "negative_pct": row["negative_pct"],
                "avg_rating": row["avg_review_rating"],
                "total_reviews": row["total_reviews"],
            }

    aspect_summary = {}
    if not aspect_comp.empty:
        for aspect in aspect_comp["aspect"].unique():
            subset = aspect_comp[aspect_comp["aspect"] == aspect]
            best = subset.loc[subset["net_sentiment"].idxmax()]
            worst = subset.loc[subset["net_sentiment"].idxmin()]
            aspect_summary[aspect] = {
                "best_place": best["place_name"],
                "best_score": best["net_sentiment"],
                "worst_place": worst["place_name"],
                "worst_score": worst["net_sentiment"],
            }

    return {
        "rankings": rankings,
        "aspect_summary": aspect_summary,
        "competitive_advantages": advantages,
        "sentiment_comparison": sentiment_comp.to_dict("index") if not sentiment_comp.empty else {},
        "aspect_comparison": aspect_comp.to_dict("records") if not aspect_comp.empty else [],
    }
