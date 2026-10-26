"""
pages/4_Venue_Analytics.py - Venue-level statistics.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from analytics.venues import get_matches_by_venue, get_avg_first_innings_by_venue, get_runs_by_venue, get_all_venues
from database.connection import get_db

from ui.theme import STADIUM_CSS, apply_plotly_theme

st.set_page_config(page_title="Venue Intelligence -- CricketIQ STADIUM X", page_icon=None, layout="wide")
st.markdown(STADIUM_CSS, unsafe_allow_html=True)

st.markdown("# Venue Analytics")
st.markdown("*Historical stadium renamings (e.g., Feroz Shah Kotla → Arun Jaitley Stadium; Motera → Narendra Modi Stadium) and city-suffixed variations are unified under canonical venue identities.*")
st.markdown("---")

@st.cache_resource
def check_db():
    try:
        db = get_db(); db.command("ping"); return None
    except Exception as e: return str(e)

err = check_db()
if err:
    st.error(f"DB not connected: {err}"); st.stop()

# -- Matches by venue ---------------------------------------------------------
st.markdown('<div class="section-header">Matches Hosted by Venue</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def cached_matches_venue(): return get_matches_by_venue(limit=25)

with st.spinner("Loading venue data..."):
    try: mv_data = cached_matches_venue()
    except Exception as e: st.error(str(e)); mv_data = []

if mv_data:
    df_mv = pd.DataFrame(mv_data)
    fig = px.bar(df_mv, x="matches", y="venue", orientation="h",
                 color="matches", color_continuous_scale=["#1e3a5f","#a855f7"],
                 title="Top 25 Venues by Matches Hosted")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                      font_color="#e2e8f0",yaxis=dict(autorange="reversed"),
                      coloraxis_showscale=False, height=600)
    st.plotly_chart(fig, width='stretch')

# -- Avg first-innings score --------------------------------------------------
st.markdown('<div class="section-header">Average First-Innings Scores by Venue</div>', unsafe_allow_html=True)
st.caption("Minimum 5 matches at venue. Higher average indicates batting-friendly conditions.")

@st.cache_data(ttl=300)
def cached_avg_score(): return get_avg_first_innings_by_venue(min_matches=5, limit=20)

with st.spinner():
    try: avg_data = cached_avg_score()
    except Exception as e: st.error(str(e)); avg_data = []

if avg_data:
    df_avg = pd.DataFrame(avg_data)
    col_a, col_b = st.columns([3,2])
    with col_a:
        fig2 = px.bar(df_avg, x="avg_score", y="venue", orientation="h",
                      color="avg_score", color_continuous_scale=["#1e3a5f","#f59e0b"],
                      title="Average 1st-Innings Score",
                      error_x=None)
        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                           font_color="#e2e8f0",yaxis=dict(autorange="reversed"),
                           coloraxis_showscale=False)
        st.plotly_chart(fig2, width='stretch')
    with col_b:
        st.dataframe(df_avg.rename(columns={"venue":"Venue","avg_score":"Avg Score",
                                             "highest":"Highest","matches":"Matches"}),
                     width='stretch', hide_index=True)

# -- Total runs by venue ------------------------------------------------------
st.markdown('<div class="section-header">Total Runs Scored at Venue</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def cached_runs_venue(): return get_runs_by_venue(limit=20)

with st.spinner():
    try: rv_data = cached_runs_venue()
    except Exception as e: st.error(str(e)); rv_data = []

if rv_data:
    df_rv = pd.DataFrame(rv_data)
    fig3 = px.scatter(df_rv, x="matches", y="total_runs", text="venue",
                      size="total_runs", color="total_runs",
                      color_continuous_scale=["#1e3a5f","#a855f7"],
                      title="Total Runs vs Matches Played (per Venue)",
                      labels={"matches":"Matches Played","total_runs":"Total Runs"})
    fig3.update_traces(textposition="top center", textfont_size=9)
    fig3.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                       font_color="#e2e8f0",coloraxis_showscale=False)
    st.plotly_chart(fig3, width='stretch')
