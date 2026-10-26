"""
pages/1_Batting_Analytics.py - Batting statistics dashboard page.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from database.connection import get_db
from analytics.batting import get_top_scorers, get_highest_innings, get_boundary_leaders, get_season_batting_trends
from analytics.teams import get_all_seasons
from analytics.team_mapping import format_season, season_sort_key

from ui.theme import STADIUM_CSS, apply_plotly_theme

st.set_page_config(page_title="Batting Lab -- CricketIQ STADIUM X", page_icon=None, layout="wide")
st.markdown(STADIUM_CSS, unsafe_allow_html=True)

st.markdown("# Batting Analytics")
st.markdown("*Definition: Batting Average = Total Runs / Innings Played. Strike Rate = (Runs / Balls) x 100.*")
st.markdown("---")

@st.cache_resource
def get_db_cached():
    try:
        db = get_db(); db.command("ping"); return db, None
    except Exception as e: return None, str(e)

_, err = get_db_cached()
if err:
    st.error(f"DB not connected: {err}")
    st.stop()

@st.cache_data(ttl=300)
def cached_seasons():
    return ["All"] + get_all_seasons()

seasons = cached_seasons()
col_filter, _ = st.columns([1, 3])
with col_filter:
    sel_season = st.selectbox("Season", seasons, key="bat_season")

st.markdown('<div class="section-header">Top Run Scorers</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def cached_scorers(season): return get_top_scorers(season if season != "All" else None)

with st.spinner("Loading batting data..."):
    try:
        data = cached_scorers(sel_season)
    except Exception as e:
        st.error(f"Query failed: {e}"); st.stop()

if not data:
    st.info("No batting data found. Import data first.")
else:
    df = pd.DataFrame(data)
    col_a, col_b = st.columns([3, 2])
    with col_a:
        fig = px.bar(df.head(15), x="total_runs", y="batter", orientation="h",
                     color="strike_rate", color_continuous_scale=["#1e3a5f","#f59e0b","#ef4444"],
                     title="Top 15 Run Scorers", labels={"total_runs":"Runs","batter":"Batter","strike_rate":"SR"})
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",font_color="#e2e8f0",
                          yaxis=dict(autorange="reversed"),coloraxis_colorbar=dict(title="SR"))
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        st.dataframe(df[["batter","total_runs","innings","batting_avg","strike_rate","fours","sixes"]].rename(
            columns={"batter":"Batter","total_runs":"Runs","innings":"Inn","batting_avg":"Avg",
                     "strike_rate":"SR","fours":"4s","sixes":"6s"}),
            use_container_width=True, hide_index=True)

st.markdown('<div class="section-header">Highest Individual Innings</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def cached_innings(season): return get_highest_innings(season if season != "All" else None)

with st.spinner("Loading innings data..."):
    try:
        innings_data = cached_innings(sel_season)
    except Exception as e:
        st.error(f"Query failed: {e}"); innings_data = []

if innings_data:
    df_inn = pd.DataFrame(innings_data)
    fig2 = px.scatter(df_inn.head(50), x="balls", y="runs", color="batter",
                      size="sixes", hover_data=["batter","batting_team","season"],
                      title="Top 50 Innings: Runs vs Balls (size = sixes)",
                      labels={"runs":"Runs","balls":"Balls Faced"})
    fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",font_color="#e2e8f0")
    st.plotly_chart(fig2, use_container_width=True)

st.markdown('<div class="section-header">Boundary Leaders</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def cached_boundaries(season): return get_boundary_leaders(season if season != "All" else None)

with st.spinner():
    try:
        bnd_data = cached_boundaries(sel_season)
    except Exception as e:
        st.error(f"Query failed: {e}"); bnd_data = []

if bnd_data:
    df_bnd = pd.DataFrame(bnd_data).head(15)
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(name="Fours", x=df_bnd["batter"], y=df_bnd["fours"],
                          marker_color="#3b82f6"))
    fig3.add_trace(go.Bar(name="Sixes", x=df_bnd["batter"], y=df_bnd["sixes"],
                          marker_color="#f59e0b"))
    fig3.update_layout(barmode="stack", title="Top 15 Boundary Hitters (4s + 6s)",
                       plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                       font_color="#e2e8f0", xaxis_tickangle=-45)
    st.plotly_chart(fig3, use_container_width=True)

st.markdown('<div class="section-header">Season Batting Trends</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def cached_bat_trends(): return get_season_batting_trends()

with st.spinner():
    try:
        trend_data = cached_bat_trends()
    except Exception as e:
        st.error(f"Query failed: {e}"); trend_data = []

if trend_data:
    df_trend = pd.DataFrame(trend_data)
    df_trend["season_display"] = df_trend["season"].apply(format_season)
    df_trend["sort_key"] = df_trend["season"].apply(season_sort_key)
    df_trend = df_trend.sort_values("sort_key")

    fig4 = px.line(df_trend, x="season_display", y="total_runs", markers=True,
                   title="Total Batter Runs Per Season",
                   color_discrete_sequence=["#f59e0b"],
                   labels={"season_display": "Season", "total_runs": "Total Runs"})
    fig4.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0",
                       xaxis_tickangle=-45)
    fig4.update_xaxes(type="category")
    fig4.update_traces(connectgaps=True, line_width=2.5)
    st.plotly_chart(fig4, use_container_width=True)
