"""
ui/theme.py - Stadium X visual design system and theme styles.
Cinematic sports broadcasting aesthetics with dark glassmorphism and electric accents.
"""

import base64
import functools
from pathlib import Path

# Palette definition
COLOR_BG_DARK = "#040814"
COLOR_BG_CARD = "rgba(10, 20, 42, 0.65)"
COLOR_BG_CARD_HOVER = "rgba(16, 32, 64, 0.85)"
COLOR_ORANGE = "#ff6a00"
COLOR_ORANGE_GLOW = "rgba(255, 106, 0, 0.45)"
COLOR_CYAN = "#00f0ff"
COLOR_CYAN_GLOW = "rgba(0, 240, 255, 0.4)"
COLOR_TEXT_PRIMARY = "#f8fafc"
COLOR_TEXT_MUTED = "#94a3b8"
COLOR_BORDER = "rgba(255, 255, 255, 0.1)"
COLOR_BORDER_ORANGE = "rgba(255, 106, 0, 0.35)"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIR = PROJECT_ROOT / "assets" / "images"

IMAGE_MAP = {
    "overview": "ipl_overview.jpg",
    "teams": "rcb_team.jpg",
    "seasons": "ipl_season.jpg",
    "batting": "virat_kohli_orange_cap.jpg",
    "bowling": "chahal_bhuvneshwar.jpg",
    "match": "rcb_trophy.jpg",
    "venues": "chinnaswamy_stadium.jpg",
}

@functools.lru_cache(maxsize=16)
def get_image_base64(image_key: str) -> str:
    """Load and base64-encode an image from assets/images/ with caching."""
    filename = IMAGE_MAP.get(image_key, image_key)
    path = IMAGE_DIR / filename
    if path.exists():
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/jpeg;base64,{encoded}"
    return ""

def get_page_background_css(image_key: str) -> str:
    """Inject dynamic page-level background image with dark cinematic overlay."""
    b64 = get_image_base64(image_key)
    if not b64:
        return ""
    return f"""<style>
.stApp {{
    background: 
        linear-gradient(180deg, rgba(4, 8, 20, 0.88) 0%, rgba(6, 12, 28, 0.94) 45%, rgba(3, 6, 17, 0.98) 100%),
        url("{b64}") no-repeat center top / cover fixed !important;
}}
</style>"""

def render_stats_banner(stats: list) -> str:
    """
    Renders the standardized horizontal statistics ribbon near the bottom
    of the hero section. stats is a list of (value, label) tuples.
    """
    items_html = []
    for idx, (val, lbl) in enumerate(stats):
        if idx > 0:
            items_html.append('<div style="width:1px;height:36px;background:rgba(255,255,255,0.12);margin:0 0.25rem;"></div>')
        items_html.append(
            f'<div class="hero-stat-item">'
            f'<span class="hero-stat-val">{val}</span>'
            f'<span class="hero-stat-lbl">{lbl}</span>'
            f'</div>'
        )
    return f'<div class="hero-stats-banner">{"".join(items_html)}</div>'


def render_stadium_hero(image_key: str, badge_text: str, title_html: str, tagline_html: str, stats_banner_html: str = "") -> str:
    """
    Renders the cinematic STADIUM X hero banner card with real background photograph,
    dark glass overlay, bold typography, glowing accents, and bottom statistics ribbon.
    """
    b64 = get_image_base64(image_key)
    bg_style = f"background-image: linear-gradient(135deg, rgba(4, 8, 20, 0.90) 0%, rgba(4, 8, 20, 0.65) 55%, rgba(4, 8, 20, 0.92) 100%), url('{b64}');" if b64 else ""

    html = (
        f'<div class="stadium-hero-banner" style="{bg_style}">'
        f'<div class="hero-top-content">'
        f'<div class="stadium-brand-badge">{badge_text}</div>'
        f'<div class="stadium-hero-title">{title_html}</div>'
        f'<div class="stadium-hero-tagline">{tagline_html}</div>'
        f'</div>'
        f'{stats_banner_html}'
        '</div>'
    )
    return html


STADIUM_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800;900&family=JetBrains+Mono:wght@400;600;700&display=swap');

/* Global Reset & Typography */
html, body, [class*="css"], .stApp {
    font-family: 'Outfit', sans-serif !important;
    color: #f1f5f9;
}

/* Fix Streamlit Top Header & White Bar */
header[data-testid="stHeader"] {
    background: transparent !important;
    background-color: transparent !important;
}

[data-testid="stToolbar"] {
    right: 1.5rem;
    top: 0.5rem;
}

[data-testid="stDecoration"] {
    display: none !important;
}

/* ==========================================================================
   1. REMOVE STREAMLIT MPA AUTO-GENERATED SIDEBAR NAVIGATION
   ========================================================================== */
[data-testid="stSidebarNav"],
[data-testid="stSidebarNavItems"],
[data-testid="stSidebarNavSeparator"],
ul[data-testid="stSidebarNavItems"],
div[data-testid="stSidebarNav"] {
    display: none !important;
    height: 0 !important;
    max-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
    visibility: hidden !important;
    pointer-events: none !important;
}

[data-testid="stSidebarHeader"] {
    padding-top: 0.75rem !important;
    padding-bottom: 0 !important;
}

/* ==========================================================================
   2. STADIUM X SIDEBAR THEME & CONTAINER
   ========================================================================== */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #040814 0%, #060e22 50%, #030611 100%) !important;
    border-right: 1px solid rgba(255, 106, 0, 0.25) !important;
    box-shadow: 12px 0 35px rgba(0, 0, 0, 0.7) !important;
    min-width: 325px !important;
    max-width: 350px !important;
}

section[data-testid="stSidebar"] > div:first-child {
    background: transparent !important;
}

[data-testid="stSidebarContent"] {
    padding: 1.5rem 1.25rem 2.5rem 1.25rem !important;
    scrollbar-width: thin;
    scrollbar-color: rgba(255, 106, 0, 0.3) transparent;
}

[data-testid="stSidebarContent"]::-webkit-scrollbar {
    width: 5px;
}
[data-testid="stSidebarContent"]::-webkit-scrollbar-thumb {
    background: rgba(255, 106, 0, 0.3);
    border-radius: 4px;
}

/* Branding elements in sidebar */
.sidebar-brand-box {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 0.85rem;
    padding: 0.25rem 0.25rem;
}

.sidebar-logo-icon {
    background: linear-gradient(135deg, #ff6a00 0%, #ff3d00 100%);
    border-radius: 12px;
    width: 46px;
    height: 46px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 20px rgba(255, 106, 0, 0.45);
    font-size: 1.45rem;
    flex-shrink: 0;
}

.sidebar-brand-title {
    font-size: 1.35rem;
    font-weight: 900;
    letter-spacing: -0.02em;
    color: #ffffff;
    line-height: 1.1;
}

.sidebar-brand-title span {
    color: #ff6a00;
}

.sidebar-brand-sub {
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.18em;
    color: #ff8c38;
    text-transform: uppercase;
    margin-top: 2px;
}

.sidebar-status-row {
    margin: 0.5rem 0 0.35rem;
}

.sidebar-tagline {
    font-size: 0.73rem;
    font-weight: 600;
    color: #64748b;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin: 0.4rem 0 1rem 0;
    line-height: 1.4;
}

.sidebar-divider {
    height: 1px;
    background: linear-gradient(90deg, rgba(255, 106, 0, 0.4) 0%, rgba(255, 255, 255, 0.08) 60%, transparent 100%);
    margin: 1.1rem 0 1.25rem 0;
}

.status-dot-active {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 10px #22c55e;
    margin-right: 8px;
    animation: statusPulse 2s infinite ease-in-out;
}

@keyframes statusPulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.85); }
}

.nav-indicator-accent {
    display: inline-block;
    width: 4px;
    height: 14px;
    border-radius: 2px;
    background: #00f0ff;
    box-shadow: 0 0 8px rgba(0, 240, 255, 0.6);
    margin-right: 8px;
}

.arena-nav-header {
    font-size: 0.78rem;
    font-weight: 800;
    letter-spacing: 0.15em;
    color: #00f0ff;
    text-transform: uppercase;
    margin-bottom: 0.85rem;
    display: flex;
    align-items: center;
}

/* ==========================================================================
   3. ARENA NAVIGATION RADIO INTERFACE
   ========================================================================== */
div[data-testid="stRadio"] {
    margin-top: 0.25rem !important;
    margin-bottom: 1.25rem !important;
}

div[data-testid="stRadio"] > label {
    display: none !important;
}

div[data-testid="stRadio"] div[role="radiogroup"] {
    display: flex !important;
    flex-direction: column !important;
    gap: 9px !important;
}

div[data-testid="stRadio"] div[role="radiogroup"] > label[data-baseweb="radio"] {
    display: flex !important;
    align-items: center !important;
    padding: 11px 16px !important;
    border-radius: 12px !important;
    background: rgba(15, 23, 42, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.07) !important;
    cursor: pointer !important;
    transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1) !important;
    margin: 0 !important;
    box-sizing: border-box !important;
    width: 100% !important;
    backdrop-filter: blur(10px) !important;
}

div[data-testid="stRadio"] div[role="radiogroup"] > label[data-baseweb="radio"]::before {
    content: '';
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: rgba(148, 163, 184, 0.4);
    margin-right: 12px;
    flex-shrink: 0;
    transition: all 0.22s ease;
}

div[data-testid="stRadio"] div[role="radiogroup"] > label[data-baseweb="radio"]:hover::before {
    background: #ff8c38;
    box-shadow: 0 0 8px rgba(255, 140, 56, 0.8);
    transform: scale(1.15);
}

div[data-testid="stRadio"] div[role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked)::before {
    background: #ff6a00;
    box-shadow: 0 0 12px #ff6a00, 0 0 4px #ffffff;
    transform: scale(1.3);
}

div[data-testid="stRadio"] div[role="radiogroup"] > label[data-baseweb="radio"] div[data-testid="stRadioButton"] {
    display: none !important;
}

div[data-testid="stRadio"] div[role="radiogroup"] > label[data-baseweb="radio"] [data-testid="stMarkdownContainer"] p,
div[data-testid="stRadio"] div[role="radiogroup"] > label[data-baseweb="radio"] span {
    font-size: 15.5px !important;
    font-weight: 600 !important;
    color: #cbd5e1 !important;
    letter-spacing: -0.01em !important;
    line-height: 1.35 !important;
    transition: color 0.2s ease !important;
    white-space: normal !important;
    word-break: break-word !important;
}

div[data-testid="stRadio"] div[role="radiogroup"] > label[data-baseweb="radio"]:hover {
    background: rgba(255, 106, 0, 0.12) !important;
    border-color: rgba(255, 106, 0, 0.4) !important;
    transform: translateX(4px) !important;
    box-shadow: 0 4px 15px rgba(255, 106, 0, 0.15) !important;
}

div[data-testid="stRadio"] div[role="radiogroup"] > label[data-baseweb="radio"]:hover [data-testid="stMarkdownContainer"] p,
div[data-testid="stRadio"] div[role="radiogroup"] > label[data-baseweb="radio"]:hover span {
    color: #ffffff !important;
}

div[data-testid="stRadio"] div[role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) {
    background: linear-gradient(90deg, rgba(255, 106, 0, 0.24) 0%, rgba(255, 106, 0, 0.08) 100%) !important;
    border: 1px solid rgba(255, 106, 0, 0.65) !important;
    box-shadow: 0 4px 18px rgba(255, 106, 0, 0.22), inset 0 0 10px rgba(255, 106, 0, 0.12) !important;
    transform: translateX(5px) !important;
}

div[data-testid="stRadio"] div[role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) [data-testid="stMarkdownContainer"] p,
div[data-testid="stRadio"] div[role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) span {
    color: #ffffff !important;
    font-weight: 800 !important;
    text-shadow: 0 0 12px rgba(255, 106, 0, 0.5) !important;
}

div[data-testid="stRadio"] div[role="radiogroup"] > label[data-baseweb="radio"] input:checked + div {
    border-color: #ff6a00 !important;
    background-color: #ff6a00 !important;
    box-shadow: 0 0 10px #ff6a00 !important;
}

/* Main App Container Styling & Background */
.stApp {
    background-color: #040814 !important;
    background-image: 
        radial-gradient(circle at 50% -10%, rgba(255, 106, 0, 0.22) 0%, transparent 60%),
        radial-gradient(circle at 10% 40%, rgba(0, 240, 255, 0.08) 0%, transparent 45%),
        radial-gradient(circle at 90% 70%, rgba(255, 106, 0, 0.09) 0%, transparent 50%),
        linear-gradient(180deg, #040814 0%, #080f24 50%, #030611 100%) !important;
    background-attachment: fixed !important;
}

.main .block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
    max-width: 97% !important;
    width: 97% !important;
    margin-left: auto !important;
    margin-right: auto !important;
}

/* Header & Stadium X Branding */
.stadium-hero-banner {
    position: relative;
    border-radius: 20px;
    overflow: hidden;
    background-size: cover;
    background-position: center top;
    background-repeat: no-repeat;
    border: 1px solid rgba(255, 106, 0, 0.35);
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.7), 0 0 35px rgba(255, 106, 0, 0.12);
    padding: 3rem 2.5rem 2.25rem 2.5rem;
    margin-bottom: 2rem;
    min-height: 540px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-sizing: border-box;
    animation: fadeInHero 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.hero-top-content {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
}

@keyframes fadeInHero {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes pulseGlow {
    0%, 100% { box-shadow: 0 0 15px rgba(255, 106, 0, 0.2); }
    50% { box-shadow: 0 0 25px rgba(255, 106, 0, 0.55); }
}

.stadium-brand-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    background: rgba(255, 106, 0, 0.12);
    border: 1px solid rgba(255, 106, 0, 0.4);
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    color: #ff8c38;
    text-transform: uppercase;
    box-shadow: 0 0 15px rgba(255, 106, 0, 0.2);
    animation: pulseGlow 3s infinite ease-in-out;
}

.stadium-hero-title {
    font-size: 3.2rem;
    font-weight: 900;
    letter-spacing: -0.02em;
    line-height: 1.1;
    margin: 0.6rem 0 0.4rem;
    background: linear-gradient(135deg, #ffffff 30%, #ff8c38 70%, #ff5500 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 10px 30px rgba(255, 106, 0, 0.15);
}

.stadium-hero-tagline {
    font-size: 1.15rem;
    font-weight: 400;
    color: #94a3b8;
    max-width: 820px;
    line-height: 1.6;
    margin-bottom: 1.5rem;
}

.hero-stats-banner {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 1.75rem;
    padding: 1.15rem 2rem;
    background: rgba(15, 23, 42, 0.82);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
    margin-top: 1.5rem;
    margin-bottom: 0 !important;
    box-shadow: 0 12px 35px rgba(0, 0, 0, 0.5), 0 0 1px rgba(255, 106, 0, 0.3);
    width: fit-content;
    max-width: 100%;
}

@media (max-width: 1024px) {
    .stadium-hero-banner {
        min-height: 480px;
        padding: 2.25rem 1.75rem 1.75rem;
    }
    .stadium-hero-title {
        font-size: 2.5rem !important;
    }
    .hero-stats-banner {
        gap: 1.25rem;
        padding: 1rem 1.25rem;
    }
}

@media (max-width: 640px) {
    .stadium-hero-banner {
        min-height: 420px;
        padding: 1.75rem 1.25rem 1.25rem;
    }
    .stadium-hero-title {
        font-size: 1.85rem !important;
    }
    .hero-stats-banner {
        gap: 0.75rem;
        padding: 0.75rem 1rem;
    }
}

.hero-stat-item {
    display: flex;
    flex-direction: column;
}
.hero-stat-val {
    font-size: 1.5rem;
    font-weight: 900;
    color: #00f0ff;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: -0.02em;
    text-shadow: 0 0 12px rgba(0, 240, 255, 0.3);
}
.hero-stat-lbl {
    font-size: 0.72rem;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 2px;
}

/* Glassmorphism Metric / KPI Cards */
.kpi-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.25rem;
    margin-bottom: 2rem;
}

.kpi-card-stadium {
    position: relative;
    background: linear-gradient(145deg, rgba(16, 28, 54, 0.7) 0%, rgba(8, 16, 32, 0.8) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 1.1rem 1.25rem;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.kpi-card-stadium::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #ff6a00, transparent);
    opacity: 0.8;
}

.kpi-card-stadium.blue-accent::before {
    background: linear-gradient(90deg, #00f0ff, transparent);
}

.kpi-card-stadium:hover {
    transform: translateY(-4px);
    border-color: rgba(255, 106, 0, 0.3);
    box-shadow: 0 16px 40px rgba(255, 106, 0, 0.15), 0 0 20px rgba(255, 106, 0, 0.08);
}

.kpi-card-stadium.blue-accent:hover {
    border-color: rgba(0, 240, 255, 0.35);
    box-shadow: 0 16px 40px rgba(0, 240, 255, 0.15), 0 0 20px rgba(0, 240, 255, 0.08);
}

.kpi-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}

.kpi-title {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: #94a3b8;
    text-transform: uppercase;
}

.kpi-icon {
    font-size: 1rem;
    opacity: 0.85;
}

.kpi-numeric {
    font-size: 1.65rem;
    font-weight: 900;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.2;
    color: #ffffff;
    margin-bottom: 0.3rem;
    white-space: nowrap;
    letter-spacing: -0.02em;
    text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
}

.kpi-numeric.highlight-orange {
    background: linear-gradient(135deg, #ffffff 40%, #ff8c38 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.kpi-numeric.highlight-cyan {
    background: linear-gradient(135deg, #ffffff 40%, #00f0ff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.kpi-subtext {
    font-size: 0.74rem;
    color: #64748b;
}

/* Glass Section Container */
.stadium-glass-panel {
    background: linear-gradient(145deg, rgba(14, 25, 48, 0.65) 0%, rgba(7, 14, 28, 0.75) 100%);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 18px;
    padding: 1.75rem;
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    box-shadow: 0 10px 35px rgba(0, 0, 0, 0.4);
    margin-bottom: 2rem;
}

.panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    padding-bottom: 1rem;
    margin-bottom: 1.25rem;
}

.panel-title {
    font-size: 1.25rem;
    font-weight: 800;
    color: #f8fafc;
    letter-spacing: -0.01em;
    display: flex;
    align-items: center;
    gap: 10px;
}

.panel-badge {
    background: rgba(255, 106, 0, 0.15);
    color: #ff9142;
    border: 1px solid rgba(255, 106, 0, 0.3);
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
}

/* Sidebar Customization */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #060b18 0%, #0a1329 100%) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.07) !important;
}

[data-testid="stSidebar"] hr {
    border-color: rgba(255, 255, 255, 0.08) !important;
}

/* Streamlit Tabs Styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: rgba(10, 18, 36, 0.8);
    padding: 6px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.06);
}

.stTabs [data-baseweb="tab"] {
    height: 42px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.85rem;
    color: #94a3b8;
    background-color: transparent;
    border: none;
    padding: 0 16px;
    transition: all 0.2s ease;
}

.stTabs [data-baseweb="tab"]:hover {
    color: #f8fafc;
    background-color: rgba(255, 255, 255, 0.05);
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #ff6a00 0%, #e65100 100%) !important;
    color: #ffffff !important;
    font-weight: 700;
    box-shadow: 0 4px 15px rgba(255, 106, 0, 0.35);
}

/* Custom Match Scorecard Display */
.stadium-scorecard {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: linear-gradient(135deg, rgba(16, 28, 54, 0.8) 0%, rgba(9, 17, 34, 0.9) 100%);
    border: 1px solid rgba(255, 106, 0, 0.25);
    border-radius: 14px;
    padding: 1.25rem 1.75rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
}

.team-box {
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.team-name {
    font-size: 1.2rem;
    font-weight: 800;
    color: #ffffff;
}
.team-score {
    font-size: 1.5rem;
    font-weight: 900;
    font-family: 'JetBrains Mono', monospace;
    color: #ff9142;
}

.vs-badge {
    padding: 4px 12px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 9999px;
    font-weight: 800;
    font-size: 0.8rem;
    color: #64748b;
}

/* Streamlit Selectboxes & Sliders */
div[data-baseweb="select"] > div {
    background-color: rgba(15, 23, 42, 0.8) !important;
    border-color: rgba(255, 255, 255, 0.12) !important;
    border-radius: 10px !important;
    color: #ffffff !important;
}

.stDataFrame {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.08);
}
</style>"""


def apply_plotly_theme(fig):
    """
    Apply cinematic dark styling to a Plotly figure to blend seamlessly
    into the Stadium X glassmorphism aesthetic.
    """
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(8, 16, 32, 0.4)",
        font=dict(family="Outfit, sans-serif", color="#e2e8f0", size=12),
        margin=dict(l=40, r=30, t=50, b=40),
        xaxis=dict(
            gridcolor="rgba(255, 255, 255, 0.06)",
            zerolinecolor="rgba(255, 255, 255, 0.1)",
            tickfont=dict(color="#94a3b8"),
            title_font=dict(color="#cbd5e1", size=13),
        ),
        yaxis=dict(
            gridcolor="rgba(255, 255, 255, 0.06)",
            zerolinecolor="rgba(255, 255, 255, 0.1)",
            tickfont=dict(color="#94a3b8"),
            title_font=dict(color="#cbd5e1", size=13),
        ),
        legend=dict(
            bgcolor="rgba(10, 20, 40, 0.6)",
            bordercolor="rgba(255, 255, 255, 0.1)",
            borderwidth=1,
            font=dict(color="#e2e8f0"),
        ),
        hoverlabel=dict(
            bgcolor="#0a1329",
            bordercolor="#ff6a00",
            font=dict(family="Outfit, sans-serif", color="#ffffff", size=13),
        ),
    )
    return fig
