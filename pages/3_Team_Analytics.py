"""
pages/3_Team_Analytics.py - Team win/loss records and head-to-head.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from analytics.teams import get_team_records, get_season_performance, get_head_to_head, get_all_teams, get_all_seasons
from analytics.team_mapping import format_season, season_sort_key
from database.connection import get_db

from ui.theme import STADIUM_CSS, apply_plotly_theme

st.set_page_config(page_title="Team Arena -- CricketIQ STADIUM X", page_icon=None, layout="wide")
st.markdown(STADIUM_CSS, unsafe_allow_html=True)

st.markdown("# Team Analytics")
st.markdown("""
*Historical franchise names are unified under their canonical identities
(e.g., Royal Challengers Bangalore → Bengaluru, Kings XI Punjab → Punjab Kings, Delhi Daredevils → Capitals)
for continuous franchise analytics across all seasons.*
""")
st.markdown("---")

@st.cache_resource
def check_db():
    try:
        db = get_db(); db.command("ping"); return None
    except Exception as e: return str(e)

err = check_db()
if err:
    st.error(f"DB not connected: {err}"); st.stop()

@st.cache_data(ttl=300)
def cached_seasons(): return ["All"] + get_all_seasons()
@st.cache_data(ttl=300)
def cached_teams(): return get_all_teams()

seasons = cached_seasons()
teams = cached_teams()

col_f, _ = st.columns([1,3])
with col_f:
    sel_season = st.selectbox("Season", seasons, key="team_season")

season = sel_season if sel_season != "All" else None

# -- Overall records ----------------------------------------------------------
st.markdown('<div class="section-header">Overall Team Records</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def cached_records(s): return get_team_records(s)

with st.spinner("Loading team records..."):
    try: rec_data = cached_records(season)
    except Exception as e: st.error(str(e)); rec_data = []

if rec_data:
    df = pd.DataFrame(rec_data)
    col_a, col_b = st.columns([3,2])
    with col_a:
        fig = px.bar(df, x="team", y=["wins","losses"],
                     title="Wins vs Losses by Team",
                     barmode="group",
                     color_discrete_map={"wins":"#22c55e","losses":"#ef4444"},
                     labels={"value":"Matches","variable":"Result","team":"Team"})
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                          font_color="#e2e8f0",xaxis_tickangle=-45,legend_title="")
        st.plotly_chart(fig, width='stretch')
    with col_b:
        st.dataframe(df.rename(columns={"team":"Team","matches_played":"Played",
                                         "wins":"Wins","losses":"Losses","win_pct":"Win %"}),
                     width='stretch', hide_index=True)

    # Win % treemap
    fig2 = px.treemap(df, path=["team"], values="matches_played", color="win_pct",
                      color_continuous_scale=["#1e3a5f","#22c55e"],
                      title="Team Win Percentage (size = matches played)")
    fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)",font_color="#e2e8f0")
    st.plotly_chart(fig2, width='stretch')

# -- Head-to-head -------------------------------------------------------------
st.markdown('<div class="section-header">Head-to-Head Comparison</div>', unsafe_allow_html=True)

if len(teams) >= 2:
    col1, col2 = st.columns(2)
    with col1:
        t1 = st.selectbox("Team 1", teams, key="h2h_t1")
    with col2:
        remaining = [t for t in teams if t != t1]
        t2 = st.selectbox("Team 2", remaining, key="h2h_t2")

    @st.cache_data(ttl=300)
    def cached_h2h(a,b): return get_head_to_head(a,b)

    with st.spinner():
        try: h2h = cached_h2h(t1,t2)
        except Exception as e: st.error(str(e)); h2h = {}

    if h2h:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total Matches", h2h.get("total_matches",0))
        c2.metric(f"{t1} Wins", h2h.get("team1_wins",0))
        c3.metric(f"{t2} Wins", h2h.get("team2_wins",0))
        c4.metric("No Result", h2h.get("no_result",0))

        fig3 = go.Figure(go.Pie(
            labels=[t1, t2, "No Result"],
            values=[h2h.get("team1_wins",0), h2h.get("team2_wins",0), h2h.get("no_result",0)],
            hole=0.4,
            marker_colors=["#3b82f6","#f59e0b","#6b7280"]))
        fig3.update_layout(title=f"{t1} vs {t2}", paper_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0")
        st.plotly_chart(fig3, width='stretch')
    else:
        st.info("No matches found between these teams.")

# -- Season performance for a single team -------------------------------------
st.markdown('<div class="section-header">Season-wise Performance</div>', unsafe_allow_html=True)

sel_team = st.selectbox("Select Team", teams, key="team_season_sel")

@st.cache_data(ttl=300)
def cached_season_perf(team): return get_season_performance(team)

with st.spinner():
    try: sp_data = cached_season_perf(sel_team)
    except Exception as e: st.error(str(e)); sp_data = []

if sp_data:
    df_sp = pd.DataFrame(sp_data)
    df_sp["season_display"] = df_sp["season"].apply(format_season)
    df_sp["sort_key"] = df_sp["season"].apply(season_sort_key)
    df_sp = df_sp.sort_values("sort_key")

    fig4 = px.line(df_sp, x="season_display", y=["matches","wins"], markers=True,
                   title=f"{sel_team} -- Season Record",
                   labels={"season_display": "Season", "value": "Count", "variable": "Metric"},
                   color_discrete_map={"matches":"#3b82f6","wins":"#22c55e"})
    fig4.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                       font_color="#e2e8f0",xaxis_tickangle=-45,legend_title="")
    fig4.update_xaxes(type="category")
    fig4.update_traces(connectgaps=True, line_width=2.5)
    st.plotly_chart(fig4, width='stretch')
else:
    st.info(f"No data for {sel_team}.")
