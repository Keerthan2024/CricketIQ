"""
pages/5_Match_Explorer.py - Browse individual match details and deliveries.
"""
import streamlit as st
import pandas as pd
from database.connection import get_db
from analytics.teams import get_all_seasons
import config

from ui.theme import STADIUM_CSS, apply_plotly_theme

st.set_page_config(page_title="Match Centre -- CricketIQ STADIUM X", page_icon=None, layout="wide")
st.markdown(STADIUM_CSS, unsafe_allow_html=True)

st.markdown("# Match Explorer")
st.markdown("*Browse season, match, innings and inspect individual delivery records.*")
st.markdown("---")

@st.cache_resource
def get_db_handle():
    try:
        db = get_db(); db.command("ping"); return db, None
    except Exception as e: return None, str(e)

db, err = get_db_handle()
if err:
    st.error(f"DB not connected: {err}"); st.stop()

@st.cache_data(ttl=300)
def cached_seasons(): return get_all_seasons()

seasons = cached_seasons()
if not seasons:
    st.info("No data found. Please import IPL data first."); st.stop()

sel_season = st.selectbox("Select Season", seasons, key="explorer_season")

# Fetch matches for this season
@st.cache_data(ttl=300)
def get_matches_for_season(season):
    matches = list(db[config.COLLECTION_MATCHES].find(
        {"season": season},
        {"match_id":1,"date":1,"teams":1,"venue":1,"winner":1,"result":1,"player_of_match":1,"_id":0}
    ).sort("date", 1))
    return matches

with st.spinner("Loading matches..."):
    season_matches = get_matches_for_season(sel_season)

if not season_matches:
    st.info(f"No matches found for season {sel_season}."); st.stop()

# Build display labels
def match_label(m):
    teams = " vs ".join(m.get("teams", ["?","?"]))
    date = m.get("date","?")
    venue = m.get("venue","?")
    return f"{date} | {teams} | {venue}"

match_options = {match_label(m): m["match_id"] for m in season_matches}

sel_match_label = st.selectbox("Select Match", list(match_options.keys()), key="explorer_match")
sel_match_id = match_options[sel_match_label]

# -- Match details ------------------------------------------------------------
@st.cache_data(ttl=300)
def get_match_detail(match_id):
    return db[config.COLLECTION_MATCHES].find_one({"match_id": match_id}, {"_id":0})

match = get_match_detail(sel_match_id)
if match:
    teams = match.get("teams", [])
    winner = match.get("winner", "N/A")
    st.markdown(f"""
<div class="match-card">
  <h3 style="color:#f59e0b;margin:0 0 .5rem">{" vs ".join(teams)}</h3>
  <table style="width:100%;color:#e2e8f0;font-size:.9rem">
    <tr><td style="color:#94a3b8">Date</td><td>{match.get("date","N/A")}</td>
        <td style="color:#94a3b8">Venue</td><td>{match.get("venue","N/A")}</td></tr>
    <tr><td style="color:#94a3b8">Winner</td><td style="color:#22c55e;font-weight:600">{winner}</td>
        <td style="color:#94a3b8">Result</td><td>{match.get("result","N/A")}</td></tr>
    <tr><td style="color:#94a3b8">Toss Winner</td><td>{match.get("toss_winner","N/A")}</td>
        <td style="color:#94a3b8">Toss Decision</td><td>{match.get("toss_decision","N/A")}</td></tr>
    <tr><td style="color:#94a3b8">Player of Match</td>
        <td colspan="3">{", ".join(match.get("player_of_match",[]) or ["N/A"])}</td></tr>
  </table>
</div>""", unsafe_allow_html=True)

# -- Innings summary ----------------------------------------------------------
st.markdown('<div class="section-header">Innings Summary</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def get_innings_summary(match_id):
    pipeline = [
        {"$match": {"match_id": match_id}},
        {"$group": {
            "_id": {"innings": "$innings", "batting_team": "$batting_team"},
            "runs": {"$sum": "$total_runs"},
            "wickets": {"$sum": {"$cond": [{"$ne": ["$wicket_kind", None]}, 1, 0]}},
            "balls": {"$sum": {"$cond": [{"$gt": [{"$ifNull": ["$extras.wides", 0]}, 0]}, 0, 1]}},
        }},
        {"$sort": {"_id.innings": 1}},
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))

inn_data = get_innings_summary(sel_match_id)
if inn_data:
    cols = st.columns(len(inn_data))
    for i, inn in enumerate(inn_data):
        team = inn["_id"]["batting_team"]
        runs = inn["runs"]; wkts = inn["wickets"]
        with cols[i]:
            st.metric(f"Innings {inn['_id']['innings']} -- {team}", f"{runs}/{wkts}")

# -- Batter performance -------------------------------------------------------
st.markdown('<div class="section-header">Batter Performance</div>', unsafe_allow_html=True)

sel_innings = st.selectbox("Innings", [1, 2] + ([3,4] if len(inn_data)>2 else []), key="inn_sel")

@st.cache_data(ttl=300)
def get_batter_stats(match_id, innings):
    pipeline = [
        {"$match": {"match_id": match_id, "innings": innings}},
        {"$group": {
            "_id": "$batter",
            "runs": {"$sum": "$batter_runs"},
            "balls": {"$sum": 1},
            "fours": {"$sum": {"$cond": [{"$eq": ["$batter_runs",4]},1,0]}},
            "sixes": {"$sum": {"$cond": [{"$eq": ["$batter_runs",6]},1,0]}},
        }},
        {"$sort": {"runs": -1}},
        {"$project": {"_id":0,"batter":"$_id","runs":1,"balls":1,"fours":1,"sixes":1,
            "sr": {"$round":[{"$multiply":[{"$divide":["$runs",{"$max":["$balls",1]}]},100]},2]}}},
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))

@st.cache_data(ttl=300)
def get_bowler_stats(match_id, innings):
    pipeline = [
        {"$match": {"match_id": match_id, "innings": innings}},
        {"$group": {
            "_id": "$bowler",
            "runs": {"$sum": {"$add":["$batter_runs",{"$ifNull":["$extras.wides",0]},{"$ifNull":["$extras.noballs",0]}]}},
            "wkts": {"$sum": {"$cond": [{"$in":["$wicket_kind", list(config.BOWLER_CREDITED_DISMISSALS)]},1,0]}},
            "balls": {"$sum": {"$cond":[{"$gt":[{"$ifNull":["$extras.wides",0]},0]},0,1]}},
        }},
        {"$sort": {"wkts": -1}},
        {"$project": {"_id":0,"bowler":"$_id","runs":1,"wkts":1,
            "overs": {"$round":[{"$divide":["$balls",6]},1]},
            "economy": {"$round":[{"$cond":[{"$gt":["$balls",0]},
                {"$divide":["$runs",{"$divide":["$balls",6]}]},0]},2]}}},
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))

col_bat, col_bowl = st.columns(2)
with col_bat:
    st.markdown("**Batting Scorecard**")
    bat_stats = get_batter_stats(sel_match_id, sel_innings)
    if bat_stats:
        st.dataframe(pd.DataFrame(bat_stats).rename(columns={
            "batter":"Batter","runs":"R","balls":"B","fours":"4s","sixes":"6s","sr":"SR"}),
            use_container_width=True, hide_index=True)
with col_bowl:
    st.markdown("**Bowling Figures**")
    bowl_stats = get_bowler_stats(sel_match_id, sel_innings)
    if bowl_stats:
        st.dataframe(pd.DataFrame(bowl_stats).rename(columns={
            "bowler":"Bowler","overs":"O","runs":"R","wkts":"W","economy":"Econ"}),
            use_container_width=True, hide_index=True)

# -- Ball-by-ball -------------------------------------------------------------
with st.expander("?? Ball-by-Ball Delivery Log"):
    @st.cache_data(ttl=300)
    def get_deliveries(match_id, innings):
        docs = list(db[config.COLLECTION_DELIVERIES].find(
            {"match_id": match_id, "innings": innings},
            {"_id":0,"over":1,"delivery":1,"batter":1,"bowler":1,
             "batter_runs":1,"extras_runs":1,"total_runs":1,"wicket_kind":1,"dismissed_batter":1},
        ).sort([("over",1),("delivery",1)]))
        return docs

    raw = get_deliveries(sel_match_id, sel_innings)
    if raw:
        df_del = pd.DataFrame(raw)
        df_del["ball"] = df_del["over"].astype(str) + "." + df_del["delivery"].astype(str)
        cols_show = ["ball","batter","bowler","batter_runs","extras_runs","total_runs","wicket_kind","dismissed_batter"]
        st.dataframe(df_del[[c for c in cols_show if c in df_del.columns]].rename(columns={
            "ball":"Ball","batter":"Batter","bowler":"Bowler","batter_runs":"Bat R",
            "extras_runs":"Ext","total_runs":"Total","wicket_kind":"Wkt","dismissed_batter":"Out"}),
            use_container_width=True, hide_index=True)
    else:
        st.info("No delivery data for this innings.")
