"""
Streamlit Dashboard: Google Maps Review Analytics
Multi-page interactive dashboard for visualizing review analysis.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import json

st.set_page_config(
    page_title="Review Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config import PROCESSED_DIR, DASHBOARD_TITLE


def load_data() -> tuple:
    """Load analyzed data from processed directory."""
    parquet_files = list(PROCESSED_DIR.glob("*_analyzed.parquet"))
    json_files = list(PROCESSED_DIR.glob("*_results.json"))

    df = None
    results = {}

    if parquet_files:
        latest_parquet = max(parquet_files, key=lambda p: p.stat().st_mtime)
        df = pd.read_parquet(latest_parquet)
        st.sidebar.success(f"Loaded: {latest_parquet.name}")

    if json_files:
        latest_json = max(json_files, key=lambda p: p.stat().st_mtime)
        with open(latest_json, "r") as f:
            results = json.load(f)

    return df, results


def overview_page(df: pd.DataFrame, results: dict):
    """Overview dashboard page."""
    st.title(f"📊 {DASHBOARD_TITLE}")
    st.markdown("---")

    stats = results.get("stats", {})
    sentiment_summary = results.get("sentiment_summary", {})

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Reviews", stats.get("total_reviews", "N/A"))
    col2.metric("Places Analyzed", stats.get("total_places", "N/A"))
    col3.metric("Avg Rating", stats.get("avg_rating", "N/A"))
    col4.metric("Avg Words/Review", stats.get("avg_word_count", "N/A"))

    st.markdown("---")
    st.subheader("📈 Place Rankings")
    if sentiment_summary:
        ranking_df = pd.DataFrame.from_dict(sentiment_summary, orient="index")
        ranking_df = ranking_df.sort_values("positive_pct", ascending=False)

        col1, col2 = st.columns([2, 1])
        with col1:
            st.dataframe(
                ranking_df.style.background_gradient(subset=["positive_pct"], cmap="RdYlGn")
                .format("{:.1f}%", subset=["positive_pct", "neutral_pct", "negative_pct"])
                .format("{:.2f}", subset=["avg_sentiment_score", "avg_review_rating"]),
                width="stretch",
            )
        with col2:
            st.subheader("🏆 Top Performer")
            if not ranking_df.empty:
                top = ranking_df.index[0]
                top_data = ranking_df.iloc[0]
                st.markdown(f"### {top}")
                st.markdown(f"- 😊 Positive: **{top_data['positive_pct']:.1f}%**")
                st.markdown(f"- 😔 Negative: **{top_data['negative_pct']:.1f}%**")
                st.markdown(f"- ⭐ Avg Rating: **{top_data['avg_review_rating']:.2f}**")
                st.markdown(f"- 📝 Reviews: **{int(top_data['total_reviews'])}**")
    else:
        st.info("No sentiment data available. Run the analytics pipeline first.")

    st.markdown("---")
    st.subheader("📊 Rating Distribution")
    if df is not None and "review_rating" in df.columns:
        import plotly.express as px
        rating_dist = df["review_rating"].value_counts().sort_index()
        fig = px.bar(
            x=rating_dist.index, y=rating_dist.values,
            labels={"x": "Star Rating", "y": "Count"},
            color=rating_dist.index,
            color_continuous_scale="Viridis",
        )
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)


def sentiment_page(df: pd.DataFrame, results: dict):
    """Sentiment analysis page."""
    st.title("😊😐😔 Sentiment Analysis")
    st.markdown("---")

    if df is None or "sentiment" not in df.columns:
        st.warning("No sentiment data available. Run the pipeline first.")
        return

    import plotly.express as px
    import plotly.graph_objects as go

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Overall Sentiment Distribution")
        sentiment_counts = df["sentiment"].value_counts()
        fig = px.pie(
            values=sentiment_counts.values,
            names=sentiment_counts.index,
            color=sentiment_counts.index,
            color_discrete_map={"positive": "#2ecc71", "neutral": "#f1c40f", "negative": "#e74c3c"},
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Sentiment by Rating")
        if "review_rating" in df.columns:
            rating_sentiment = df.groupby("review_rating")["sentiment"].value_counts(normalize=True).unstack().fillna(0) * 100
            fig = px.bar(
                rating_sentiment,
                barmode="stack",
                color_discrete_map={"positive": "#2ecc71", "neutral": "#f1c40f", "negative": "#e74c3c"},
                labels={"value": "Percentage", "review_rating": "Star Rating"},
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Sentiment by Place")
    place_sentiment = df.groupby("place_name")["sentiment"].value_counts(normalize=True).unstack().fillna(0) * 100
    place_sentiment = place_sentiment.sort_values("positive", ascending=False)

    fig = px.bar(
        place_sentiment,
        barmode="group",
        color_discrete_map={"positive": "#2ecc71", "neutral": "#f1c40f", "negative": "#e74c3c"},
        labels={"value": "Percentage (%)", "place_name": "Place"},
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("😊 Top Positive Reviews")
        positive = df[df["sentiment"] == "positive"].nlargest(5, "sentiment_score")
        for _, row in positive.iterrows():
            with st.expander(f"⭐ {row['place_name']} (score: {row['sentiment_score']:.2f})"):
                st.write(row["clean_text"][:500])

    with col2:
        st.subheader("😔 Top Negative Reviews")
        negative = df[df["sentiment"] == "negative"].nlargest(5, "sentiment_score")
        for _, row in negative.iterrows():
            with st.expander(f"💢 {row['place_name']} (score: {row['sentiment_score']:.2f})"):
                st.write(row["clean_text"][:500])


def aspects_page(df: pd.DataFrame, results: dict):
    """Aspect-based analysis page."""
    st.title("🔍 Aspect Analysis")
    st.markdown("---")

    aspect_summary = results.get("aspect_summary", {})
    if not aspect_summary:
        st.warning("No aspect analysis data available.")
        return

    import plotly.express as px
    import plotly.graph_objects as go

    aspects_data = []
    for aspect, data in aspect_summary.items():
        if data.get("total_mentions", 0) > 0:
            aspects_data.append({
                "Aspect": aspect.replace("_", " ").title(),
                "Mentions": data["total_mentions"],
                "Positive %": data["positive_pct"],
                "Negative %": data["negative_pct"],
                "Mention Rate %": data.get("mention_rate", 0),
            })

    if not aspects_data:
        st.info("No aspects were mentioned in reviews.")
        return

    aspect_df = pd.DataFrame(aspects_data)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Aspect Mention Frequency")
        fig = px.bar(
            aspect_df.sort_values("Mentions", ascending=True),
            x="Mentions", y="Aspect", orientation="h",
            color="Mentions", color_continuous_scale="Blues",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Aspect Sentiment (Positive vs Negative)")
        fig = px.bar(
            aspect_df,
            x="Aspect", y=["Positive %", "Negative %"],
            barmode="group",
            color_discrete_map={"Positive %": "#2ecc71", "Negative %": "#e74c3c"},
            labels={"value": "Percentage (%)"},
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Aspect Details")

    for aspect, data in aspect_summary.items():
        if data.get("total_mentions", 0) == 0:
            continue

        col1, col2, col3, col4 = st.columns(4)
        col1.metric(f"{aspect.title()}", f"{data['total_mentions']} mentions")
        col2.metric("Positive", f"{data['positive_pct']}%")
        col3.metric("Negative", f"{data['negative_pct']}%")
        col4.metric("Avg Rating", f"{data['avg_rating']:.2f}")

        with st.expander("Sample Reviews"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.caption("😊 Positive examples:")
                for r in data.get("sample_positive", [])[:3]:
                    st.write(f"- {r[:200]}...")
            with col_b:
                st.caption("😔 Negative examples:")
                for r in data.get("sample_negative", [])[:3]:
                    st.write(f"- {r[:200]}...")


def keywords_page(df: pd.DataFrame, results: dict):
    """Keywords & Topics page."""
    st.title("🔑 Keywords & Topics")
    st.markdown("---")

    global_keywords = results.get("global_keywords", [])
    word_frequencies = results.get("word_frequencies", [])
    phrase_frequencies = results.get("phrase_frequencies", [])
    kw_corr = results.get("kw_sentiment_correlation", [])
    topic_modeling = results.get("topic_modeling", {})

    import plotly.express as px

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("☁️ Word Cloud")
        if word_frequencies:
            try:
                from wordcloud import WordCloud
                import matplotlib.pyplot as plt

                freq_dict = dict(word_frequencies)
                wc = WordCloud(
                    width=600, height=400,
                    background_color="white",
                    colormap="viridis",
                    max_words=100,
                ).generate_from_frequencies(freq_dict)

                fig, ax = plt.subplots(figsize=(8, 5))
                ax.imshow(wc, interpolation="bilinear")
                ax.axis("off")
                st.pyplot(fig)
            except ImportError:
                st.info("Install wordcloud package for word cloud visualization.")

    with col2:
        st.subheader("🔝 Top Phrases (3-grams)")
        if phrase_frequencies:
            phrase_df = pd.DataFrame(phrase_frequencies, columns=["Phrase", "Count"])
            fig = px.bar(
                phrase_df.head(15).sort_values("Count"),
                x="Count", y="Phrase", orientation="h",
                color="Count", color_continuous_scale="Viridis",
            )
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("🎯 Keywords by Sentiment Association")

    if isinstance(kw_corr, list) and kw_corr:
        kw_corr_df = pd.DataFrame(kw_corr)
    elif isinstance(kw_corr, dict):
        kw_corr_df = pd.DataFrame(kw_corr)
    else:
        kw_corr_df = pd.DataFrame()

    if not kw_corr_df.empty and "sentiment_bias" in kw_corr_df.columns:
        kw_corr_df = kw_corr_df.sort_values("sentiment_bias")

        fig = px.bar(
            kw_corr_df.head(20),
            x="sentiment_bias", y="keyword", orientation="h",
            color="sentiment_bias",
            color_continuous_scale=["red", "gray", "green"],
            color_continuous_midpoint=0,
            labels={"sentiment_bias": "Positive ← → Negative"},
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("🧠 Topic Modeling (LDA)")

    topics = topic_modeling.get("topics", {})
    topic_counts = topic_modeling.get("topic_counts", {})

    if topics:
        cols = st.columns(len(topics))
        for i, (topic_name, topic_data) in enumerate(topics.items()):
            with cols[i]:
                count = topic_counts.get(topic_name, 0)
                st.metric(topic_name.replace("_", " ").title(), f"{count} reviews")
                words = topic_data.get("words", [])
                st.markdown("\n".join([f"`{w}`" for w in words[:10]]))

    st.markdown("---")
    st.subheader("🔍 Keywords by Place")

    place_keywords = results.get("place_keywords", {})
    if place_keywords:
        selected_place = st.selectbox("Select Place", list(place_keywords.keys()))
        if selected_place and place_keywords.get(selected_place):
            kw_list = place_keywords[selected_place]
            if kw_list:
                kw_df = pd.DataFrame(kw_list, columns=["Keyword", "Score"])
                fig = px.bar(
                    kw_df.head(15).sort_values("Score"),
                    x="Score", y="Keyword", orientation="h",
                    color="Score", color_continuous_scale="Viridis",
                )
                st.plotly_chart(fig, use_container_width=True)


def comparison_page(df: pd.DataFrame, results: dict):
    """Competitor comparison page."""
    st.title("⚔️ Competitor Comparison")
    st.markdown("---")

    if df is None or df["place_name"].nunique() < 2:
        st.warning("Need at least 2 places for comparison. Scrape multiple places first.")
        return

    import plotly.express as px
    import plotly.graph_objects as go

    places = sorted(df["place_name"].unique())
    selected_places = st.multiselect(
        "Select places to compare (2+ recommended)",
        places, default=list(places)[:min(5, len(places))],
    )

    if len(selected_places) < 2:
        st.info("Select at least 2 places to compare.")
        return

    comp_df = df[df["place_name"].isin(selected_places)]

    st.subheader("📊 Sentiment Comparison")
    if "sentiment" in comp_df.columns:
        sentiment_comp = comp_df.groupby("place_name")["sentiment"].value_counts(normalize=True).unstack().fillna(0) * 100

        fig = px.bar(
            sentiment_comp,
            barmode="group",
            color_discrete_map={"positive": "#2ecc71", "neutral": "#f1c40f", "negative": "#e74c3c"},
            labels={"value": "Percentage (%)"},
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("⭐ Rating Comparison")
        rating_comp = comp_df.groupby("place_name")["review_rating"].agg(["mean", "count"]).round(2)
        fig = px.bar(
            rating_comp.reset_index(),
            x="place_name", y="mean",
            color="mean", color_continuous_scale="RdYlGn",
            text="mean",
            labels={"place_name": "", "mean": "Avg Rating"},
            height=350,
        )
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📈 Sentiment Health Score")
        if "sentiment" in comp_df.columns:
            health = comp_df.groupby("place_name").agg(
                health_score=("sentiment", lambda x: (x == "positive").mean() * 100 - (x == "negative").mean() * 100)
            ).round(1).sort_values("health_score", ascending=False)

            fig = px.bar(
                health.reset_index(),
                x="place_name", y="health_score",
                color="health_score", color_continuous_scale="RdYlGn",
                text="health_score",
                labels={"place_name": "", "health_score": "Health Score"},
                height=350,
            )
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("🔍 Aspect Comparison Matrix")

    from analytics.compare import compare_aspects
    aspect_comp = compare_aspects(comp_df)

    if not aspect_comp.empty:
        pivot = aspect_comp.pivot_table(
            index="aspect", columns="place_name",
            values="net_sentiment", aggfunc="mean",
        ).fillna(0).round(1)

        selected_aspects = pivot.index.tolist()
        pivot.index = [a.replace("_", " ").title() for a in selected_aspects]

        fig = px.imshow(
            pivot,
            text_auto=True,
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0,
            aspect="auto",
            labels={"color": "Net Sentiment"},
        )
        fig.update_layout(height=max(300, len(selected_aspects) * 40))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("🏆 Competitive Advantages")

    from analytics.compare import compute_competitive_advantages
    advantages = compute_competitive_advantages(comp_df)

    if advantages:
        for place, advs in advantages.items():
            with st.expander(f"💪 {place} - Advantages"):
                for adv in advs:
                    st.markdown(f"- ✅ **{adv.replace('_', ' ').title()}**")
    else:
        st.info("No clear competitive advantages detected.")


def insights_page(df: pd.DataFrame, results: dict):
    """Insights & Recommendations page."""
    st.title("💡 Insights & Recommendations")
    st.markdown("---")

    recommendations = results.get("recommendations", [])
    strengths = results.get("strengths", [])
    complaint_analysis = results.get("complaint_analysis", {})
    improvement_roadmap = results.get("improvement_roadmap", [])

    st.subheader("✅ Strengths (What You're Doing Well)")
    if strengths:
        strength_cols = st.columns(min(3, len(strengths)))
        for i, s in enumerate(strengths[:6]):
            with strength_cols[i % 3]:
                st.markdown(f"**{s['aspect'].replace('_', ' ').title()}**")
                st.markdown(f"📊 Score: **{s['strength_score']}%**")
                st.markdown(f"📝 {s['positive_review_count']} positive mentions")
                st.progress(min(s["strength_score"] / 100, 1.0))
    else:
        st.info("No strength data available.")

    st.markdown("---")
    st.subheader("⚠️ Areas for Improvement")

    complaint_categories = complaint_analysis.get("complaint_categories", {})
    if complaint_categories:
        comp_cols = st.columns(min(3, len(complaint_categories)))
        for i, (aspect, data) in enumerate(sorted(
            complaint_categories.items(),
            key=lambda x: x[1]["count"], reverse=True
        )[:6]):
            with comp_cols[i % 3]:
                severity = "🔴" if data["pct_of_negative_reviews"] > 20 else \
                           "🟠" if data["pct_of_negative_reviews"] > 10 else \
                           "🟡" if data["pct_of_negative_reviews"] > 5 else "🟢"
                st.markdown(f"{severity} **{aspect.replace('_', ' ').title()}**")
                st.markdown(f"📝 {data['count']} complaints ({data['pct_of_all_reviews']}%)")
                st.markdown(f"⭐ Avg rating: {data['avg_rating']}")
    else:
        st.info("No complaint data available.")

    st.markdown("---")
    st.subheader("📋 Improvement Roadmap")

    if improvement_roadmap:
        if isinstance(improvement_roadmap, list):
            roadmap_df = pd.DataFrame(improvement_roadmap)
        else:
            roadmap_df = pd.DataFrame(improvement_roadmap)

        if not roadmap_df.empty:
            severity_filter = st.multiselect(
                "Filter by severity",
                ["critical", "high", "medium", "low"],
                default=["critical", "high"],
            )
            filtered = roadmap_df[roadmap_df["severity"].isin(severity_filter)]

            st.dataframe(
                filtered.style.applymap(
                    lambda x: "background-color: #ff6b6b; color: white" if x == "critical"
                    else "background-color: #ffa502; color: white" if x == "high"
                    else "background-color: #ffd43b" if x == "medium"
                    else "",
                    subset=["severity"],
                ),
                width="stretch",
                height=400,
            )

            if st.button("📥 Export Roadmap as CSV"):
                csv = filtered.to_csv(index=False)
                st.download_button(
                    "Download CSV", csv, "improvement_roadmap.csv", "text/csv",
                )
    else:
        st.info("No recommendations available yet.")

    st.markdown("---")
    st.subheader("📝 Sample Complaints by Category")
    if complaint_categories:
        for aspect, data in sorted(
            complaint_categories.items(),
            key=lambda x: x[1]["count"], reverse=True
        )[:5]:
            with st.expander(f"{aspect.replace('_', ' ').title()} ({data['count']} complaints)"):
                for c in data.get("sample_complaints", [])[:5]:
                    st.markdown(f"- {c[:300]}...")


def main():
    """Main dashboard entry point."""
    st.sidebar.title("🗺️ Navigation")
    st.sidebar.markdown("---")

    df, results = load_data()

    pages = {
        "📊 Overview": overview_page,
        "😊 Sentiment Analysis": sentiment_page,
        "🔍 Aspect Analysis": aspects_page,
        "🔑 Keywords & Topics": keywords_page,
        "⚔️ Competitor Comparison": comparison_page,
        "💡 Insights & Recommendations": insights_page,
    }

    page = st.sidebar.radio("Select Page", list(pages.keys()))

    if df is None and not results:
        st.sidebar.warning("No analysis data found.")

    st.sidebar.markdown("---")
    st.sidebar.caption("Google Maps Review Analytics")
    st.sidebar.caption("v1.0.0")

    pages[page](df, results)


if __name__ == "__main__":
    main()
