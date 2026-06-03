"""
Full Analytics Pipeline
Orchestrates all phases: preprocessing, sentiment, topics, insights, comparison.
"""
import json
import pandas as pd
from pathlib import Path
from typing import Optional, Dict

from config import PROCESSED_DIR

from analytics.preprocess import preprocess_reviews, get_review_stats
from analytics.sentiment import (
    run_sentiment_analysis, get_sentiment_summary,
    analyze_aspect_sentiment, get_aspect_summary, get_place_aspect_comparison,
)
from analytics.topics import (
    extract_global_keywords, extract_keywords_per_place,
    run_topic_modeling, get_phrase_frequencies, generate_word_frequencies,
    keyword_sentiment_correlation,
)
from analytics.insights import (
    generate_full_insight_report, generate_improvement_roadmap,
    analyze_negative_reviews, identify_strengths, generate_recommendations,
)
from analytics.compare import (
    compare_sentiment, compare_aspects, compare_keywords,
    generate_comparison_report, compute_competitive_advantages,
)


class AnalyticsPipeline:
    """
    Full analytics pipeline that processes reviews through all phases.
    """

    def __init__(self, df: pd.DataFrame, output_prefix: str = "analysis"):
        self.raw_df = df
        self.df = None
        self.output_prefix = output_prefix
        self.results: Dict = {}

    def run(self, sentiment_method: str = "transformer") -> Dict:
        """
        Run the full analytics pipeline.

        Args:
            sentiment_method: 'transformer' (multilingual) or 'vader' (English, fast)

        Returns:
            Dict with all analysis results.
        """
        if self.raw_df is None or self.raw_df.empty:
            print("[pipeline] No data to analyze.")
            return {}

        print("\n" + "=" * 60)
        print("  PHASE 1: Preprocessing & Cleaning")
        print("=" * 60)
        self.df = preprocess_reviews(self.raw_df)
        self.results["stats"] = get_review_stats(self.df)

        print("\n" + "=" * 60)
        print("  PHASE 2: Sentiment Analysis")
        print("=" * 60)
        self.df = run_sentiment_analysis(self.df, method=sentiment_method)
        self.df = analyze_aspect_sentiment(self.df)
        self.results["sentiment_summary"] = get_sentiment_summary(self.df)
        self.results["aspect_summary"] = get_aspect_summary(self.df)
        self.results["aspect_comparison_df"] = get_place_aspect_comparison(self.df)

        print("\n" + "=" * 60)
        print("  PHASE 3: Topic & Keyword Extraction")
        print("=" * 60)
        self.results["global_keywords"] = extract_global_keywords(self.df, method="tfidf")
        self.results["place_keywords"] = extract_keywords_per_place(self.df, method="tfidf")
        self.results["phrase_frequencies"] = get_phrase_frequencies(self.df, ngram=3)
        self.results["word_frequencies"] = generate_word_frequencies(self.df, top_n=50)
        self.results["kw_sentiment_correlation"] = keyword_sentiment_correlation(self.df)

        topic_result = run_topic_modeling(self.df, n_topics=5)
        self.results["topic_modeling"] = topic_result

        print("\n" + "=" * 60)
        print("  PHASE 4: Insights & Recommendations")
        print("=" * 60)
        complaint_analysis = analyze_negative_reviews(self.df)
        self.results["complaint_analysis"] = complaint_analysis
        self.results["strengths"] = identify_strengths(self.df)
        self.results["recommendations"] = generate_recommendations(complaint_analysis)
        self.results["improvement_roadmap"] = generate_improvement_roadmap(
            self.results["recommendations"]
        )

        print("\n" + "=" * 60)
        print("  COMPARISON: Cross-Place Analysis")
        print("=" * 60)
        places_count = self.df["place_name"].nunique()
        if places_count >= 2:
            self.results["comparison_report"] = generate_comparison_report(self.df)
            self.results["sentiment_comparison_df"] = compare_sentiment(self.df)
            self.results["keywords_comparison_df"] = compare_keywords(self.df)
            print(f"[pipeline] Compared {places_count} places.")
        else:
            print("[pipeline] Only 1 place found. Skipping comparison (need 2+).")
            self.results["comparison_report"] = None

        self._save_results()

        print("\n" + "=" * 60)
        print("  PIPELINE COMPLETE")
        print("=" * 60)
        self._print_summary()

        return self.results

    def _save_results(self):
        """Save processed DataFrame and JSON results."""
        self.df.to_parquet(
            PROCESSED_DIR / f"{self.output_prefix}_analyzed.parquet",
            index=False,
        )

        json_output = {}
        for key, value in self.results.items():
            try:
                if isinstance(value, pd.DataFrame):
                    json_output[key] = value.to_dict("records")
                elif isinstance(value, dict):
                    json_output[key] = value
                elif isinstance(value, list):
                    json_output[key] = value
            except Exception:
                json_output[key] = str(value)

        json_path = PROCESSED_DIR / f"{self.output_prefix}_results.json"
        with open(json_path, "w") as f:
            json.dump(json_output, f, indent=2, default=str, ensure_ascii=False)
        print(f"[pipeline] Results saved to {json_path}")

    def _print_summary(self):
        """Print a concise summary of findings."""
        stats = self.results.get("stats", {})
        sentiment = self.results.get("sentiment_summary", {})
        recs = self.results.get("recommendations", [])

        print(f"\n  Total Reviews: {stats.get('total_reviews', 0)}")
        print(f"  Total Places: {stats.get('total_places', 0)}")
        print(f"  Avg Rating: {stats.get('avg_rating', 0)}")

        if sentiment:
            print("\n  Top Places by Sentiment:")
            for place, data in list(sentiment.items())[:5]:
                print(f"    - {place}: {data.get('positive_pct', 0):.1f}% positive "
                      f"({data.get('total_reviews', 0)} reviews)")

        if recs:
            print(f"\n  Top {min(3, len(recs))} Improvement Recommendations:")
            for rec in recs[:3]:
                print(f"    [{rec.get('severity', '?').upper()}] {rec.get('title', '')}")


def run_pipeline_from_parquet(parquet_file: str, output_prefix: str = "analysis",
                               sentiment_method: str = "transformer") -> Dict:
    """Convenience function to run the full pipeline from a parquet file."""
    path = PROCESSED_DIR / parquet_file
    if not path.exists():
        path = Path(parquet_file)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {parquet_file}")

    print(f"[pipeline] Loading data from {path}")
    df = pd.read_parquet(path)
    pipeline = AnalyticsPipeline(df, output_prefix=output_prefix)
    return pipeline.run(sentiment_method=sentiment_method)
