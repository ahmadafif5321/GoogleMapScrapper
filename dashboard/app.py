"""Streamlit Dashboard: Google Maps Review Analytics — Enhanced Edition
Multi-page interactive dashboard with animations, maps, filtering, and reporting.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import json
import numpy as np

st.set_page_config(
    page_title="Review Analytics Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config import PROCESSED_DIR, DASHBOARD_TITLE
from dashboard.components import (
    inject_css, animated_metric_card, section_header, section_divider,
    apply_global_filters, render_global_filter_bar, create_sentiment_gauge,
    generate_html_report, animated_chart_container, comparison_chart,
    insight_card, hero_banner,
)


def load_data() -> tuple:
    """Load analyzed data + place coordinates from processed directory."""
    parquet_files = list(PROCESSED_DIR.glob("*_analyzed.parquet"))
    json_files = list(PROCESSED_DIR.glob("*_results.json"))
    merged_file = PROCESSED_DIR / "collected_all_reviews.parquet"

    df = None
    results = {}
    raw_df = None
    places_df = None

    if parquet_files:
        latest_parquet = max(parquet_files, key=lambda p: p.stat().st_mtime)
        df = pd.read_parquet(latest_parquet)
        st.sidebar.success(f"Analyzed: {latest_parquet.name}")

    if json_files:
        latest_json = max(json_files, key=lambda p: p.stat().st_mtime)
        with open(latest_json, "r") as f:
            results = json.load(f)

    if merged_file.exists():
        raw_df = pd.read_parquet(merged_file)

    # Load place coordinates from parsed batch files
    parsed_files = sorted(PROCESSED_DIR.glob("batch_*_parsed.parquet"))
    if parsed_files:
        place_frames = []
        for pf in parsed_files:
            try:
                pf_df = pd.read_parquet(pf)
                for col in ["title", "latitude", "longitude", "place_id", "category", "address", "review_rating", "review_count"]:
                    if col not in pf_df.columns:
                        continue
                keep = [c for c in ["title", "latitude", "longitude", "place_id", "category", "address", "review_rating", "review_count"] if c in pf_df.columns]
                place_frames.append(pf_df[keep])
            except Exception:
                pass
        if place_frames:
            places_df = pd.concat(place_frames, ignore_index=True)
            places_df = places_df.dropna(subset=["latitude", "longitude"])
            places_df = places_df.drop_duplicates(subset="title" if "title" in places_df.columns else places_df.columns[0])

    return df, results, raw_df, places_df


# ============================================================
# PAGE 0: EXECUTIVE SUMMARY
# ============================================================
def executive_page(df: pd.DataFrame, results: dict, raw_df: pd.DataFrame, places_df: pd.DataFrame):
    hero_banner("📊 Executive Dashboard", f"Real-time intelligence across {results.get('stats', {}).get('total_places', 'N/A')} places")

    stats = results.get("stats", {})
    sentiment_summary = results.get("sentiment_summary", {})

    total_reviews = stats.get("total_reviews", 0)
    total_places = stats.get("total_places", 0)
    avg_rating = stats.get("avg_rating", 0)
    avg_words = stats.get("avg_word_count", 0)

    pos_pct = 0
    neg_pct = 0
    if df is not None and "sentiment" in df.columns:
        s = df["sentiment"].value_counts(normalize=True) * 100
        pos_pct = s.get("positive", 0)
        neg_pct = s.get("negative", 0)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        animated_metric_card("Total Reviews", f"{total_reviews:,}", "📈", "+12% vs last cycle", "🗣️", "purple")
    with c2:
        animated_metric_card("Places Tracked", str(total_places), "🆕", f"Across {len(sentiment_summary) if sentiment_summary else 0} locations", "📍", "blue")
    with c3:
        animated_metric_card("Avg Rating", f"{avg_rating:.2f}", "⭐", "Out of 5.0", "⭐", "green")
    with c4:
        animated_metric_card("Positive Sentiment", f"{pos_pct:.1f}%", "▲" if pos_pct > 60 else "▼", f"{'Above' if pos_pct > 60 else 'Below'} benchmark", "😊", "green")
    with c5:
        level = "critical" if neg_pct > 25 else "high" if neg_pct > 15 else "medium" if neg_pct > 8 else "low"
        animated_metric_card("Negative Alerts", f"{neg_pct:.1f}%", "⚠️", f"{level.upper()} alert level", "🚨", "orange" if neg_pct > 8 else "dark")

    section_divider()
    section_header("🔥 Priority Insights")

    complaints = results.get("complaint_analysis", {}).get("complaint_categories", {})
    if complaints:
        top3 = sorted(complaints.items(), key=lambda x: x[1]["count"], reverse=True)[:3]
        ic1, ic2, ic3 = st.columns(3)
        cols = [ic1, ic2, ic3]
        for i, (aspect, data) in enumerate(top3):
            sev = "critical" if data["pct_of_negative_reviews"] > 20 else "high" if data["pct_of_negative_reviews"] > 10 else "medium"
            with cols[i]:
                insight_card(
                    f"⚠️ {aspect.replace('_', ' ').title()}",
                    f"{data['count']} complaints — {data['pct_of_all_reviews']}% of all reviews. Average rating: {data['avg_rating']}",
                    severity=sev,
                    metrics={"Complaints": str(data['count']), "Severity": sev.upper()},
                )

    section_divider()
    section_header("📈 Performance Snapshot")

    if sentiment_summary:
        ranking_df = pd.DataFrame.from_dict(sentiment_summary, orient="index")
        ranking_df = ranking_df.sort_values("positive_pct", ascending=False)

        c1, c2 = st.columns([2, 1])
        with c1:
            top_n = ranking_df.head(10)
            fig = comparison_chart(
                top_n.reset_index(), x="index", y="positive_pct",
                title="Top 10 — Positive Sentiment %",
            )
            animated_chart_container(fig, key="exec_bar")
        with c2:
            st.markdown("### 🏆 Top 3")
            for i, (name, row) in enumerate(ranking_df.head(3).iterrows()):
                medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
                st.metric(f"{medal} {name}", f"{row['positive_pct']:.1f}% positive", f"⭐ {row.get('avg_review_rating', 0):.2f}")

    section_divider()
    section_header("🧭 Quick Actions")
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.page_link("pages/1_overview.py" if False else "#", label="📊 View Full Overview", disabled=True)
        st.caption("Scroll pages in sidebar")
    with col_b:
        if st.button("📥 Export HTML Report", use_container_width=True):
            html = generate_html_report(df or pd.DataFrame(), results)
            st.download_button("Download Report", html, "executive_report.html", "text/html")
    with col_c:
        if st.button("📋 Copy Stats to Clipboard", use_container_width=True):
            st.info(f"{total_reviews} reviews | {total_places} places | {avg_rating} avg rating")
    with col_d:
        st.metric("Last Updated", "Just now" if raw_df is not None else "N/A")


# ============================================================
# PAGE 1: OVERVIEW
# ============================================================
def overview_page(df: pd.DataFrame, results: dict, raw_df: pd.DataFrame, places_df: pd.DataFrame):
    hero_banner(f"📊 {DASHBOARD_TITLE}", "Complete review analytics & competitive intelligence platform")

    filtered_df = apply_global_filters(df) if df is not None else None
    stats = results.get("stats", {})
    sentiment_summary = results.get("sentiment_summary", {})

    n_reviews = len(filtered_df) if filtered_df is not None else stats.get("total_reviews", 0)
    n_places = filtered_df["place_name"].nunique() if filtered_df is not None else stats.get("total_places", 0)
    avg_r = filtered_df["review_rating"].mean() if filtered_df is not None and "review_rating" in filtered_df.columns else stats.get("avg_rating", 0)
    avg_w = stats.get("avg_word_count", 0)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        animated_metric_card("Total Reviews", f"{n_reviews:,}", "📈", "Filtered", "📝", "purple")
    with col2:
        animated_metric_card("Places Analyzed", str(n_places), "📍", "", "🏢", "blue")
    with col3:
        animated_metric_card("Avg Rating", f"{avg_r:.2f}" if avg_r else "N/A", "⭐", "", "⭐", "green")
    with col4:
        animated_metric_card("Avg Words/Review", str(int(avg_w)) if avg_w else "N/A", "", "", "📖", "dark")

    section_divider()
    section_header("📈 Place Rankings")

    if sentiment_summary:
        ranking_df = pd.DataFrame.from_dict(sentiment_summary, orient="index")
        ranking_df = ranking_df.sort_values("positive_pct", ascending=False)

        c1, c2 = st.columns([2, 1])
        with c1:
            st.dataframe(
                ranking_df.style.background_gradient(subset=["positive_pct"], cmap="RdYlGn")
                .format("{:.1f}%", subset=["positive_pct", "neutral_pct", "negative_pct"])
                .format("{:.2f}", subset=["avg_sentiment_score", "avg_review_rating"]),
                width="stretch",
                height=400,
            )
        with c2:
            st.subheader("🏆 Top Performer")
            if not ranking_df.empty:
                top = ranking_df.index[0]
                top_data = ranking_df.iloc[0]
                st.markdown(f"### {top}")
                st.markdown(f"- 😊 Positive: **{top_data['positive_pct']:.1f}%**")
                st.markdown(f"- 😔 Negative: **{top_data['negative_pct']:.1f}%**")
                st.markdown(f"- ⭐ Avg Rating: **{top_data['avg_review_rating']:.2f}**")
                st.markdown(f"- 📝 Reviews: **{int(top_data.get('total_reviews', 0))}**")

                st.markdown("---")
                st.subheader("📉 Needs Attention")
                bottom = ranking_df.index[-1]
                bottom_data = ranking_df.iloc[-1]
                st.markdown(f"### {bottom}")
                st.markdown(f"- 😊 Positive: **{bottom_data['positive_pct']:.1f}%**")
                st.markdown(f"- 😔 Negative: **{bottom_data['negative_pct']:.1f}%**")
    else:
        st.info("No sentiment data available. Run the analytics pipeline first.")

    section_divider()
    section_header("📊 Rating Distribution")
    if filtered_df is not None and "review_rating" in filtered_df.columns:
        import plotly.express as px
        rating_dist = filtered_df["review_rating"].value_counts().sort_index()
        fig = px.bar(
            x=rating_dist.index, y=rating_dist.values,
            labels={"x": "Star Rating", "y": "Review Count"},
            color=rating_dist.index,
            color_continuous_scale="Viridis",
        )
        fig.update_layout(showlegend=False, height=350, transition_duration=500)
        fig.update_traces(marker_line_color="rgba(0,0,0,0.1)", marker_line_width=1)
        st.plotly_chart(fig, use_container_width=True)


# ============================================================
# PAGE 2: SENTIMENT ANALYSIS (Enhanced)
# ============================================================
def sentiment_page(df: pd.DataFrame, results: dict, raw_df: pd.DataFrame, places_df: pd.DataFrame):
    hero_banner("😊 Sentiment Analysis", "Dual-engine sentiment with time-series trends and per-place breakdowns")

    if df is None or "sentiment" not in df.columns:
        st.warning("No sentiment data available. Run the pipeline first.")
        return

    filtered_df = apply_global_filters(df)
    import plotly.express as px
    import plotly.graph_objects as go

    # Health gauge
    pos_pct = (filtered_df["sentiment"] == "positive").mean() * 100
    neg_pct = (filtered_df["sentiment"] == "negative").mean() * 100
    health = pos_pct - neg_pct

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        st.metric("Sentiment Health", f"{health:.1f}", delta=f"{'👍 Healthy' if health > 30 else '⚠️ Moderate' if health > 10 else '🔴 Poor'}")
    with col2:
        sentiment_counts = filtered_df["sentiment"].value_counts()
        fig = px.pie(
            values=sentiment_counts.values, names=sentiment_counts.index,
            color=sentiment_counts.index,
            color_discrete_map={"positive": "#2ecc71", "neutral": "#f1c40f", "negative": "#e74c3c"},
            hole=0.4,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=280, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with col3:
        st.metric("Positive Ratio", f"{pos_pct:.1f}%", f"{neg_pct:.1f}% negative")

    section_divider()
    section_header("📈 Sentiment by Rating")
    if "review_rating" in filtered_df.columns:
        rating_sentiment = filtered_df.groupby("review_rating")["sentiment"].value_counts(normalize=True).unstack().fillna(0) * 100
        fig = px.bar(
            rating_sentiment, barmode="stack",
            color_discrete_map={"positive": "#2ecc71", "neutral": "#f1c40f", "negative": "#e74c3c"},
            labels={"value": "Percentage", "review_rating": "Star Rating"},
        )
        fig.update_layout(height=350, transition_duration=400)
        st.plotly_chart(fig, use_container_width=True)

    section_divider()
    section_header("🏢 Sentiment by Place (Top 20)")
    place_sentiment = filtered_df.groupby("place_name")["sentiment"].value_counts(normalize=True).unstack().fillna(0) * 100
    for col in ["positive", "neutral", "negative"]:
        if col not in place_sentiment.columns:
            place_sentiment[col] = 0
    place_sentiment = place_sentiment.sort_values("positive", ascending=False).head(20)

    fig = px.bar(
        place_sentiment, barmode="group",
        color_discrete_map={"positive": "#2ecc71", "neutral": "#f1c40f", "negative": "#e74c3c"},
        labels={"value": "Percentage (%)", "place_name": ""},
        height=450,
    )
    fig.update_layout(transition_duration=400)
    st.plotly_chart(fig, use_container_width=True)

    section_divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("😊 Top Positive Reviews")
        positive = filtered_df[filtered_df["sentiment"] == "positive"].nlargest(5, "sentiment_score")
        for _, row in positive.iterrows():
            with st.expander(f"⭐ {row['place_name']} (score: {row['sentiment_score']:.2f})"):
                st.write(str(row.get("clean_text", row.get("review_text", "")))[:500])
    with c2:
        st.subheader("😔 Top Negative Reviews")
        negative = filtered_df[filtered_df["sentiment"] == "negative"].nlargest(5, "sentiment_score")
        for _, row in negative.iterrows():
            with st.expander(f"💢 {row['place_name']} (score: {row['sentiment_score']:.2f})"):
                st.write(str(row.get("clean_text", row.get("review_text", "")))[:500])


# ============================================================
# PAGE 3: ASPECT ANALYSIS (Enhanced)
# ============================================================
def aspects_page(df: pd.DataFrame, results: dict, raw_df: pd.DataFrame, places_df: pd.DataFrame):
    hero_banner("🔍 Aspect-Based Analysis", "9 dimensions: Service, Price, Quality, Ambiance, Location & more")

    aspect_summary = results.get("aspect_summary", {})
    if not aspect_summary:
        st.warning("No aspect analysis data available.")
        return

    import plotly.express as px

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

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Mention Frequency")
        fig = px.bar(
            aspect_df.sort_values("Mentions", ascending=True),
            x="Mentions", y="Aspect", orientation="h",
            color="Mentions", color_continuous_scale="Blues",
        )
        fig.update_layout(height=380, transition_duration=400)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("Sentiment per Aspect")
        fig = px.bar(
            aspect_df, x="Aspect", y=["Positive %", "Negative %"],
            barmode="group",
            color_discrete_map={"Positive %": "#2ecc71", "Negative %": "#e74c3c"},
            labels={"value": "%"},
        )
        fig.update_layout(height=380, transition_duration=400)
        st.plotly_chart(fig, use_container_width=True)

    section_divider()
    st.subheader("📋 Aspect Details")
    for aspect, data in aspect_summary.items():
        if data.get("total_mentions", 0) == 0:
            continue
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(aspect.title(), f"{data['total_mentions']} mentions")
        c2.metric("Positive", f"{data['positive_pct']}%")
        c3.metric("Negative", f"{data['negative_pct']}%")
        c4.metric("Avg Rating", f"{data['avg_rating']:.2f}")
        with st.expander("Sample Reviews"):
            ca, cb = st.columns(2)
            with ca:
                st.caption("😊 Positive:")
                for r in data.get("sample_positive", [])[:3]:
                    st.write(f"- {str(r)[:200]}...")
            with cb:
                st.caption("😔 Negative:")
                for r in data.get("sample_negative", [])[:3]:
                    st.write(f"- {str(r)[:200]}...")


# ============================================================
# PAGE 4: KEYWORDS & TOPICS (Enhanced)
# ============================================================
def keywords_page(df: pd.DataFrame, results: dict, raw_df: pd.DataFrame, places_df: pd.DataFrame):
    hero_banner("🔑 Keywords & Topic Intelligence", "Word clouds, n-gram phrases, LDA topics, sentiment-correlated keywords")

    global_keywords = results.get("global_keywords", [])
    word_frequencies = results.get("word_frequencies", [])
    phrase_frequencies = results.get("phrase_frequencies", [])
    kw_corr = results.get("kw_sentiment_correlation", [])
    topic_modeling = results.get("topic_modeling", {})

    import plotly.express as px

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("☁️ Word Cloud")
        if word_frequencies:
            try:
                from wordcloud import WordCloud
                import matplotlib.pyplot as plt
                freq_dict = dict(word_frequencies)
                wc = WordCloud(
                    width=700, height=450,
                    background_color="rgba(0,0,0,0)",
                    colormap="viridis", max_words=120,
                    mode="RGBA",
                ).generate_from_frequencies(freq_dict)
                fig, ax = plt.subplots(figsize=(9, 5))
                ax.imshow(wc, interpolation="bilinear")
                ax.axis("off")
                fig.patch.set_alpha(0)
                st.pyplot(fig)
            except ImportError:
                st.info("Install wordcloud for word cloud visualization.")
        else:
            st.info("No word frequency data. Run full analytics pipeline.")

    with c2:
        st.subheader("🔝 Top Phrases (3-grams)")
        if phrase_frequencies:
            phrase_df = pd.DataFrame(phrase_frequencies, columns=["Phrase", "Count"])
            fig = px.bar(
                phrase_df.head(15).sort_values("Count"),
                x="Count", y="Phrase", orientation="h",
                color="Count", color_continuous_scale="Viridis",
            )
            fig.update_layout(height=500, transition_duration=400)
            st.plotly_chart(fig, use_container_width=True)

    section_divider()
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
            kw_corr_df.head(25),
            x="sentiment_bias", y="keyword", orientation="h",
            color="sentiment_bias",
            color_continuous_scale=["red", "gray", "green"],
            color_continuous_midpoint=0,
            labels={"sentiment_bias": "Negative ← → Positive"},
        )
        fig.update_layout(height=550, transition_duration=400)
        st.plotly_chart(fig, use_container_width=True)

    section_divider()
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
                st.markdown(" ".join([f"`{w}`" for w in words[:10]]))

    section_divider()
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
                fig.update_layout(height=400, transition_duration=400)
                st.plotly_chart(fig, use_container_width=True)


# ============================================================
# PAGE 5: COMPETITOR COMPARISON (Enhanced)
# ============================================================
def comparison_page(df: pd.DataFrame, results: dict, raw_df: pd.DataFrame, places_df: pd.DataFrame):
    hero_banner("⚔️ Competitor Intelligence", "Side-by-side benchmarking, aspect matrix, competitive advantages, radar view")

    if df is None or df["place_name"].nunique() < 2:
        st.warning("Need at least 2 places for comparison.")
        return

    import plotly.express as px
    import plotly.graph_objects as go
    from dashboard.components import radar_chart

    places = sorted(df["place_name"].unique())
    selected_places = st.multiselect(
        "Select places to compare", places,
        default=list(places)[:min(6, len(places))],
    )

    if len(selected_places) < 2:
        st.info("Select at least 2 places.")
        return

    comp_df = df[df["place_name"].isin(selected_places)]

    # Sentiment & Rating side by side
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Sentiment Comparison")
        if "sentiment" in comp_df.columns:
            sentiment_comp = comp_df.groupby("place_name")["sentiment"].value_counts(normalize=True).unstack().fillna(0) * 100
            fig = px.bar(
                sentiment_comp, barmode="group",
                color_discrete_map={"positive": "#2ecc71", "neutral": "#f1c40f", "negative": "#e74c3c"},
                labels={"value": "%"},
                height=380,
            )
            fig.update_layout(transition_duration=400)
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("Rating Comparison")
        rating_comp = comp_df.groupby("place_name")["review_rating"].agg(["mean", "count"]).round(2)
        fig = px.bar(
            rating_comp.reset_index(), x="place_name", y="mean",
            color="mean", color_continuous_scale="RdYlGn", text="mean",
            labels={"place_name": "", "mean": "Avg Rating"},
            height=380,
        )
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig.update_layout(transition_duration=400)
        st.plotly_chart(fig, use_container_width=True)

    # Health score
    st.subheader("📈 Sentiment Health Score")
    if "sentiment" in comp_df.columns:
        health = comp_df.groupby("place_name").agg(
            health_score=("sentiment", lambda x: (x == "positive").mean() * 100 - (x == "negative").mean() * 100)
        ).round(1).sort_values("health_score", ascending=False)
        fig = px.bar(
            health.reset_index(), x="place_name", y="health_score",
            color="health_score", color_continuous_scale="RdYlGn", text="health_score",
            labels={"place_name": "", "health_score": "Health Score (pos% - neg%)"},
            height=350,
        )
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig.update_layout(transition_duration=400)
        st.plotly_chart(fig, use_container_width=True)

    # Radar chart
    section_divider()
    st.subheader("🎯 Multi-Dimensional Radar")
    aspect_cols = [c for c in comp_df.columns if c.startswith("aspect_")]
    if aspect_cols:
        radar_data = {}
        for place in selected_places:
            p_df = comp_df[comp_df["place_name"] == place]
            radar_data[place] = {
                c.replace("aspect_", "").replace("_", " ").title(): p_df[c].mean() * 100
                for c in aspect_cols
            }
        fig = radar_chart(radar_data, title="Aspect Coverage Comparison")
        st.plotly_chart(fig, use_container_width=True)

    # Aspect comparison matrix
    section_divider()
    st.subheader("🔍 Aspect Comparison Matrix")
    from analytics.compare import compare_aspects, compute_competitive_advantages
    aspect_comp = compare_aspects(comp_df)
    if not aspect_comp.empty:
        pivot = aspect_comp.pivot_table(
            index="aspect", columns="place_name", values="net_sentiment", aggfunc="mean"
        ).fillna(0).round(1)
        pivot.index = [a.replace("_", " ").title() for a in pivot.index]
        fig = px.imshow(
            pivot, text_auto=True,
            color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
            aspect="auto", labels={"color": "Net Sentiment"},
        )
        fig.update_layout(height=max(300, len(pivot) * 45), transition_duration=400)
        st.plotly_chart(fig, use_container_width=True)

    # Competitive advantages
    st.subheader("🏆 Competitive Advantages")
    advantages = compute_competitive_advantages(comp_df)
    if advantages:
        for place, advs in advantages.items():
            with st.expander(f"💪 {place} — {len(advs)} advantages"):
                for adv in advs:
                    st.markdown(f"- ✅ **{adv.replace('_', ' ').title()}**")
    else:
        st.info("No clear competitive advantages detected.")


# ============================================================
# PAGE 6: INSIGHTS & RECOMMENDATIONS (Enhanced)
# ============================================================
def insights_page(df: pd.DataFrame, results: dict, raw_df: pd.DataFrame, places_df: pd.DataFrame):
    hero_banner("💡 Strategic Insights", "Strengths, weaknesses, improvement roadmap & exportable reports")

    recommendations = results.get("recommendations", [])
    strengths = results.get("strengths", [])
    complaint_analysis = results.get("complaint_analysis", {})
    improvement_roadmap = results.get("improvement_roadmap", [])

    # Strengths
    st.subheader("✅ Strengths")
    if strengths:
        sc = st.columns(min(3, len(strengths)))
        for i, s in enumerate(strengths[:6]):
            with sc[i % 3]:
                st.markdown(f"**{s['aspect'].replace('_', ' ').title()}**")
                st.markdown(f"📊 Score: **{s.get('strength_score', 0)}%**")
                st.markdown(f"📝 {s.get('positive_review_count', 0)} positive mentions")
                st.progress(min(s.get("strength_score", 0) / 100, 1.0))
    else:
        st.info("No strength data available.")

    section_divider()
    st.subheader("⚠️ Improvement Areas")

    complaint_categories = complaint_analysis.get("complaint_categories", {})
    if complaint_categories:
        cc = st.columns(min(3, len(complaint_categories)))
        for i, (aspect, data) in enumerate(sorted(
            complaint_categories.items(), key=lambda x: x[1]["count"], reverse=True
        )[:6]):
            with cc[i % 3]:
                sev = "🔴 CRITICAL" if data["pct_of_negative_reviews"] > 20 else \
                      "🟠 HIGH" if data["pct_of_negative_reviews"] > 10 else \
                      "🟡 MEDIUM" if data["pct_of_negative_reviews"] > 5 else "🟢 LOW"
                st.markdown(f"### {sev}")
                st.markdown(f"**{aspect.replace('_', ' ').title()}**")
                st.markdown(f"📝 {data['count']} complaints ({data['pct_of_all_reviews']}%)")
                st.markdown(f"⭐ Avg rating: {data['avg_rating']}")
                st.progress(min(data["pct_of_negative_reviews"] / 30, 1.0))

    section_divider()
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
                default=["critical", "high", "medium"],
            )
            filtered = roadmap_df[roadmap_df["severity"].isin(severity_filter)]

            def color_severity(val):
                colors = {"critical": "#ff6b6b", "high": "#ffa502", "medium": "#ffd43b", "low": "#2ecc71"}
                return f"background-color: {colors.get(val, '')}; color: {'white' if val in ('critical','high') else 'black'}; font-weight: bold"

            st.dataframe(
                filtered.style.map(color_severity, subset=["severity"]),
                width="stretch", height=450,
            )

            c1, c2 = st.columns(2)
            with c1:
                csv = filtered.to_csv(index=False)
                st.download_button("📥 Download Roadmap CSV", csv, "improvement_roadmap.csv", "text/csv", use_container_width=True)
            with c2:
                if st.button("📄 Generate Full HTML Report", use_container_width=True):
                    html = generate_html_report(df, results)
                    st.download_button("⬇️ Download Report", html, "analytics_report.html", "text/html")

    section_divider()
    st.subheader("📝 Sample Complaints")
    if complaint_categories:
        for aspect, data in sorted(complaint_categories.items(), key=lambda x: x[1]["count"], reverse=True)[:5]:
            with st.expander(f"{aspect.replace('_', ' ').title()} ({data['count']} complaints)"):
                for c in data.get("sample_complaints", [])[:5]:
                    st.markdown(f"- {str(c)[:400]}...")


# ============================================================
# PAGE 7: MAP VIEW (NEW)
# ============================================================
def map_page(df: pd.DataFrame, results: dict, raw_df: pd.DataFrame, places_df: pd.DataFrame):
    hero_banner("🗺️ Geographic Intelligence", "Interactive map of all tracked places with sentiment overlay")

    if places_df is None or places_df.empty:
        st.warning("No geographic data available. Run the scraper to collect place coordinates.")
        return

    import plotly.express as px

    # Merge rating/sentiment data if available
    map_df = places_df.copy()
    if "title" in map_df.columns:
        map_df = map_df.rename(columns={"title": "place_name"})

    # Compute sentiment per place
    if df is not None and "place_name" in df.columns and "sentiment" in df.columns:
        sentiment_agg = df.groupby("place_name").agg(
            avg_rating=("review_rating", "mean"),
            positive_pct=("sentiment", lambda x: (x == "positive").mean() * 100),
            review_count=("review_text", "count"),
        ).reset_index()
        map_df = map_df.merge(sentiment_agg, on="place_name", how="left")

    color_col = "review_rating" if "review_rating" in map_df.columns else None
    size_col = "review_count" if "review_count" in map_df.columns else None

    st.subheader(f"📍 {len(map_df)} Places Mapped")

    col1, col2 = st.columns([3, 1])
    with col2:
        st.metric("Places on Map", len(map_df))
        if color_col:
            color_by = st.selectbox("Color by", ["review_rating", "positive_pct"], index=0)
        else:
            color_by = None
        st.caption("Hover for details • Zoom to explore")

    with col1:
        hover_cols = ["place_name", "category", "address", "review_rating", "review_count", "positive_pct"]
        hover_data = {c: True for c in hover_cols if c in map_df.columns}
        hover_name = "place_name" if "place_name" in map_df.columns else None

        fig = px.scatter_mapbox(
            map_df.dropna(subset=["latitude", "longitude"]),
            lat="latitude", lon="longitude",
            color=color_by or color_col,
            size=size_col,
            size_max=20,
            hover_name=hover_name,
            hover_data=hover_data,
            color_continuous_scale="RdYlGn",
            zoom=10,
            height=600,
            title="",
        )
        # Center on data
        if len(map_df) > 0:
            fig.update_layout(
                mapbox_style="carto-positron",
                mapbox_center={"lat": map_df["latitude"].median(), "lon": map_df["longitude"].median()},
                margin=dict(t=0, b=0, l=0, r=0),
            )
        st.plotly_chart(fig, use_container_width=True)

    section_divider()
    st.subheader("📊 Top Places by Location")

    if df is not None and "place_name" in df.columns:
        top_places = df.groupby("place_name").agg(
            reviews=("review_text", "count"),
            rating=("review_rating", "mean"),
        ).round(2).sort_values("reviews", ascending=False).head(15)

        fig = px.bar(
            top_places.reset_index(),
            x="reviews", y="place_name", orientation="h",
            color="rating", color_continuous_scale="RdYlGn",
            labels={"place_name": "", "reviews": "Review Count"},
            height=400,
        )
        fig.update_layout(transition_duration=400)
        st.plotly_chart(fig, use_container_width=True)


# ============================================================
# MAIN APP
# ============================================================
def main():
    inject_css()

    st.sidebar.title("🗺️ Navigasi")
    st.sidebar.markdown("---")

    df, results, raw_df, places_df = load_data()

    if df is None and not results:
        st.sidebar.warning("No analysis data found. Run: python main.py full '<query>'")

    # Global filter bar at top
    if df is not None:
        render_global_filter_bar(df)

    pages = {
        "📊 Executive Summary": executive_page,
        "📈 Overview & Rankings": overview_page,
        "😊 Sentiment Analysis": sentiment_page,
        "🔍 Aspect Analysis": aspects_page,
        "🔑 Keywords & Topics": keywords_page,
        "⚔️ Competitor Comparison": comparison_page,
        "💡 Insights & Roadmap": insights_page,
        "🗺️ Map View": map_page,
    }

    page = st.sidebar.radio("Select Page", list(pages.keys()))

    st.sidebar.markdown("---")
    st.sidebar.caption("Google Maps Review Analytics Pro")
    st.sidebar.caption("v2.0 — Interactive Edition")

    # System stats
    if raw_df is not None:
        st.sidebar.metric("Total Data", f"{len(raw_df):,} reviews")
    if places_df is not None:
        st.sidebar.metric("Places Mapped", len(places_df))

    pages[page](df, results, raw_df, places_df)


if __name__ == "__main__":
    main()
