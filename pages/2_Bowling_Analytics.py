"""
pages/2_Bowling_Analytics.py - Bowling statistics dashboard page.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from analytics.bowling import get_wicket_leaders, get_economy_leaders, get_bowling_averages, get_season_bowling_trends
from analytics.teams import get_all_seasons
from analytics.team_mapping import format_season, season_sort_key
from database.connection import get_db

from ui.theme import STADIUM_CSS, apply_plotly_theme

st.set_page_config(page_title="Bowling Lab -- CricketIQ STADIUM X", page_icon=None, layout="wide")
st.markdown(STADIUM_CSS, unsafe_allow_html=True)

st.markdown("# Bowling Analytics")
st.markdown("""
*Economy = Runs Conceded / Overs Bowled. Runs conceded include batter runs + wides + no-balls.
**Byes and leg-byes are excluded** (they are fielding errors, not bowling runs).
**Only bowler-credited dismissals** (bowled, caught, lbw, stumped, hit wicket) are counted as wickets.
Run-outs are excluded.*
""")
st.markdown("---")

@st.cache_resource
def get_db_cached():
    try:
        db = get_db(); db.command("ping"); return db, None
    except Exception as e: return None, str(e)

_, err = get_db_cached()
if err:
    st.error(f"DB not connected: {err}"); st.stop()

@st.cache_data(ttl=300)
def cached_seasons():
    return ["All"] + get_all_seasons()

seasons = cached_seasons()
col_f, _ = st.columns([1,3])
with col_f:
    sel = st.selectbox("Season", seasons, key="bowl_season")

season = sel if sel != "All" else None

# -- Wicket leaders ----------------------------------------------------------
st.markdown('<div class="section-header">Top Wicket Takers</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def cached_wkt(s): return get_wicket_leaders(s)

with st.spinner():
    try: wkt_data = cached_wkt(season)
    except Exception as e: st.error(str(e)); wkt_data = []

if wkt_data:
    df_w = pd.DataFrame(wkt_data)
    col_a, col_b = st.columns([3,2])
    with col_a:
        fig = px.bar(df_w.head(15), x="wickets", y="bowler", orientation="h",
                     color="wickets", color_continuous_scale=["#1e3a5f","#ef4444"],
                     title="Top 15 Wicket Takers")
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                          font_color="#e2e8f0",yaxis=dict(autorange="reversed"),coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        st.dataframe(df_w.rename(columns={"bowler":"Bowler","wickets":"Wickets","matches":"Matches"}),
                     use_container_width=True, hide_index=True)

# -- Economy leaders ---------------------------------------------------------
st.markdown('<div class="section-header">Best Economy Rates (min 20 overs)</div>', unsafe_allow_html=True)
st.markdown('<div class="note">Minimum 20 legal overs bowled to qualify.</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def cached_econ(s): return get_economy_leaders(s, min_overs=20)

with st.spinner():
    try: econ_data = cached_econ(season)
    except Exception as e: st.error(str(e)); econ_data = []

if econ_data:
    df_e = pd.DataFrame(econ_data)
    fig2 = px.bar(df_e.head(15), x="bowler", y="economy",
                  color="economy", color_continuous_scale=["#22c55e","#f59e0b","#ef4444"],
                  title="Economy Rate -- Lower is Better")
    fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                       font_color="#e2e8f0",xaxis_tickangle=-45,coloraxis_showscale=False)
    st.plotly_chart(fig2, use_container_width=True)

# -- Bowling average ---------------------------------------------------------
st.markdown('<div class="section-header">Bowling Averages (min 10 wickets)</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def cached_avg(s): return get_bowling_averages(s, min_wickets=10)

with st.spinner():
    try: avg_data = cached_avg(season)
    except Exception as e: st.error(str(e)); avg_data = []

if avg_data:
    df_a = pd.DataFrame(avg_data)
    st.dataframe(df_a.rename(columns={"bowler":"Bowler","wickets":"Wickets",
                                       "runs_conceded":"Runs","bowling_avg":"Average"}),
                 use_container_width=True, hide_index=True)

# -- Season bowling trends ----------------------------------------------------
st.markdown('<div class="section-header">Season Bowling Trends</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def cached_trends(): return get_season_bowling_trends()

with st.spinner():
    try: trend_data = cached_trends()
    except Exception as e: st.error(str(e)); trend_data = []

if trend_data:
    df_t = pd.DataFrame(trend_data)
    df_t["season_display"] = df_t["season"].apply(format_season)
    df_t["sort_key"] = df_t["season"].apply(season_sort_key)
    df_t = df_t.sort_values("sort_key")

    fig3 = px.line(df_t, x="season_display", y="wickets", markers=True,
                   title="Bowler-Credited Wickets Per Season",
                   color_discrete_sequence=["#ef4444"],
                   labels={"season_display": "Season", "wickets": "Wickets"})
    fig3.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                       font_color="#e2e8f0", xaxis_tickangle=-45)
    fig3.update_xaxes(type="category")
    fig3.update_traces(connectgaps=True, line_width=2.5)
    st.plotly_chart(fig3, use_container_width=True)
