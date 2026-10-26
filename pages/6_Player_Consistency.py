"""
pages/6_Player_Consistency.py - Innings-level consistency stats using std deviation.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from analytics.queries import q7_player_consistency
from database.connection import get_db

from ui.theme import STADIUM_CSS, apply_plotly_theme

st.set_page_config(page_title="Player Consistency -- CricketIQ STADIUM X", page_icon=None, layout="wide")
st.markdown(STADIUM_CSS, unsafe_allow_html=True)

st.markdown("# Player Consistency")
st.markdown("---")

st.markdown("""
<div class="explain-box">
<strong>How consistency is measured here:</strong><br>
For each batter, we collect their runs scored across every innings.
We then compute the <strong>standard deviation (std_dev)</strong> of those innings scores.
<ul>
<li>A <em>smaller</em> std_dev means the player scores more predictably each innings.</li>
<li>A <em>larger</em> std_dev means the player has big-score / low-score swings.</li>
<li><strong>Important:</strong> A low std_dev does NOT mean the player is a better batter.
A consistent scorer of 20s may rank higher than an explosive player who scores 0s and 80s.</li>
</ul>
Minimum innings threshold is configurable. Average is total runs / innings played.
</div>
""", unsafe_allow_html=True)

@st.cache_resource
def check_db():
    try: db = get_db(); db.command("ping"); return None
    except Exception as e: return str(e)

err = check_db()
if err:
    st.error(f"DB not connected: {err}"); st.stop()

col_f1, col_f2, _ = st.columns([1,1,2])
with col_f1:
    min_inn = st.slider("Minimum Innings", 5, 50, 20, step=5, key="consist_min")
with col_f2:
    limit = st.slider("Players to show", 10, 50, 30, step=5, key="consist_limit")

@st.cache_data(ttl=300)
def cached_consistency(min_innings, lim):
    return q7_player_consistency(min_innings=min_innings, limit=lim)

with st.spinner("Computing consistency scores..."):
    try:
        data = cached_consistency(min_inn, limit)
    except Exception as e:
        st.error(f"Query failed: {e}"); st.stop()

if not data:
    st.info("Not enough data. Try reducing the minimum innings threshold."); st.stop()

df = pd.DataFrame(data)

# -- Most consistent (low std_dev) --------------------------------------------
st.markdown('<div class="section-header">Most Consistent Batters (Lowest Std Dev)</div>', unsafe_allow_html=True)

col_a, col_b = st.columns([3,2])
with col_a:
    fig = px.scatter(df, x="average", y="std_dev", text="batter",
                     color="std_dev", size="innings_count",
                     color_continuous_scale=["#22c55e","#f59e0b","#ef4444"],
                     title="Average vs Std Dev (size = innings played)",
                     labels={"average":"Batting Average","std_dev":"Std Deviation","innings_count":"Innings"})
    fig.update_traces(textposition="top center", textfont_size=8)
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                      font_color="#e2e8f0",coloraxis_colorbar=dict(title="Std Dev"))
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.dataframe(df.rename(columns={
        "batter":"Batter","innings_count":"Inn","total_runs":"Runs",
        "average":"Avg","std_dev":"Std Dev"}).style.format(
            {"Avg":"{:.1f}","Std Dev":"{:.1f}"}),
        use_container_width=True, hide_index=True)

# -- Bar chart: low std_dev players -------------------------------------------
st.markdown('<div class="section-header">Consistency Ranking (lower bar = more consistent)</div>', unsafe_allow_html=True)
fig2 = px.bar(df.head(20).sort_values("std_dev"), x="std_dev", y="batter",
              orientation="h", color="average",
              color_continuous_scale=["#1e3a5f","#06b6d4"],
              title="Std Dev of Innings Scores -- Lower = More Consistent",
              labels={"std_dev":"Std Dev","batter":"Batter","average":"Avg"})
fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                   font_color="#e2e8f0")
st.plotly_chart(fig2, use_container_width=True)
