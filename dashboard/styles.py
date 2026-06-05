"""Custom CSS for professional dashboard styling and animations."""

CSS = """
<style>
/* ===== FONTS & BASE ===== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

* { font-family: 'Inter', sans-serif; }

/* ===== ANIMATIONS ===== */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}
@keyframes slideInLeft {
    from { opacity: 0; transform: translateX(-30px); }
    to { opacity: 1; transform: translateX(0); }
}
@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.03); }
}
@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}
@keyframes glow {
    0%, 100% { box-shadow: 0 0 5px rgba(46, 204, 113, 0.3); }
    50% { box-shadow: 0 0 20px rgba(46, 204, 113, 0.6); }
}
@keyframes countUp {
    from { opacity: 0; transform: scale(0.8); }
    to { opacity: 1; transform: scale(1); }
}
@keyframes borderGlow {
    0%, 100% { border-color: rgba(46, 204, 113, 0.2); }
    50% { border-color: rgba(46, 204, 113, 0.6); }
}
@keyframes rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}
@keyframes barGrow {
    from { width: 0%; }
}
@keyframes floatUp {
    0% { opacity: 0; transform: translateY(40px) scale(0.95); }
    100% { opacity: 1; transform: translateY(0) scale(1); }
}

/* ===== ANIMATION CLASSES ===== */
.animate-fade-in { animation: fadeIn 0.6s ease-out; }
.animate-fade-in-up { animation: fadeInUp 0.6s ease-out; }
.animate-slide-left { animation: slideInLeft 0.5s ease-out; }
.animate-pulse { animation: pulse 2s infinite; }
.animate-float-up { animation: floatUp 0.7s cubic-bezier(0.16, 1, 0.3, 1); }

/* Staggered children */
.stagger-1 { animation-delay: 0.1s; }
.stagger-2 { animation-delay: 0.2s; }
.stagger-3 { animation-delay: 0.3s; }
.stagger-4 { animation-delay: 0.4s; }

/* ===== KPI CARDS ===== */
.kpi-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 16px;
    padding: 24px 20px;
    color: white;
    position: relative;
    overflow: hidden;
    animation: fadeInUp 0.5s ease-out;
    box-shadow: 0 8px 32px rgba(102, 126, 234, 0.25);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    height: 100%;
}
.kpi-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(102, 126, 234, 0.4);
}
.kpi-card.purple { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.kpi-card.green  { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
.kpi-card.orange { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
.kpi-card.blue   { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
.kpi-card.dark   { background: linear-gradient(135deg, #434343 0%, #000000 100%); }

.kpi-card .kpi-label {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    opacity: 0.85;
    font-weight: 600;
    margin-bottom: 8px;
}
.kpi-card .kpi-value {
    font-size: 36px;
    font-weight: 800;
    line-height: 1;
    animation: countUp 0.6s ease-out;
}
.kpi-card .kpi-trend {
    font-size: 13px;
    opacity: 0.9;
    margin-top: 6px;
    font-weight: 500;
}
.kpi-card .kpi-icon {
    position: absolute;
    top: 16px;
    right: 16px;
    font-size: 28px;
    opacity: 0.3;
}

/* ===== SECTION HEADERS ===== */
.section-header {
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 3px solid #667eea;
    display: inline-block;
    animation: fadeIn 0.5s ease-out;
}
.section-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #e0e0e0, transparent);
    margin: 28px 0;
}

/* ===== FILTER BAR ===== */
.filter-bar {
    background: linear-gradient(135deg, #f8f9fa, #e9ecef);
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 24px;
    border: 1px solid #dee2e6;
    animation: slideInLeft 0.5s ease-out;
}

/* ===== INSIGHT CARDS ===== */
.insight-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    border: 1px solid #e0e0e0;
    transition: all 0.3s ease;
    animation: fadeInUp 0.5s ease-out;
}
.insight-card:hover {
    box-shadow: 0 6px 24px rgba(0,0,0,0.08);
    transform: translateY(-2px);
}
.insight-card.critical { border-left: 4px solid #e74c3c; }
.insight-card.high     { border-left: 4px solid #e67e22; }
.insight-card.medium   { border-left: 4px solid #f1c40f; }
.insight-card.low      { border-left: 4px solid #2ecc71; }

/* ===== STAT BADGE ===== */
.stat-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}
.stat-badge.up   { background: #d4edda; color: #155724; }
.stat-badge.down { background: #f8d7da; color: #721c24; }
.stat-badge.neutral { background: #e2e3e5; color: #383d41; }

/* ===== PROGRESS BAR ENHANCED ===== */
.progress-bar-enhanced {
    height: 8px;
    background: #e9ecef;
    border-radius: 4px;
    overflow: hidden;
    margin: 6px 0;
}
.progress-bar-enhanced .fill {
    height: 100%;
    border-radius: 4px;
    background: linear-gradient(90deg, #667eea, #764ba2);
    animation: barGrow 1s ease-out;
}
.progress-bar-enhanced .fill.green  { background: linear-gradient(90deg, #11998e, #38ef7d); }
.progress-bar-enhanced .fill.orange { background: linear-gradient(90deg, #f093fb, #f5576c); }
.progress-bar-enhanced .fill.blue   { background: linear-gradient(90deg, #4facfe, #00f2fe); }

/* ===== LOADING ===== */
.loading-spinner {
    display: inline-block;
    width: 40px;
    height: 40px;
    border: 3px solid #f3f3f3;
    border-top: 3px solid #667eea;
    border-radius: 50%;
    animation: rotate 0.8s linear infinite;
}

/* ===== MAP CONTAINER ===== */
.map-container {
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 4px 24px rgba(0,0,0,0.1);
    animation: fadeIn 0.8s ease-out;
    border: 2px solid #e0e0e0;
}

/* ===== TOOLTIP ===== */
.tooltip-trigger {
    cursor: help;
    border-bottom: 1px dotted #666;
}

/* ===== SCROLLBAR ===== */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 4px; }
::-webkit-scrollbar-thumb { background: #888; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #555; }

/* ===== RANKING TABLE ===== */
.ranking-gold   { color: #ffd700; font-weight: 700; }
.ranking-silver { color: #c0c0c0; font-weight: 700; }
.ranking-bronze { color: #cd7f32; font-weight: 700; }

/* ===== HERO BANNER ===== */
.hero-banner {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f5576c 100%);
    background-size: 200% 200%;
    animation: shimmer 3s ease infinite;
    border-radius: 16px;
    padding: 32px;
    color: white;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}
.hero-banner h1 {
    font-size: 28px;
    font-weight: 800;
    margin: 0;
}
.hero-banner p {
    font-size: 14px;
    opacity: 0.9;
    margin: 8px 0 0 0;
}

/* ===== METRIC TREND ARROW ===== */
.trend-up { color: #2ecc71; }
.trend-down { color: #e74c3c; }

/* Hide Streamlit branding */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }
</style>
"""
