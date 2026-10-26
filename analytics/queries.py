"""
analytics/queries.py
Eight documented MongoDB aggregation pipelines for CricketIQ.

Each query function returns a list of result documents from MongoDB.
The pipeline stages are explained in inline comments and in
docs/aggregation_queries.md.
"""
from __future__ import annotations
from database.connection import get_db
from analytics.team_mapping import (
    get_canonical_team_expr,
    normalize_team_name,
    get_historical_names,
)
import config

BOWLER_CREDITED = list({
    "bowled", "caught", "caught and bowled",
    "lbw", "stumped", "hit wicket", "hit the ball twice",
})


# ---------------------------------------------------------------------------
# Q1 -- Top 20 run-scorers (all time)
# ---------------------------------------------------------------------------
def q1_top_run_scorers(season: str | None = None, limit: int = 20) -> list[dict]:
    """
    Purpose: Rank batters by total runs scored.
    Stages: $match (optional) ? $group ? $sort ? $limit ? $project
    """
    db = get_db()
    match_stage = {}
    if season and season != "All":
        match_stage["season"] = season

    pipeline = [
        {"$match": match_stage} if match_stage else {"$match": {}},
        {
            "$group": {
                "_id": "$batter",
                "total_runs": {"$sum": "$batter_runs"},
                "balls_faced": {"$sum": 1},
                "innings": {"$addToSet": {"match_id": "$match_id", "innings": "$innings"}},
                "fours": {"$sum": {"$cond": [{"$eq": ["$batter_runs", 4]}, 1, 0]}},
                "sixes": {"$sum": {"$cond": [{"$eq": ["$batter_runs", 6]}, 1, 0]}},
            }
        },
        {"$sort": {"total_runs": -1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 0,
                "batter": "$_id",
                "total_runs": 1,
                "balls_faced": 1,
                "innings_count": {"$size": "$innings"},
                "fours": 1,
                "sixes": 1,
                "strike_rate": {
                    "$cond": [
                        {"$gt": ["$balls_faced", 0]},
                        {"$round": [{"$multiply": [{"$divide": ["$total_runs", "$balls_faced"]}, 100]}, 2]},
                        0
                    ]
                },
            }
        },
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))


# ---------------------------------------------------------------------------
# Q2 -- Top 20 wicket-takers (bowler-credited only)
# ---------------------------------------------------------------------------
def q2_top_wicket_takers(season: str | None = None, limit: int = 20) -> list[dict]:
    """
    Purpose: Rank bowlers by wickets credited to them (not run-outs etc.).
    Stages: $match ? $group ? $sort ? $limit ? $project
    """
    db = get_db()
    match_stage: dict = {"wicket_kind": {"$in": BOWLER_CREDITED}}
    if season and season != "All":
        match_stage["season"] = season

    pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": "$bowler",
                "wickets": {"$sum": 1},
                "matches": {"$addToSet": "$match_id"},
            }
        },
        {"$sort": {"wickets": -1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 0,
                "bowler": "$_id",
                "wickets": 1,
                "matches": {"$size": "$matches"},
            }
        },
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))


# ---------------------------------------------------------------------------
# Q3 -- Bowling economy (min 30 overs bowled)
# ---------------------------------------------------------------------------
def q3_bowling_economy(season: str | None = None, limit: int = 20) -> list[dict]:
    """
    Purpose: Calculate economy rate per bowler.
             Runs conceded = batter_runs + wides + no-balls (not byes/leg-byes).
    Stages: $match ? $group ? $match (min overs) ? $sort ? $limit ? $project
    """
    db = get_db()
    match_stage = {}
    if season and season != "All":
        match_stage["season"] = season

    pipeline = [
        {"$match": match_stage} if match_stage else {"$match": {}},
        {
            "$group": {
                "_id": "$bowler",
                "batter_runs": {"$sum": "$batter_runs"},
                "wides": {"$sum": {"$ifNull": ["$extras.wides", 0]}},
                "noballs": {"$sum": {"$ifNull": ["$extras.noballs", 0]}},
                # Count legal deliveries for overs calculation
                "legal_balls": {
                    "$sum": {
                        "$cond": [
                            {"$or": [
                                {"$gt": [{"$ifNull": ["$extras.wides", 0]}, 0]},
                            ]},
                            0, 1
                        ]
                    }
                },
            }
        },
        {
            "$addFields": {
                "runs_conceded": {"$add": ["$batter_runs", "$wides", "$noballs"]},
                "overs_bowled": {"$divide": ["$legal_balls", 6]},
            }
        },
        {"$match": {"overs_bowled": {"$gte": 30}}},
        {
            "$addFields": {
                "economy": {
                    "$cond": [
                        {"$gt": ["$overs_bowled", 0]},
                        {"$round": [{"$divide": ["$runs_conceded", "$overs_bowled"]}, 2]},
                        None
                    ]
                }
            }
        },
        {"$sort": {"economy": 1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 0,
                "bowler": "$_id",
                "runs_conceded": 1,
                "overs_bowled": {"$round": ["$overs_bowled", 1]},
                "economy": 1,
            }
        },
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))


# ---------------------------------------------------------------------------
# Q4 -- Team win/loss record
# ---------------------------------------------------------------------------
def q4_team_records(season: str | None = None) -> list[dict]:
    """
    Purpose: Count matches played, wins, and compute win percentage per team.
    Stages: $match (optional) ? $unwind ? $group ? $sort ? $project
    Uses the matches collection.
    """
    db = get_db()
    match_stage = {"winner": {"$exists": True, "$ne": None}}
    if season and season != "All":
        match_stage["season"] = season

    # First get all matches and expand teams
    pipeline = [
        {"$match": {"season": match_stage.get("season", {"$exists": True})} if season and season != "All"
         else {"$match": {}}},
        {"$match": {}},
        {"$unwind": "$teams"},
        {
            "$group": {
                "_id": "$teams",
                "matches_played": {"$sum": 1},
                "wins": {
                    "$sum": {"$cond": [{"$eq": ["$winner", "$teams"]}, 1, 0]}
                },
            }
        },
        {
            "$addFields": {
                "losses": {"$subtract": ["$matches_played", "$wins"]},
                "win_pct": {
                    "$cond": [
                        {"$gt": ["$matches_played", 0]},
                        {"$round": [{"$multiply": [{"$divide": ["$wins", "$matches_played"]}, 100]}, 1]},
                        0,
                    ]
                },
            }
        },
        {"$sort": {"wins": -1}},
        {
            "$project": {
                "_id": 0,
                "team": "$_id",
                "matches_played": 1,
                "wins": 1,
                "losses": 1,
                "win_pct": 1,
            }
        },
    ]

    pipeline = [
        {"$match": {"season": season} if season and season != "All" else {}},
        {"$unwind": "$teams"},
        {
            "$project": {
                "team": get_canonical_team_expr("$teams"),
                "winner": get_canonical_team_expr("$winner"),
                "match_id": "$match_id",
            }
        },
        {
            "$group": {
                "_id": "$team",
                "matches_played": {"$sum": 1},
                "wins": {"$sum": {"$cond": [{"$eq": ["$winner", "$team"]}, 1, 0]}},
            }
        },
        {
            "$addFields": {
                "losses": {"$subtract": ["$matches_played", "$wins"]},
                "win_pct": {
                    "$round": [
                        {"$multiply": [{"$divide": ["$wins", {"$max": ["$matches_played", 1]}]}, 100]},
                        1
                    ]
                },
            }
        },
        {"$sort": {"wins": -1, "win_pct": -1}},
        {"$project": {"_id": 0, "team": "$_id", "matches_played": 1, "wins": 1, "losses": 1, "win_pct": 1}},
    ]
    return list(db[config.COLLECTION_MATCHES].aggregate(pipeline))


# ---------------------------------------------------------------------------
# Q5 -- Average first-innings score by venue
# ---------------------------------------------------------------------------
def q5_venue_avg_first_innings(limit: int = 20) -> list[dict]:
    """
    Purpose: Calculate average 1st-innings total runs per venue.
    Stages: $match (innings==1) ? $group by match+venue ? $group by venue ? $sort ? $limit
    """
    db = get_db()
    pipeline = [
        {"$match": {"innings": 1}},
        {
            "$group": {
                "_id": {"match_id": "$match_id", "batting_team": "$batting_team"},
                "total_runs": {"$sum": "$total_runs"},
                "venue": {"$first": "$batting_team"},  # placeholder
            }
        },
        # Lookup venue from matches collection
        {
            "$lookup": {
                "from": config.COLLECTION_MATCHES,
                "localField": "_id.match_id",
                "foreignField": "match_id",
                "as": "match_info",
            }
        },
        {"$unwind": "$match_info"},
        {
            "$group": {
                "_id": "$match_info.venue",
                "avg_first_innings": {"$avg": "$total_runs"},
                "matches": {"$sum": 1},
                "highest": {"$max": "$total_runs"},
            }
        },
        {"$match": {"matches": {"$gte": 5}}},
        {"$sort": {"avg_first_innings": -1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 0,
                "venue": "$_id",
                "avg_first_innings": {"$round": ["$avg_first_innings", 1]},
                "matches": 1,
                "highest": 1,
            }
        },
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))


# ---------------------------------------------------------------------------
# Q6 -- Season-by-season run totals
# ---------------------------------------------------------------------------
def q6_season_run_totals() -> list[dict]:
    """
    Purpose: Aggregate total runs and matches per season for trend charts.
    Stages: $group ? $sort ? $project
    """
    db = get_db()
    pipeline = [
        {
            "$group": {
                "_id": "$season",
                "total_runs": {"$sum": "$total_runs"},
                "total_wickets": {
                    "$sum": {"$cond": [{"$ne": ["$wicket_kind", None]}, 1, 0]}
                },
                "matches": {"$addToSet": "$match_id"},
            }
        },
        {"$sort": {"_id": 1}},
        {
            "$project": {
                "_id": 0,
                "season": "$_id",
                "total_runs": 1,
                "total_wickets": 1,
                "matches": {"$size": "$matches"},
            }
        },
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))


# ---------------------------------------------------------------------------
# Q7 -- Player innings-level consistency (standard deviation of innings scores)
# ---------------------------------------------------------------------------
def q7_player_consistency(min_innings: int = 20, limit: int = 30) -> list[dict]:
    """
    Purpose: Measure consistency via standard deviation of innings scores.
             A lower std_dev indicates more consistent (but not necessarily better) scoring.
    Stages: $group (per batter+match+innings) ? $group (per batter stats) ? $match ? $sort
    """
    db = get_db()
    pipeline = [
        # Step 1: sum runs per batter per innings
        {
            "$group": {
                "_id": {"match_id": "$match_id", "innings": "$innings", "batter": "$batter"},
                "innings_runs": {"$sum": "$batter_runs"},
            }
        },
        # Step 2: collect innings scores per batter
        {
            "$group": {
                "_id": "$_id.batter",
                "innings_scores": {"$push": "$innings_runs"},
                "innings_count": {"$sum": 1},
                "total_runs": {"$sum": "$innings_runs"},
                "avg": {"$avg": "$innings_runs"},
            }
        },
        {"$match": {"innings_count": {"$gte": min_innings}}},
        {
            "$addFields": {
                "std_dev": {
                    "$round": [
                        {"$stdDevSamp": "$innings_scores"},
                        2
                    ]
                },
                "average": {"$round": ["$avg", 2]},
            }
        },
        {"$sort": {"std_dev": 1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 0,
                "batter": "$_id",
                "innings_count": 1,
                "total_runs": 1,
                "average": 1,
                "std_dev": 1,
            }
        },
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))


# ---------------------------------------------------------------------------
# Q8 -- Head-to-head between two teams
# ---------------------------------------------------------------------------
def q8_head_to_head(team1: str, team2: str) -> dict:
    """
    Purpose: Compare match results between two specific teams (canonical franchises).
    Stages: $match (historical names for both franchises) ? $project ? $group ? $project
    """
    db = get_db()
    canonical1 = normalize_team_name(team1)
    canonical2 = normalize_team_name(team2)
    names1 = get_historical_names(team1)
    names2 = get_historical_names(team2)

    pipeline = [
        {
            "$match": {
                "$and": [
                    {"teams": {"$in": names1}},
                    {"teams": {"$in": names2}},
                ]
            }
        },
        {
            "$project": {
                "winner": get_canonical_team_expr("$winner"),
            }
        },
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "team1_wins": {"$sum": {"$cond": [{"$eq": ["$winner", canonical1]}, 1, 0]}},
                "team2_wins": {"$sum": {"$cond": [{"$eq": ["$winner", canonical2]}, 1, 0]}},
                "no_result": {"$sum": {"$cond": [{"$eq": ["$winner", None]}, 1, 0]}},
            }
        },
        {
            "$project": {
                "_id": 0,
                "total_matches": "$total",
                "team1_wins": 1,
                "team2_wins": 1,
                "no_result": 1,
            }
        },
    ]
    results = list(db[config.COLLECTION_MATCHES].aggregate(pipeline))
    return results[0] if results else {}


# ---------------------------------------------------------------------------
# Dynamic Latest Match Showcase
# ---------------------------------------------------------------------------
def get_latest_match_showcase() -> dict | None:
    """
    Retrieve the most recent completed match from MongoDB along with
    real-time innings score breakdowns from the deliveries collection.
    """
    try:
        db = get_db()
        match = db[config.COLLECTION_MATCHES].find_one({}, sort=[("date", -1)])
        if not match:
            return None

        mid = match.get("match_id")
        pipeline = [
            {"$match": {"match_id": mid}},
            {"$group": {
                "_id": {"innings": "$innings", "batting_team": "$batting_team"},
                "runs": {"$sum": "$total_runs"},
                "wickets": {"$sum": {"$cond": [{"$ne": ["$wicket_kind", None]}, 1, 0]}},
                "legal_balls": {"$sum": {"$cond": [
                    {"$or": [
                        {"$gt": [{"$ifNull": ["$extras.wides", 0]}, 0]},
                        {"$gt": [{"$ifNull": ["$extras.noballs", 0]}, 0]}
                    ]}, 0, 1
                ]}}
            }},
            {"$sort": {"_id.innings": 1}}
        ]
        inns = list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))

        formatted_innings = []
        for inn in inns:
            balls = inn.get("legal_balls", 0)
            overs = f"{balls // 6}.{balls % 6}"
            formatted_innings.append({
                "innings": inn["_id"]["innings"],
                "team": inn["_id"]["batting_team"],
                "runs": inn.get("runs", 0),
                "wickets": inn.get("wickets", 0),
                "overs": overs,
            })

        return {
            "match_id": mid,
            "season": match.get("season"),
            "date": match.get("date"),
            "venue": match.get("venue"),
            "teams": match.get("teams", []),
            "winner": match.get("winner"),
            "result": match.get("result"),
            "player_of_match": match.get("player_of_match", []),
            "innings": formatted_innings,
        }
    except Exception:
        return None

