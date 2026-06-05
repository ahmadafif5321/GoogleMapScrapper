"""Reusable animated dashboard components."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, List, Dict, Any
import streamlit.components.v1 as components


def inject_css():
    """Inject custom CSS styles into the Streamlit app."""
    from dashboard.styles import CSS
    components.html(CSS, height=0)


def animated_metric_card(
    label: str, value: str, trend: str = "", trend_value: str = "",
    icon: str = "📊", variant: str = "purple", key: str = ""
):
    """Animated KPI card with gradient background and hover effect."""
    components.html(f"""
    <div class="kpi-card {variant} animate-fade-in-up" id="{key}">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-trend">
            <span class="{'trend-up' if '▲' in trend or '+' in trend else 'trend-down' if '▼' in trend or '-' in trend else ''}">
                {trend} {trend_value}
            </span>
        </div>
    </div>
    """, height=130)


def section_header(title: str):
    """Animated section header."""
    components.html(f"""
    <div class="section-header animate-fade-in">{title}</div>
    """, height=45)


def section_divider():
    """Visual section divider."""
    components.html('<div class="section-divider"></div>', height=2)


def stat_badge(value: str, direction: str = "up"):
    """Small colored badge for trend indicators."""
    components.html(f'<span class="stat-badge {direction}">{value}</span>', height=28)


def insight_card(
    title: str, description: str, severity: str = "medium",
    metrics: Optional[Dict[str, str]] = None
):
    """Animated insight card with severity-based left border color."""
    metrics_html = ""
    if metrics:
        metrics_html = "".join(
            f'<span style="margin-right:16px;font-weight:600;">{k}: {v}</span>'
            for k, v in metrics.items()
        )
    components.html(f"""
    <div class="insight-card {severity} animate-fade-in-up">
        <strong style="font-size:16px;">{title}</strong>
        <p style="margin:8px 0;color:#555;font-size:13px;">{description}</p>
        {metrics_html}
    </div>
    """, height=100 if not metrics else 120)


def loading_overlay():
    """Animated loading spinner."""
    components.html("""
    <div style="text-align:center;padding:40px;">
        <div class="loading-spinner"></div>
        <p style="margin-top:12px;color:#888;">Processing...</p>
    </div>
    """, height=100)


def hero_banner(title: str, subtitle: str):
    """Gradient hero banner at top of the page."""
    components.html(f"""
    <div class="hero-banner animate-fade-in">
        <h1>{title}</h1>
        <p>{subtitle}</p>
    </div>
    """, height=110)


def map_container(html_content: str):
    """Styled map container."""
    components.html(f"""
    <div class="map-container">{html_content}</div>
    """, height=600)


def apply_global_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply global filters from session state to the dataframe."""
    if "filter_rating_min" not in st.session_state:
        st.session_state.filter_rating_min = 1
    if "filter_rating_max" not in st.session_state:
        st.session_state.filter_rating_max = 5
    if "filter_sentiment" not in st.session_state:
        st.session_state.filter_sentiment = []
    if "filter_places" not in st.session_state:
        st.session_state.filter_places = []
    if "filter_categories" not in st.session_state:
        st.session_state.filter_categories = []

    filtered = df.copy()

    if "review_rating" in filtered.columns:
        filtered = filtered[
            (filtered["review_rating"] >= st.session_state.filter_rating_min) &
            (filtered["review_rating"] <= st.session_state.filter_rating_max)
        ]

    if st.session_state.filter_sentiment and "sentiment" in filtered.columns:
        filtered = filtered[filtered["sentiment"].isin(st.session_state.filter_sentiment)]

    if st.session_state.filter_places and "place_name" in filtered.columns:
        filtered = filtered[filtered["place_name"].isin(st.session_state.filter_places)]

    if st.session_state.filter_categories and "place_category" in filtered.columns:
        filtered = filtered[filtered["place_category"].isin(st.session_state.filter_categories)]

    return filtered


def render_global_filter_bar(df: pd.DataFrame):
    """Render collapsible global filter controls."""
    with st.expander("🎛️ Global Filters", expanded=False):
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            if "review_rating" in df.columns:
                st.session_state.filter_rating_min = st.slider(
                    "Min Rating", 1, 5, st.session_state.get("filter_rating_min", 1)
                )
        with c2:
            if "review_rating" in df.columns:
                st.session_state.filter_rating_max = st.slider(
                    "Max Rating", 1, 5, st.session_state.get("filter_rating_max", 5)
                )
        with c3:
            if "sentiment" in df.columns:
                sentiments = sorted(df["sentiment"].dropna().unique())
                st.session_state.filter_sentiment = st.multiselect(
                    "Sentiment", sentiments,
                    default=st.session_state.get("filter_sentiment", sentiments)
                )
        with c4:
            if "place_category" in df.columns:
                categories = sorted(df["place_category"].dropna().unique())
                st.session_state.filter_categories = st.multiselect(
                    "Category", categories,
                    default=st.session_state.get("filter_categories", [])
                )

        if "place_name" in df.columns:
            places = sorted(df["place_name"].unique())
            st.session_state.filter_places = st.multiselect(
                "Places", places,
                default=st.session_state.get("filter_places", []),
                placeholder="All places (select to filter)"
            )


def create_sentiment_gauge(value: float, title: str = "") -> go.Figure:
    """Create a sentiment gauge chart."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title},
        gauge={
            "axis": {"range": [-100, 100]},
            "bar": {"color": "darkblue"},
            "steps": [
                {"range": [-100, -30], "color": "#e74c3c"},
                {"range": [-30, 30], "color": "#f1c40f"},
                {"range": [30, 100], "color": "#2ecc71"},
            ],
        },
    ))
    fig.update_layout(height=250, margin=dict(t=30, b=10, l=10, r=10))
    return fig


def animated_chart_container(fig, key: str = ""):
    """Display a Plotly chart with animations enabled."""
    fig.update_layout(
        transition_duration=500,
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def comparison_chart(
    df: pd.DataFrame, x: str, y: str, color: str = None,
    title: str = "", orientation: str = "v"
):
    """Create an animated comparison bar chart."""
    if orientation == "h":
        fig = px.bar(
            df.sort_values(y), x=y, y=x, orientation="h",
            color=color or y,
            color_continuous_scale="RdYlGn",
            title=title,
        )
    else:
        fig = px.bar(
            df, x=x, y=y,
            color=color or y,
            color_continuous_scale="RdYlGn",
            title=title,
            text=y,
        )
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(transition_duration=500)
    return fig


def feedback_toast(message: str, type: str = "info"):
    """Show a brief feedback toast-style message."""
    emoji = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}.get(type, "ℹ️")
    components.html(f"""
    <div style="
        background: #f0f8ff;
        border-left: 4px solid #667eea;
        padding: 8px 16px;
        border-radius: 4px;
        margin: 8px 0;
        font-size: 13px;
        animation: fadeIn 0.3s ease-out;
    ">{emoji} {message}</div>
    """, height=36)


def radar_chart(places_data: Dict[str, Dict[str, float]], title: str = "") -> go.Figure:
    """Create a radar/spider chart for multi-dimensional comparison."""
    fig = go.Figure()
    categories = list(next(iter(places_data.values())).keys())

    for place, values in places_data.items():
        fig.add_trace(go.Scatterpolar(
            r=[values.get(c, 0) for c in categories],
            theta=categories,
            fill="toself",
            name=place,
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title=title,
        showlegend=True,
        height=450,
    )
    return fig


def generate_html_report(
    df: pd.DataFrame, results: dict, places_summary: pd.DataFrame = None
) -> str:
    """Generate a standalone HTML report that can be saved/shared."""
    stats = results.get("stats", {})
    sentiment_summary = results.get("sentiment_summary", {})
    aspect_summary = results.get("aspect_summary", {})

    total_reviews = stats.get("total_reviews", "N/A")
    total_places = stats.get("total_places", "N/A")
    avg_rating = stats.get("avg_rating", "N/A")

    pos_pct = 0
    neg_pct = 0
    if "sentiment" in df.columns:
        s = df["sentiment"].value_counts(normalize=True) * 100
        pos_pct = s.get("positive", 0)
        neg_pct = s.get("negative", 0)

    top_places = ""
    if sentiment_summary:
        ranking = sorted(
            sentiment_summary.items(),
            key=lambda x: x[1].get("positive_pct", 0), reverse=True
        )[:10]
        top_places = "".join(
            f'<tr><td>{p}</td><td>{d.get("positive_pct",0):.1f}%</td>'
            f'<td>{d.get("negative_pct",0):.1f}%</td>'
            f'<td>{d.get("avg_review_rating",0):.2f}</td>'
            f'<td>{d.get("total_reviews",0)}</td></tr>'
            for p, d in ranking
        )

    top_complaints = ""
    complaints = results.get("complaint_analysis", {}).get("complaint_categories", {})
    if complaints:
        sorted_complaints = sorted(
            complaints.items(), key=lambda x: x[1]["count"], reverse=True
        )[:10]
        top_complaints = "".join(
            f'<tr><td>{a.replace("_"," ").title()}</td><td>{d["count"]}</td>'
            f'<td>{d.get("pct_of_all_reviews","")}%</td><td>{d["avg_rating"]}</td></tr>'
            for a, d in sorted_complaints
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Google Maps Review Analytics - Executive Report</title>
<style>
  * {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
  body {{ max-width: 1000px; margin: 0 auto; padding: 40px 20px; background: #f8f9fa; color: #212529; }}
  .hero {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 40px; border-radius: 16px; margin-bottom: 32px; }}
  .hero h1 {{ font-size: 28px; margin: 0 0 8px 0; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }}
  .kpi {{ background: white; padding: 24px; border-radius: 12px; text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }}
  .kpi .value {{ font-size: 32px; font-weight: 800; }}
  .kpi .label {{ font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }}
  th {{ background: #667eea; color: white; padding: 12px 16px; text-align: left; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }}
  td {{ padding: 12px 16px; border-bottom: 1px solid #eee; }}
  tr:last-child td {{ border-bottom: none; }}
  .section {{ background: white; padding: 28px; border-radius: 16px; margin-bottom: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }}
  .section h2 {{ margin-top: 0; color: #333; }}
  .badge-green {{ background: #d4edda; color: #155724; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
  .badge-red {{ background: #f8d7da; color: #721c24; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
  .footer {{ text-align: center; color: #aaa; font-size: 12px; margin-top: 40px; }}
</style>
</head>
<body>
<div class="hero">
  <h1>📊 Google Maps Review Analytics</h1>
  <p>Executive Summary Report — Generated from {total_places} places, {total_reviews} reviews</p>
</div>
<div class="kpi-grid">
  <div class="kpi"><div class="value">{total_reviews}</div><div class="label">Total Reviews</div></div>
  <div class="kpi"><div class="value">{total_places}</div><div class="label">Places Analyzed</div></div>
  <div class="kpi"><div class="value">{avg_rating}</div><div class="label">Avg Rating</div></div>
  <div class="kpi"><div class="value">{pos_pct:.1f}%</div><div class="label">Positive Reviews</div></div>
</div>
<div class="section">
  <h2>🏆 Top 10 Places by Sentiment</h2>
  <table><tr><th>Place</th><th>Positive %</th><th>Negative %</th><th>Avg Rating</th><th>Reviews</th></tr>{top_places}</table>
</div>
<div class="section">
  <h2>⚠️ Top Complaint Categories</h2>
  <table><tr><th>Aspect</th><th>Complaints</th><th>% of Reviews</th><th>Avg Rating</th></tr>{top_complaints}</table>
</div>
<div class="section">
  <h2>📋 Recommendations</h2>
  <table><tr><th>Priority</th><th>Aspect</th><th>Action</th><th>Severity</th></tr>
  {"".join(f'<tr><td>{i+1}</td><td>{r.get("aspect","").replace("_"," ").title()}</td><td>{r.get("action","")}</td><td><span class="badge-{"red" if r.get("severity") in ("critical","high") else "green"}">{r.get("severity","")}</span></td></tr>' for i, r in enumerate(results.get("recommendations",[])[:10]))}
  </table>
</div>
<div class="footer">Generated by GoogleMapScrapper — google-maps-review-analytics</div>
</body>
</html>"""
    return html
