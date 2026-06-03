"""
Phase 4: Insights & Improvement Recommendations
Analyzes negative reviews to identify improvement areas and generates
actionable recommendations based on sentiment patterns.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from collections import Counter

from config import ASPECT_CATEGORIES


def analyze_negative_reviews(df: pd.DataFrame, min_reviews: int = 3) -> Dict:
    """
    Deep-dive into negative reviews to find patterns and pain points.

    Returns:
        Dict with complaint categories, keywords, and sample reviews.
    """
    if df.empty or "sentiment" not in df.columns:
        return {}

    negative = df[df["sentiment"] == "negative"].copy()
    if len(negative) < min_reviews:
        return {"error": f"Not enough negative reviews (found {len(negative)}, need {min_reviews})"}

    complaint_aspects = {}
    for aspect, keywords in ASPECT_CATEGORIES.items():
        col = f"aspect_{aspect}"
        if col not in negative.columns:
            continue
        aspect_neg = negative[negative[col]]
        if len(aspect_neg) == 0:
            continue

        tokens_all = []
        for tokens in aspect_neg["tokens"]:
            if isinstance(tokens, list):
                tokens_all.extend(tokens)
        token_freq = Counter(tokens_all).most_common(15)

        neg_pct = round(len(aspect_neg) / len(negative) * 100, 1)
        total_neg_pct = round(len(aspect_neg) / len(df) * 100, 1)

        complaint_aspects[aspect] = {
            "count": len(aspect_neg),
            "pct_of_negative_reviews": neg_pct,
            "pct_of_all_reviews": total_neg_pct,
            "avg_rating": round(aspect_neg["review_rating"].mean(), 2),
            "top_keywords": token_freq,
            "sample_complaints": aspect_neg["clean_text"].head(5).tolist(),
        }

    sorted_complaints = sorted(
        complaint_aspects.items(),
        key=lambda x: x[1]["count"],
        reverse=True,
    )

    return {
        "total_negative_reviews": len(negative),
        "negative_pct": round(len(negative) / len(df) * 100, 1),
        "avg_negative_rating": round(negative["review_rating"].mean(), 2),
        "complaint_categories": dict(sorted_complaints),
    }


def generate_recommendations(complaint_analysis: Dict) -> List[Dict]:
    """
    Generate actionable improvement recommendations from complaint analysis.

    Returns:
        List of recommendation dicts with category, severity, and action items.
    """
    if "complaint_categories" not in complaint_analysis:
        return []

    recommendations = []
    categories = complaint_analysis.get("complaint_categories", {})

    recommendation_templates = {
        "service": {
            "title": "Improve Staff Service Quality",
            "actions": [
                "Implement regular customer service training for staff",
                "Set up a feedback system to track staff performance",
                "Consider mystery shopper programs to audit service quality",
                "Establish clear service standards and response protocols",
            ],
        },
        "price": {
            "title": "Review Pricing Strategy",
            "actions": [
                "Benchmark prices against top competitors in the area",
                "Create value meal/package options for budget-conscious customers",
                "Clearly communicate price-value proposition on menu/listings",
                "Consider loyalty programs or discounts for repeat customers",
            ],
        },
        "quality": {
            "title": "Enhance Product/Service Quality",
            "actions": [
                "Audit current quality control processes",
                "Source higher-quality ingredients/materials",
                "Implement quality checkpoints before serving/delivering",
                "Gather real-time quality feedback from customers",
            ],
        },
        "ambiance": {
            "title": "Upgrade Atmosphere & Environment",
            "actions": [
                "Assess cleanliness and maintenance schedules",
                "Consider interior design improvements or renovation",
                "Manage noise levels and music selection",
                "Ensure comfortable temperature and lighting",
            ],
        },
        "location": {
            "title": "Address Location & Accessibility Issues",
            "actions": [
                "Improve signage and directions to the location",
                "Partner with nearby parking facilities or add valet service",
                "Highlight accessibility features on online listings",
                "Consider offering delivery/pickup if not already available",
            ],
        },
        "wait_time": {
            "title": "Reduce Wait Times",
            "actions": [
                "Implement online ordering/reservation system",
                "Optimize kitchen/fulfillment workflow",
                "Add staff during peak hours",
                "Provide estimated wait times and comfortable waiting area",
            ],
        },
        "menu_variety": {
            "title": "Expand Menu/Product Variety",
            "actions": [
                "Survey customers about desired menu items/products",
                "Add seasonal or limited-time offerings",
                "Include dietary-specific options (vegan, gluten-free, halal)",
                "Rotate menu items to keep offerings fresh",
            ],
        },
        "portion": {
            "title": "Adjust Portion Sizes",
            "actions": [
                "Review portion sizes against customer expectations",
                "Offer multiple size options (small/regular/large)",
                "Ensure consistency in portioning across all orders",
                "Consider combo/family-size options for groups",
            ],
        },
        "delivery": {
            "title": "Improve Delivery & Takeout Experience",
            "actions": [
                "Partner with reliable delivery platforms",
                "Improve packaging to maintain food/product quality during transit",
                "Set accurate delivery time estimates",
                "Implement order tracking for customers",
            ],
        },
    }

    for aspect, data in sorted(categories.items(), key=lambda x: x[1]["count"], reverse=True):
        severity = "critical" if data["pct_of_negative_reviews"] > 20 else \
                   "high" if data["pct_of_negative_reviews"] > 10 else \
                   "medium" if data["pct_of_negative_reviews"] > 5 else "low"

        template = recommendation_templates.get(aspect, {
            "title": f"Address issues related to: {aspect}",
            "actions": [f"Investigate customer complaints about {aspect}",
                        f"Benchmark {aspect} against competitors",
                        f"Create action plan for {aspect} improvement"],
        })

        recommendations.append({
            "category": aspect,
            "severity": severity,
            "title": template["title"],
            "actions": template["actions"],
            "negative_review_count": data["count"],
            "negative_review_pct": data["pct_of_all_reviews"],
            "avg_rating": data["avg_rating"],
        })

    return recommendations


def identify_strengths(df: pd.DataFrame) -> List[Dict]:
    """
    Identify strengths (what the business does well) based on positive reviews.
    """
    if df.empty or "sentiment" not in df.columns:
        return []

    positive = df[df["sentiment"] == "positive"]
    strengths = []

    for aspect, keywords in ASPECT_CATEGORIES.items():
        col = f"aspect_{aspect}"
        if col not in positive.columns:
            continue
        aspect_pos = positive[positive[col]]
        if len(aspect_pos) == 0:
            continue

        pos_pct = round(len(aspect_pos) / len(positive) * 100, 1)

        strengths.append({
            "aspect": aspect,
            "strength_score": pos_pct,
            "positive_review_count": len(aspect_pos),
            "avg_rating": round(aspect_pos["review_rating"].mean(), 2),
            "sample_praise": aspect_pos["clean_text"].head(3).tolist(),
        })

    return sorted(strengths, key=lambda x: x["strength_score"], reverse=True)


def generate_full_insight_report(df: pd.DataFrame) -> Dict:
    """
    Generate a comprehensive insight report for a single place or group.
    """
    report = {
        "overview": {
            "total_reviews": len(df),
            "avg_rating": round(df["review_rating"].mean(), 2) if "review_rating" in df.columns else 0,
            "sentiment_distribution": df["sentiment"].value_counts().to_dict() if "sentiment" in df.columns else {},
        },
        "strengths": [],
        "weaknesses": [],
        "recommendations": [],
    }

    if "sentiment" in df.columns:
        pos_pct = round((df["sentiment"] == "positive").mean() * 100, 1)
        neg_pct = round((df["sentiment"] == "negative").mean() * 100, 1)

        report["overview"]["positive_pct"] = pos_pct
        report["overview"]["negative_pct"] = neg_pct
        report["overview"]["sentiment_ratio"] = round(pos_pct / max(neg_pct, 0.1), 1)

        report["strengths"] = identify_strengths(df)

        complaint_analysis = analyze_negative_reviews(df)
        report["weaknesses"] = list(complaint_analysis.get("complaint_categories", {}).items())
        report["recommendations"] = generate_recommendations(complaint_analysis)

    return report


def generate_improvement_roadmap(recommendations: List[Dict]) -> pd.DataFrame:
    """
    Create a prioritized improvement roadmap as a DataFrame.
    """
    if not recommendations:
        return pd.DataFrame()

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_recs = sorted(recommendations, key=lambda x: severity_order.get(x["severity"], 99))

    rows = []
    for i, rec in enumerate(sorted_recs):
        for j, action in enumerate(rec["actions"]):
            rows.append({
                "priority": i + 1,
                "severity": rec["severity"],
                "category": rec["category"],
                "action_item": action,
                "impact_area": rec["category"],
                "estimated_effort": "Medium",
                "measure_of_success": f"Reduction in negative reviews about {rec['category']}",
            })

    return pd.DataFrame(rows)
