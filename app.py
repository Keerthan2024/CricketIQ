"""
app.py - CricketIQ -- STADIUM X: Cinematic Sports Analytics Dashboard
Main Streamlit entry point: Interactive IPL Command Centre
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

import config
from database.connection import get_db
from analytics.team_mapping import format_season, season_sort_key, normalize_team_name
from analytics.teams import get_all_seasons, get_all_teams
from analytics.queries import (
    q1_top_run_scorers,
    q2_top_wicket_takers,
    q3_bowling_economy,
    q4_team_records,
    q6_season_run_totals,
    get_latest_match_showcase,
)
from analytics.venues import get_matches_by_venue, get_avg_first_innings_by_venue
import importlib
import ui.theme
try:
    importlib.reload(ui.theme)
except Exception:
    pass

from ui.theme import (
    STADIUM_CSS,
    apply_plotly_theme,
    get_page_background_css,
    render_stadium_hero,
)

try:
    from ui.theme import render_stats_banner
except ImportError:
    def render_stats_banner(stats: list) -> str:
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

# -- Page Configuration -----------------------------------------------------
st.set_page_config(
    page_title="CricketIQ -- STADIUM X | Cinematic IPL Analytics",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply Cinematic Stadium Design System
st.markdown(STADIUM_CSS, unsafe_allow_html=True)

# -- Database Connection ----------------------------------------------------
@st.cache_resource
def init_db():
    try:
        db = get_db()
        db.command("ping")
        return db, None
    except Exception as exc:
        return None, str(exc)

db, conn_error = init_db()

# -- Sidebar: Stadium Navigation & Quick Controls ---------------------------
with st.sidebar:
    st.markdown("""<div class="sidebar-brand-box">
<div class="sidebar-logo-icon">
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
    <line x1="18" y1="20" x2="18" y2="10"></line>
    <line x1="12" y1="20" x2="12" y2="4"></line>
    <line x1="6" y1="20" x2="6" y2="14"></line>
  </svg>
</div>
<div>
<div class="sidebar-brand-title">Cricket<span>IQ</span></div>
<div class="sidebar-brand-sub">STADIUM X</div>
</div>
</div>
<div class="sidebar-status-row">
<div class="stadium-brand-badge"><span class="status-dot-active"></span>SYSTEM ONLINE</div>
</div>
<div class="sidebar-tagline">DECODE THE GAME. OWN THE NUMBERS.</div>
<div class="sidebar-divider"></div>
<div class="arena-nav-header"><span class="nav-indicator-accent"></span>ARENA NAVIGATION</div>
""", unsafe_allow_html=True)
    
    nav_option = st.radio(
        "ARENA NAVIGATION",
        [
            "Stadium Command Centre",
            "IPL Season Evolution",
            "Team Performance Arena",
            "Batting Lab",
            "Bowling Lab",
            "Match Centre & Innings Momentum",
            "Venue Intelligence",
        ],
        label_visibility="collapsed",
        key="arena_navigation_radio",
    )
    
    st.markdown("""<div class="sidebar-divider"></div>
<div style="background:rgba(15,23,42,0.65);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:12px 14px;font-size:0.75rem;color:#94a3b8;line-height:1.6;box-shadow:0 4px 15px rgba(0,0,0,0.3);">
<div style="color:#00f0ff;font-weight:800;letter-spacing:0.05em;margin-bottom:2px;"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#00f0ff;margin-right:6px;"></span>LIVE ENGINE: MongoDB Atlas M0</div>
<div style="color:#ff8c38;font-weight:700;"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#ff8c38;margin-right:6px;"></span>DATASET: Official Cricsheet IPL</div>
<div style="color:#22c55e;font-weight:700;"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#22c55e;margin-right:6px;"></span>COVERAGE: 2008 – 2026 Tournament Era</div>
</div>""", unsafe_allow_html=True)


if conn_error:
    uri = config.MONGODB_URI
    is_localhost = not uri or "localhost" in uri or "127.0.0.1" in uri
    if is_localhost:
        st.error("""
### Streamlit Cloud Secrets Missing
The app is attempting to connect to `localhost:27017` because `MONGODB_URI` was not found in Streamlit Cloud Secrets.

**How to Fix (in 1 minute):**
1. In your Streamlit Cloud app dashboard, click **Settings** (or **Manage app** -> **Settings**).
2. Go to the **Secrets** tab.
3. Paste your credentials:
```toml
DATABASE_NAME = "CricketIQ"
MONGODB_URI = "your_actual_mongodb_atlas_connection_string"
```
4. Click **Save**. The app will automatically reload and connect!
""")
    else:
        from database.connection import _mask_uri
        st.error(f"""
### MongoDB Atlas Network Access Required
Could not reach MongoDB Atlas cluster within 20 seconds.
Cluster target: `{_mask_uri(uri)}`

Streamlit Community Cloud runs in dynamic AWS cloud containers. To allow the cloud container to connect to your Atlas database:

**How to Fix:**
1. Log in to [MongoDB Atlas](https://cloud.mongodb.com/).
2. In the left sidebar, click **Security** -> **Network Access**.
3. Click **+ Add IP Address**.
4. Select **Allow Access from Anywhere** (IP: `0.0.0.0/0`) and click **Confirm**.
5. Wait 30 seconds for Atlas to apply the rule, then click **Reboot app** in Streamlit Cloud!
""")
    st.stop()


# -- Data Helper Functions --------------------------------------------------
@st.cache_data(ttl=300)
def load_kpi_overview():
    d = db[config.COLLECTION_DELIVERIES]
    m = db[config.COLLECTION_MATCHES]
    matches_count = m.count_documents({})
    delivs_count = d.count_documents({})
    
    agg = list(d.aggregate([
        {"$group": {
            "_id": None,
            "total_runs": {"$sum": "$total_runs"},
            "total_wickets": {"$sum": {"$cond": [{"$ne": ["$wicket_kind", None]}, 1, 0]}}
        }}
    ]))
    
    total_runs = agg[0]["total_runs"] if agg else 401738
    total_wickets = agg[0]["total_wickets"] if agg else 14705
    raw_seasons = m.distinct("season")
    seasons = sorted(raw_seasons, key=season_sort_key)
    
    return matches_count, delivs_count, total_runs, total_wickets, seasons

matches_cnt, delivs_cnt, runs_cnt, wickets_cnt, all_seasons = (
    1243, 295732, 401738, 14705, [str(y) for y in range(2008, 2027)]
)

try:
    matches_cnt, delivs_cnt, runs_cnt, wickets_cnt, all_seasons = load_kpi_overview()
except Exception as e:
    import requests
    current_ip = "Unknown"
    try:
        current_ip = requests.get('https://api.ipify.org?format=json', timeout=3).json().get('ip', 'Unknown')
    except Exception:
        pass
        
    st.markdown(f"""<div style="background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.4);border-radius:14px;padding:1.5rem;margin:2rem 0;">
<div style="font-size:1.1rem;font-weight:800;color:#ef4444;margin-bottom:0.5rem;">MongoDB Atlas Network Access Blocked</div>
<p style="color:#e2e8f0;font-size:0.9rem;line-height:1.6;margin-bottom:1rem;">
Your cellular / Wi-Fi network rotated your IP address to: <b style="color:#00f0ff;font-family:'JetBrains Mono';font-size:1.05rem;">{current_ip}</b>.<br>
MongoDB Atlas closes the SSL connection when your current IP is not in the whitelist.
</p>
<div style="background:rgba(15,23,42,0.8);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:1rem;font-size:0.85rem;color:#94a3b8;">
<b>Fix in 30 seconds:</b><br>
1. Go to <a href="https://cloud.mongodb.com" target="_blank" style="color:#ff8c38;text-decoration:underline;">cloud.mongodb.com</a> → <b>Security</b> → <b>Network Access</b>.<br>
2. Click <b>Add IP Address</b> → Select <b>ALLOW ACCESS FROM ANYWHERE (0.0.0.0/0)</b> or enter <code>{current_ip}/32</code>.<br>
3. Click <b>Confirm</b> and refresh this page.
</div>
</div>""", unsafe_allow_html=True)
    st.stop()


# ===========================================================================
# VIEW 1: STADIUM COMMAND CENTRE (HERO & OVERVIEW)
# ===========================================================================
if nav_option == "Stadium Command Centre":
    st.markdown(get_page_background_css("overview"), unsafe_allow_html=True)

    stats_banner_v1 = render_stats_banner([
        (f"{matches_cnt:,}", "IPL MATCHES ANALYZED"),
        (f"{delivs_cnt:,}", "BALLS INGESTED"),
        (f"{runs_cnt:,}", "TOTAL RUNS SCORED"),
        (f"{wickets_cnt:,}", "TOTAL WICKETS"),
        (f"{len(all_seasons)}", "HISTORIC SEASONS"),
    ])
    hero_html = render_stadium_hero(
        image_key="overview",
        badge_text="BIG DATA CRICKET INTELLIGENCE",
        title_html="DECODE THE GAME.<br><span style='color:#ff6a00;'>OWN THE NUMBERS.</span>",
        tagline_html="Every season. Every delivery. Every tactical decision. Explore the full mathematical architecture of the Indian Premier League inside <b>STADIUM X</b>.",
        stats_banner_html=stats_banner_v1,
    )
    st.markdown(hero_html, unsafe_allow_html=True)
    
    # 5 Futuristic Glass KPI Cards
    c1, c2, c3, c4, c5 = st.columns(5)
    
    with c1:
        st.markdown(f"""<div class="kpi-card-stadium">
<div class="kpi-header"><span class="kpi-title">Matches</span><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#ff8c38" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg></div>
<div class="kpi-numeric highlight-orange" style="font-size:1.45rem;white-space:nowrap;">{matches_cnt:,}</div>
<div class="kpi-subtext">Across 19 IPL editions</div>
</div>""", unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""<div class="kpi-card-stadium blue-accent">
<div class="kpi-header"><span class="kpi-title">Deliveries</span><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#00f0ff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg></div>
<div class="kpi-numeric highlight-cyan" style="font-size:1.45rem;white-space:nowrap;">{delivs_cnt:,}</div>
<div class="kpi-subtext">Ball-by-ball granularity</div>
</div>""", unsafe_allow_html=True)

    with c3:
        st.markdown(f"""<div class="kpi-card-stadium">
<div class="kpi-header"><span class="kpi-title">Total Runs</span><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#ff8c38" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg></div>
<div class="kpi-numeric highlight-orange" style="font-size:1.45rem;white-space:nowrap;">{runs_cnt:,}</div>
<div class="kpi-subtext">Batting & extras combined</div>
</div>""", unsafe_allow_html=True)

    with c4:
        st.markdown(f"""<div class="kpi-card-stadium blue-accent">
<div class="kpi-header"><span class="kpi-title">Total Wickets</span><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#00f0ff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="22" y1="12" x2="18" y2="12"/><line x1="6" y1="12" x2="2" y2="12"/><line x1="12" y1="6" x2="12" y2="2"/><line x1="12" y1="22" x2="12" y2="18"/></svg></div>
<div class="kpi-numeric highlight-cyan" style="font-size:1.45rem;white-space:nowrap;">{wickets_cnt:,}</div>
<div class="kpi-subtext">Bowled, caught, run outs</div>
</div>""", unsafe_allow_html=True)

    with c5:
        st.markdown(f"""<div class="kpi-card-stadium">
<div class="kpi-header"><span class="kpi-title">Seasons</span><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#ff8c38" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg></div>
<div class="kpi-numeric highlight-orange" style="font-size:1.45rem;white-space:nowrap;">{len(all_seasons)}</div>
<div class="kpi-subtext">From 2008 inaugural to 2024+</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)
    
    # Dynamic Latest Match Showcase Broadcast Card
    latest_m = None
    try:
        latest_m = get_latest_match_showcase()
    except Exception:
        pass

    if latest_m:
        teams = latest_m.get("teams", ["Team 1", "Team 2"])
        team1 = teams[0] if len(teams) > 0 else "Team 1"
        team2 = teams[1] if len(teams) > 1 else "Team 2"
        venue = latest_m.get("venue", "N/A")
        season = latest_m.get("season", "")
        date = latest_m.get("date", "")
        result = latest_m.get("result", "")
        poms = ", ".join(latest_m.get("player_of_match", []))
        pom_str = f" • Player of the Match: {poms}" if poms else ""

        inns = latest_m.get("innings", [])
        inn1_score = "—"
        inn2_score = "—"
        if len(inns) >= 1:
            inn1_score = f"{inns[0]['runs']}/{inns[0]['wickets']} <small style='font-size:0.85rem;color:#94a3b8;'>({inns[0]['overs']} ov)</small>"
            if inns[0]["team"] == team2 and len(teams) > 1:
                team1, team2 = team2, team1
        if len(inns) >= 2:
            inn2_score = f"{inns[1]['runs']}/{inns[1]['wickets']} <small style='font-size:0.85rem;color:#94a3b8;'>({inns[1]['overs']} ov)</small>"

        st.markdown(f"""<div class="stadium-glass-panel">
<div class="panel-header">
<div class="panel-title"><span>LATEST MATCH BROADCAST: {season} SEASON ({date})</span></div>
<span class="panel-badge">{venue.upper()}</span>
</div>
<div class="stadium-scorecard">
<div class="team-box">
<span class="team-name">{team1}</span>
<span class="team-score">{inn1_score}</span>
</div>
<div class="vs-badge">VS</div>
<div class="team-box" style="text-align:right;">
<span class="team-name">{team2}</span>
<span class="team-score" style="color:#00f0ff;">{inn2_score}</span>
</div>
</div>
<p style="font-size:0.85rem;color:#94a3b8;margin:0;">
<b>Result:</b> {result}{pom_str}
</p>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div class="stadium-glass-panel">
<div class="panel-header">
<div class="panel-title"><span>SHOWCASE BROADCAST</span></div>
<span class="panel-badge">LIVE ARENA</span>
</div>
<div style="color:#94a3b8;font-size:0.9rem;padding:0.5rem 0;">Connecting to match feed...</div>
</div>""", unsafe_allow_html=True)

    # Multi-Panel Analytics Grid
    col_left, col_right = st.columns([1.5, 1])
    
    with col_left:
        st.markdown('<div class="panel-title" style="margin-bottom:0.75rem;">Macro Run Volume Trends Across Seasons</div>', unsafe_allow_html=True)
        
        season_stats = q6_season_run_totals()
        if season_stats:
            df_season = pd.DataFrame(season_stats)
            df_season["formatted_season"] = df_season["season"].apply(format_season)
            df_season["sort_key"] = df_season["season"].apply(season_sort_key)
            df_season = df_season.sort_values("sort_key")
            
            fig_macro = px.area(
                df_season,
                x="formatted_season",
                y="total_runs",
                markers=True,
                labels={"formatted_season": "Season", "total_runs": "Cumulative Runs Scored"},
            )
            fig_macro.update_traces(
                line=dict(color="#ff6a00", width=3),
                fillcolor="rgba(255, 106, 0, 0.15)",
                marker=dict(size=7, color="#ff8c38", line=dict(width=2, color="#ffffff")),
                connectgaps=True,
            )
            fig_macro.update_xaxes(type="category")
            apply_plotly_theme(fig_macro)
            st.plotly_chart(fig_macro, use_container_width=True)

    with col_right:
        st.markdown('<div class="panel-title" style="margin-bottom:0.75rem;">All-Time Dynasty: Match Wins</div>', unsafe_allow_html=True)
        
        team_rec = q4_team_records(season="All")
        if team_rec:
            df_tr = pd.DataFrame(team_rec).head(7)
            fig_bar = px.bar(
                df_tr,
                x="wins",
                y="team",
                orientation="h",
                text="wins",
                labels={"wins": "Championship Matches Won", "team": ""},
            )
            fig_bar.update_traces(
                marker=dict(
                    color=df_tr["win_pct"],
                    colorscale=[[0, "#1e3a5f"], [0.5, "#ff6a00"], [1.0, "#00f0ff"]],
                    line=dict(color="rgba(255,255,255,0.15)", width=1)
                ),
                textposition="outside",
                textfont=dict(color="#ffffff", family="JetBrains Mono", size=11),
            )
            fig_bar.update_layout(yaxis=dict(autorange="reversed"))
            apply_plotly_theme(fig_bar)
            st.plotly_chart(fig_bar, use_container_width=True)


# ===========================================================================
# VIEW 2: IPL SEASON EVOLUTION
# ===========================================================================
elif nav_option == "IPL Season Evolution":
    st.markdown(get_page_background_css("seasons"), unsafe_allow_html=True)
    stats_banner_v2 = render_stats_banner([
        (f"{len(all_seasons)}", "IPL EDITIONS"),
        ("2008 – 2026", "ERA ARCHIVE"),
        (f"{runs_cnt:,}", "AGGREGATE RUNS"),
        (f"{wickets_cnt:,}", "TOTAL WICKETS"),
        ("211.4", "PEAK 1ST INN PAR"),
    ])
    hero_html = render_stadium_hero(
        image_key="seasons",
        badge_text="HISTORICAL ARCHITECTURE & ERA DYNAMICS",
        title_html="TOURNAMENT EVOLUTION.<br><span style='color:#ff6a00;'>SCORING VELOCITIES.</span>",
        tagline_html="Trace the generational progression of T20 cricket from 2008 to 2026. Audit run-rate inflation, boundary surges, and dismissal distributions across 19 editions.",
        stats_banner_html=stats_banner_v2,
    )
    st.markdown(hero_html, unsafe_allow_html=True)
    
    season_stats = q6_season_run_totals()
    df_s = pd.DataFrame(season_stats)
    df_s["formatted_season"] = df_s["season"].apply(format_season)
    df_s["sort_key"] = df_s["season"].apply(season_sort_key)
    df_s = df_s.sort_values("sort_key").reset_index(drop=True)
    
    # Filter: Season range slider
    sel_range = st.select_slider(
        "Select Tournament Era",
        options=list(df_s["formatted_season"]),
        value=(df_s["formatted_season"].iloc[0], df_s["formatted_season"].iloc[-1]),
    )
    
    start_idx = df_s[df_s["formatted_season"] == sel_range[0]].index[0]
    end_idx = df_s[df_s["formatted_season"] == sel_range[1]].index[0]
    filtered_df = df_s.iloc[start_idx:end_idx+1]
    
    tab1, tab2 = st.tabs(["Runs & Matches Momentum", "Wickets & Dismissal Flow"])
    
    with tab1:
        fig_s1 = go.Figure()
        fig_s1.add_trace(go.Bar(
            x=filtered_df["formatted_season"],
            y=filtered_df["matches"],
            name="Matches Played",
            marker=dict(color="rgba(0, 240, 255, 0.4)", line=dict(color="#00f0ff", width=1.5)),
            yaxis="y2",
        ))
        fig_s1.add_trace(go.Scatter(
            x=filtered_df["formatted_season"],
            y=filtered_df["total_runs"],
            name="Total Runs Scored",
            mode="lines+markers",
            line=dict(color="#ff6a00", width=4),
            marker=dict(size=9, color="#ffffff", line=dict(color="#ff6a00", width=3)),
            yaxis="y",
        ))
        fig_s1.update_layout(
            yaxis=dict(title="Total Runs", gridcolor="rgba(255,255,255,0.06)"),
            yaxis2=dict(title="Matches Played", overlaying="y", side="right", showgrid=False),
            xaxis=dict(type="category"),
            legend=dict(x=0.01, y=0.98),
        )
        apply_plotly_theme(fig_s1)
        st.plotly_chart(fig_s1, use_container_width=True)
        
    with tab2:
        fig_w = px.bar(
            filtered_df,
            x="formatted_season",
            y="total_wickets",
            text="total_wickets",
            labels={"formatted_season": "Season", "total_wickets": "Wickets Claimed"},
            title="Total Wickets Claimed per Season"
        )
        fig_w.update_traces(
            marker=dict(
                color=filtered_df["total_wickets"],
                colorscale=[[0, "#ff5500"], [0.5, "#ff8c38"], [1.0, "#00f0ff"]],
            ),
            textposition="outside",
            textfont=dict(color="#ffffff", family="JetBrains Mono"),
        )
        fig_w.update_xaxes(type="category")
        apply_plotly_theme(fig_w)
        st.plotly_chart(fig_w, use_container_width=True)


# ===========================================================================
# VIEW 3: TEAM PERFORMANCE ARENA
# ===========================================================================
elif nav_option == "Team Performance Arena":
    st.markdown(get_page_background_css("teams"), unsafe_allow_html=True)
    stats_banner_v3 = render_stats_banner([
        ("15+", "FRANCHISES AUDITED"),
        ("5 TITLES", "MI & CSK BENCHMARK"),
        ("58.2%", "PEAK WIN RATE"),
        (f"{matches_cnt:,}", "CONTESTS ANALYZED"),
        ("PLAY BOLD", "ROYAL CHALLENGERS"),
    ])
    hero_html = render_stadium_hero(
        image_key="teams",
        badge_text="FRANCHISE SUPREMACY & HEAD-TO-HEAD",
        title_html="DYNASTIC DOMINANCE.<br><span style='color:#ff6a00;'>FRANCHISE RIVALRIES.</span>",
        tagline_html="Evaluate win percentages, championship legacies, and head-to-head records across every franchise in tournament history.",
        stats_banner_html=stats_banner_v3,
    )
    st.markdown(hero_html, unsafe_allow_html=True)
    
    team_opts = ["All"] + all_seasons
    col_ctrl1, col_ctrl2 = st.columns([1, 2])
    with col_ctrl1:
        sel_season_team = st.selectbox("Season Filter", team_opts, index=0)
        
    records = q4_team_records(season=sel_season_team)
    if records:
        df_teams = pd.DataFrame(records)
        
        c_kpi1, c_kpi2, c_kpi3 = st.columns(3)
        top_team = df_teams.iloc[0]
        c_kpi1.metric("Highest Win Count", top_team["team"], f"{top_team['wins']} wins")
        c_kpi2.metric("Highest Win Percentage", df_teams.sort_values("win_pct", ascending=False).iloc[0]["team"], f"{df_teams.sort_values('win_pct', ascending=False).iloc[0]['win_pct']}%")
        c_kpi3.metric("Total Competing Franchises", len(df_teams))
        
        p1, p2 = st.columns([1.3, 1])
        with p1:
            st.markdown("#### Win / Loss Ratio by Franchise")
            fig_teams = go.Figure()
            fig_teams.add_trace(go.Bar(
                name="Wins",
                x=df_teams["team"],
                y=df_teams["wins"],
                marker=dict(color="#00f0ff"),
            ))
            fig_teams.add_trace(go.Bar(
                name="Losses",
                x=df_teams["team"],
                y=df_teams["losses"],
                marker=dict(color="rgba(255, 106, 0, 0.5)"),
            ))
            fig_teams.update_layout(barmode="stack", xaxis=dict(tickangle=-45))
            apply_plotly_theme(fig_teams)
            st.plotly_chart(fig_teams, use_container_width=True)
            
        with p2:
            st.markdown("#### Franchise Leaderboard")
            st.dataframe(
                df_teams.rename(columns={
                    "team": "Franchise",
                    "matches_played": "Mat",
                    "wins": "W",
                    "losses": "L",
                    "win_pct": "Win %"
                }),
                use_container_width=True,
                hide_index=True
            )


# ===========================================================================
# VIEW 4: BATTING LAB
# ===========================================================================
elif nav_option == "Batting Lab":
    st.markdown(get_page_background_css("batting"), unsafe_allow_html=True)
    stats_banner_v4 = render_stats_banner([
        ("8,000+", "ALL-TIME RUN RECORD"),
        ("130+", "LEAGUE AVG SR"),
        ("25,000+", "FOURS LOGGED"),
        ("12,000+", "SIXES CLEARED"),
        ("ORANGE CAP", "BATTING SUPREMACY"),
    ])
    hero_html = render_stadium_hero(
        image_key="batting",
        badge_text="BALLISTIC PROFILES & RUN VELOCITY",
        title_html="WILLOW MASTERY.<br><span style='color:#ff6a00;'>BOUNDARY ARCHITECTURE.</span>",
        tagline_html="Deconstruct boundary densities, velocity profiles, and strike-rate accelerators for the most dominant run-scorers in IPL history.",
        stats_banner_html=stats_banner_v4,
    )
    st.markdown(hero_html, unsafe_allow_html=True)
    
    col_b1, col_b2 = st.columns([1, 1])
    with col_b1:
        sel_bat_season = st.selectbox("Season", ["All"] + all_seasons, key="bat_season_sel")
    with col_b2:
        top_n_bat = st.slider("Top Batters Limit", min_value=10, max_value=30, value=15)
        
    batters = q1_top_run_scorers(season=sel_bat_season, limit=top_n_bat)
    if batters:
        df_bat = pd.DataFrame(batters)
        best_run_batter = df_bat.iloc[0]
        
        st.markdown(f"""<div class="stadium-scorecard">
<div class="team-box">
<span style="font-size:0.75rem;color:#ff8c38;text-transform:uppercase;font-weight:700;">ORANGE CAP LEADER / PROWESS</span>
<span class="team-name" style="font-size:1.6rem;color:#ffffff;">{best_run_batter['batter']}</span>
</div>
<div style="display:flex;gap:2rem;">
<div class="team-box" style="text-align:right;">
<span style="font-size:0.7rem;color:#64748b;">RUNS</span>
<span class="team-score">{best_run_batter['total_runs']:,}</span>
</div>
<div class="team-box" style="text-align:right;">
<span style="font-size:0.7rem;color:#64748b;">STRIKE RATE</span>
<span class="team-score" style="color:#00f0ff;">{best_run_batter['strike_rate']}</span>
</div>
<div class="team-box" style="text-align:right;">
<span style="font-size:0.7rem;color:#64748b;">BOUNDARIES (4s/6s)</span>
<span class="team-score" style="color:#22c55e;">{best_run_batter['fours']}/{best_run_batter['sixes']}</span>
</div>
</div>
</div>""", unsafe_allow_html=True)
        
        tab_bat1, tab_bat2 = st.tabs(["Boundary Distribution (4s vs 6s)", "Strike Rate vs Volume Matrix"])
        
        with tab_bat1:
            fig_bounds = go.Figure()
            fig_bounds.add_trace(go.Bar(
                name="Fours (4s)",
                x=df_bat["batter"],
                y=df_bat["fours"],
                marker=dict(color="#ff8c38"),
            ))
            fig_bounds.add_trace(go.Bar(
                name="Sixes (6s)",
                x=df_bat["batter"],
                y=df_bat["sixes"],
                marker=dict(color="#00f0ff"),
            ))
            fig_bounds.update_layout(barmode="group", xaxis=dict(tickangle=-45))
            apply_plotly_theme(fig_bounds)
            st.plotly_chart(fig_bounds, use_container_width=True)
            
        with tab_bat2:
            fig_scatter = px.scatter(
                df_bat,
                x="balls_faced",
                y="strike_rate",
                size="total_runs",
                color="total_runs",
                text="batter",
                color_continuous_scale=[[0, "#1e3a5f"], [0.5, "#ff6a00"], [1.0, "#00f0ff"]],
                labels={"balls_faced": "Balls Faced", "strike_rate": "Strike Rate", "total_runs": "Runs"},
            )
            fig_scatter.update_traces(textposition="top center")
            apply_plotly_theme(fig_scatter)
            st.plotly_chart(fig_scatter, use_container_width=True)


# ===========================================================================
# VIEW 5: BOWLING LAB
# ===========================================================================
elif nav_option == "Bowling Lab":
    st.markdown(get_page_background_css("bowling"), unsafe_allow_html=True)
    stats_banner_v5 = render_stats_banner([
        ("230+", "ALL-TIME WICKETS"),
        ("6.21", "BENCHMARK ECONOMY"),
        (f"{wickets_cnt:,}", "DISMISSALS AUDITED"),
        ("PURPLE CAP", "BOWLING CROWN"),
        ("DOT BALLS", "PRESSURE INDEX"),
    ])
    hero_html = render_stadium_hero(
        image_key="bowling",
        badge_text="BALLISTIC & WICKET DYNAMICS",
        title_html="LETHAL PRECISION.<br><span style='color:#ff6a00;'>DISMISSAL SCIENCE.</span>",
        tagline_html="Analyze economy containment, wicket distribution vectors, and pressure building across pacers and spinners.",
        stats_banner_html=stats_banner_v5,
    )
    st.markdown(hero_html, unsafe_allow_html=True)
    
    col_bw1, col_bw2 = st.columns([1, 1])
    with col_bw1:
        sel_bowl_season = st.selectbox("Season Filter", ["All"] + all_seasons, key="bowl_season_sel")
    with col_bw2:
        top_n_bowl = st.slider("Top Bowlers Limit", min_value=10, max_value=30, value=15)
        
    bowlers = q2_top_wicket_takers(season=sel_bowl_season, limit=top_n_bowl)
    if bowlers:
        df_bowl = pd.DataFrame(bowlers)
        
        tab_bowl1, tab_bowl2 = st.tabs(["Top Wicket Takers", "Best Economy Rates"])
        
        with tab_bowl1:
            fig_bowl = px.bar(
                df_bowl,
                x="wickets",
                y="bowler",
                orientation="h",
                text="wickets",
                color="wickets",
                color_continuous_scale=[[0, "#1e3a5f"], [0.5, "#ff6a00"], [1.0, "#00f0ff"]],
                labels={"wickets": "Wickets Taken", "bowler": ""},
                title="Purple Cap Leaderboard"
            )
            fig_bowl.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
            fig_bowl.update_traces(textposition="outside", textfont=dict(color="#ffffff", family="JetBrains Mono"))
            apply_plotly_theme(fig_bowl)
            st.plotly_chart(fig_bowl, use_container_width=True)
            
            st.markdown("#### Top Wicket Takers Table")
            st.dataframe(
                df_bowl.rename(columns={
                    "bowler": "Bowler",
                    "wickets": "Wickets",
                    "matches": "Matches"
                }),
                use_container_width=True,
                hide_index=True
            )
            
        with tab_bowl2:
            econ_data = q3_bowling_economy(season=sel_bowl_season, limit=top_n_bowl)
            if econ_data:
                df_econ = pd.DataFrame(econ_data)
                fig_econ = px.bar(
                    df_econ,
                    x="bowler",
                    y="economy",
                    text="economy",
                    color="economy",
                    color_continuous_scale=[[0, "#00f0ff"], [0.5, "#ff8c38"], [1.0, "#ff3333"]],
                    labels={"economy": "Economy Rate", "bowler": ""},
                    title="Best Bowling Economy Rates (Min 30 Overs)"
                )
                fig_econ.update_traces(textposition="outside", textfont=dict(color="#ffffff", family="JetBrains Mono"))
                apply_plotly_theme(fig_econ)
                st.plotly_chart(fig_econ, use_container_width=True)
                
                st.dataframe(
                    df_econ.rename(columns={
                        "bowler": "Bowler",
                        "runs_conceded": "Runs Conceded",
                        "overs_bowled": "Overs",
                        "economy": "Economy"
                    }),
                    use_container_width=True,
                    hide_index=True
                )


# ===========================================================================
# VIEW 6: MATCH CENTRE & INNINGS MOMENTUM
# ===========================================================================
elif nav_option == "Match Centre & Innings Momentum":
    st.markdown(get_page_background_css("match"), unsafe_allow_html=True)
    stats_banner_v6 = render_stats_banner([
        (f"{matches_cnt:,}", "MATCH ARCHIVES"),
        (f"{delivs_cnt:,}", "BALL TELEMETRY"),
        ("20.0 OV", "FULL MATCH DEPTH"),
        ("MOMENTUM", "SCORE ACCELERATION"),
        ("BALL-BY-BALL", "TACTICAL TIMELINE"),
    ])
    hero_html = render_stadium_hero(
        image_key="match",
        badge_text="TACTICAL MATCH ROOM & CELEBRATION",
        title_html="TACTICAL AUDIT.<br><span style='color:#ff6a00;'>INNINGS MOMENTUM.</span>",
        tagline_html="Inspect granular ball-by-ball score acceleration, partnership swings, and wicket leverage moments from any match in the archive.",
        stats_banner_html=stats_banner_v6,
    )
    st.markdown(hero_html, unsafe_allow_html=True)
    
    col_m1, col_m2 = st.columns([1, 2])
    with col_m1:
        sel_m_season = st.selectbox("Select Season", all_seasons, index=len(all_seasons)-1, key="mc_season")
        
    matches = list(db[config.COLLECTION_MATCHES].find(
        {"season": sel_m_season},
        {"match_id": 1, "date": 1, "teams": 1, "venue": 1, "winner": 1, "result": 1, "player_of_match": 1, "_id": 0}
    ).sort("date", -1))
    
    if matches:
        def format_m_label(m):
            teams_str = " vs ".join(m.get("teams", ["?", "?"]))
            return f"{m.get('date', '?')} | {teams_str} ({m.get('venue', '?')[:25]})"
            
        m_opts = {format_m_label(m): m["match_id"] for m in matches}
        with col_m2:
            sel_lbl = st.selectbox("Select Match to Inspect", list(m_opts.keys()), key="mc_match_select")
            sel_mid = m_opts[sel_lbl]
            
        match_doc = db[config.COLLECTION_MATCHES].find_one({"match_id": sel_mid}, {"_id": 0})
        delivs = list(db[config.COLLECTION_DELIVERIES].find({"match_id": sel_mid}).sort([("innings", 1), ("over", 1), ("delivery", 1)]))
        
        if match_doc and delivs:
            df_d = pd.DataFrame(delivs)
            teams = match_doc.get("teams", ["Team 1", "Team 2"])
            winner = match_doc.get("winner", "No Result")
            pom = ", ".join(match_doc.get("player_of_match", []) or ["N/A"])
            
            st.markdown(f"""<div class="stadium-scorecard">
<div class="team-box">
<span style="font-size:0.75rem;color:#94a3b8;text-transform:uppercase;">{match_doc.get('date')} • {match_doc.get('venue')}</span>
<span class="team-name">{' vs '.join(teams)}</span>
</div>
<div class="vs-badge">COMPLETED</div>
<div class="team-box" style="text-align:right;">
<span style="font-size:0.75rem;color:#00f0ff;font-weight:700;">WINNER</span>
<span class="team-name" style="color:#22c55e;">{winner}</span>
<span style="font-size:0.75rem;color:#94a3b8;">Player of Match: {pom}</span>
</div>
</div>""", unsafe_allow_html=True)
            
            st.markdown("#### Innings Momentum: Cumulative Score Acceleration")
            fig_momentum = go.Figure()
            colors = ["#ff6a00", "#00f0ff"]
            
            for inn_idx, inn_num in enumerate(sorted(df_d["innings"].unique())):
                inn_df = df_d[df_d["innings"] == inn_num].copy().reset_index(drop=True)
                inn_df["ball_num"] = range(1, len(inn_df) + 1)
                inn_df["cum_runs"] = inn_df["total_runs"].cumsum()
                team_name = inn_df["batting_team"].iloc[0] if not inn_df.empty else f"Innings {inn_num}"
                
                fig_momentum.add_trace(go.Scatter(
                    x=inn_df["ball_num"],
                    y=inn_df["cum_runs"],
                    name=f"Inn {inn_num}: {team_name}",
                    mode="lines",
                    line=dict(color=colors[inn_idx % 2], width=3),
                ))
                
                w_points = inn_df[inn_df["wicket_kind"].notna()]
                if not w_points.empty:
                    fig_momentum.add_trace(go.Scatter(
                        x=w_points["ball_num"],
                        y=w_points["cum_runs"],
                        name=f"Wickets ({team_name})",
                        mode="markers",
                        marker=dict(symbol="x", size=9, color="#ff3333"),
                        showlegend=False,
                    ))
                    
            fig_momentum.update_layout(
                xaxis=dict(title="Balls Bowled"),
                yaxis=dict(title="Cumulative Score"),
            )
            apply_plotly_theme(fig_momentum)
            st.plotly_chart(fig_momentum, use_container_width=True)


# ===========================================================================
# VIEW 7: VENUE INTELLIGENCE
# ===========================================================================
elif nav_option == "Venue Intelligence":
    st.markdown(get_page_background_css("venues"), unsafe_allow_html=True)
    stats_banner_v7 = render_stats_banner([
        ("M. CHINNASWAMY", "ICONIC FORTRESS"),
        ("175.4", "1ST INNINGS PAR"),
        ("35+", "GLOBAL GROUNDS"),
        ("TOSS BIAS", "CHASE VS DEFEND"),
        ("ALTITUDE", "BOUNDARY HAVEN"),
    ])
    hero_html = render_stadium_hero(
        image_key="venues",
        badge_text="FORTRESS DYNAMICS & GROUND INTEL",
        title_html="VENUE ARCHITECTURE.<br><span style='color:#ff6a00;'>PITCH PAR METRICS.</span>",
        tagline_html="Evaluate boundary geometry, first-innings par scoring, and toss bias across 35+ legendary cricket grounds worldwide.",
        stats_banner_html=stats_banner_v7,
    )
    st.markdown(hero_html, unsafe_allow_html=True)

    tab_v1, tab_v2, tab_v3 = st.tabs(["Most Frequented Venues", "1st Innings Scoring Par", "Toss & Field Bias"])

    with tab_v1:
        venue_matches = get_matches_by_venue(limit=15)
        if venue_matches:
            df_vm = pd.DataFrame(venue_matches)
            fig_v1 = px.bar(
                df_vm,
                x="matches",
                y="venue",
                orientation="h",
                text="matches",
                color="matches",
                color_continuous_scale=[[0, "#1e3a5f"], [0.5, "#ff6a00"], [1.0, "#00f0ff"]],
                labels={"matches": "Total IPL Matches Hosted", "venue": ""},
                title="Top 15 Most Frequented IPL Stadiums (Canonical)"
            )
            fig_v1.update_layout(yaxis=dict(autorange="reversed"))
            apply_plotly_theme(fig_v1)
            st.plotly_chart(fig_v1, use_container_width=True)

    with tab_v2:
        venue_avg = get_avg_first_innings_by_venue(min_matches=5, limit=15)
        if venue_avg:
            df_va = pd.DataFrame(venue_avg)
            fig_v2 = px.bar(
                df_va,
                x="venue",
                y="avg_score",
                text="avg_score",
                color="avg_score",
                color_continuous_scale=[[0, "#00f0ff"], [0.5, "#ff8c38"], [1.0, "#ff3333"]],
                labels={"avg_score": "Avg 1st Innings Total", "venue": ""},
                title="Average First-Innings Score by Stadium (Min 5 Matches)"
            )
            fig_v2.update_traces(textposition="outside")
            apply_plotly_theme(fig_v2)
            st.plotly_chart(fig_v2, use_container_width=True)

            st.dataframe(
                df_va.rename(columns={
                    "venue": "Stadium",
                    "avg_score": "Avg 1st Innings Score",
                    "highest": "Highest Score",
                    "matches": "Matches Analyzed"
                }),
                use_container_width=True,
                hide_index=True
            )

    with tab_v3:
        venue_docs = list(db[config.COLLECTION_MATCHES].aggregate([
            {"$group": {
                "_id": "$venue",
                "matches": {"$sum": 1},
                "toss_field_wins": {"$sum": {"$cond": [{"$and": [{"$eq": ["$toss_decision", "field"]}, {"$eq": ["$winner", "$toss_winner"]}]}, 1, 0]}},
                "toss_bat_wins": {"$sum": {"$cond": [{"$and": [{"$eq": ["$toss_decision", "bat"]}, {"$eq": ["$winner", "$toss_winner"]}]}, 1, 0]}}
            }},
            {"$sort": {"matches": -1}},
            {"$limit": 15}
        ]))
        if venue_docs:
            df_venue = pd.DataFrame(venue_docs)
            df_venue["venue"] = df_venue["_id"]
            fig_v3 = go.Figure()
            fig_v3.add_trace(go.Bar(
                name="Toss Win + Field Win",
                x=df_venue["venue"],
                y=df_venue["toss_field_wins"],
                marker=dict(color="#00f0ff")
            ))
            fig_v3.add_trace(go.Bar(
                name="Toss Win + Bat Win",
                x=df_venue["venue"],
                y=df_venue["toss_bat_wins"],
                marker=dict(color="#ff6a00")
            ))
            fig_v3.update_layout(
                barmode="group",
                title="Toss Decision Match Win Bias Across Top Venues",
                xaxis=dict(tickangle=-45)
            )
            apply_plotly_theme(fig_v3)
            st.plotly_chart(fig_v3, use_container_width=True)
