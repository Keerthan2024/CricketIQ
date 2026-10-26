"""
analytics/bowling.py - Bowling analytics aggregation pipelines.

Cricket scoring rules applied:
  - Runs conceded = batter_runs + wides + no-balls  (NOT byes/leg-byes).
  - Bowler-credited wickets exclude run-outs, obstructing the field, etc.
  - Economy = runs conceded / overs bowled  (wides are not legal deliveries).
  - Bowling average = runs conceded / bowler-credited wickets.
"""
from __future__ import annotations
from database.connection import get_db
import config

BOWLER_CREDITED = list(config.BOWLER_CREDITED_DISMISSALS)


def get_wicket_leaders(season: str | None = None, limit: int = 20) -> list[dict]:
    """Bowlers ranked by wickets credited to them."""
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
        {"$project": {"_id": 0, "bowler": "$_id", "wickets": 1, "matches": {"$size": "$matches"}}},
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))


def get_economy_leaders(season: str | None = None, min_overs: float = 20.0, limit: int = 20) -> list[dict]:
    """Bowlers with best economy (min_overs legal deliveries bowled)."""
    db = get_db()
    match_stage = {}
    if season and season != "All":
        match_stage["season"] = season
    pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": "$bowler",
                "batter_runs": {"$sum": "$batter_runs"},
                "wides": {"$sum": {"$ifNull": ["$extras.wides", 0]}},
                "noballs": {"$sum": {"$ifNull": ["$extras.noballs", 0]}},
                "legal_balls": {
                    "$sum": {
                        "$cond": [{"$gt": [{"$ifNull": ["$extras.wides", 0]}, 0]}, 0, 1]
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
        {"$match": {"overs_bowled": {"$gte": min_overs}}},
        {
            "$addFields": {
                "economy": {
                    "$round": [{"$divide": ["$runs_conceded", "$overs_bowled"]}, 2]
                }
            }
        },
        {"$sort": {"economy": 1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 0, "bowler": "$_id",
                "runs_conceded": 1,
                "overs_bowled": {"$round": ["$overs_bowled", 1]},
                "economy": 1,
            }
        },
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))


def get_bowling_averages(season: str | None = None, min_wickets: int = 10, limit: int = 20) -> list[dict]:
    """Bowling average = runs conceded / wickets (bowler credited)."""
    db = get_db()
    match_stage = {}
    if season and season != "All":
        match_stage["season"] = season

    pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": "$bowler",
                "batter_runs": {"$sum": "$batter_runs"},
                "wides": {"$sum": {"$ifNull": ["$extras.wides", 0]}},
                "noballs": {"$sum": {"$ifNull": ["$extras.noballs", 0]}},
                "wickets": {
                    "$sum": {
                        "$cond": [{"$in": ["$wicket_kind", BOWLER_CREDITED]}, 1, 0]
                    }
                },
            }
        },
        {
            "$addFields": {
                "runs_conceded": {"$add": ["$batter_runs", "$wides", "$noballs"]},
            }
        },
        {"$match": {"wickets": {"$gte": min_wickets}}},
        {
            "$addFields": {
                "bowling_avg": {
                    "$round": [{"$divide": ["$runs_conceded", "$wickets"]}, 2]
                }
            }
        },
        {"$sort": {"bowling_avg": 1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 0, "bowler": "$_id",
                "wickets": 1, "runs_conceded": 1, "bowling_avg": 1,
            }
        },
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))


def get_season_bowling_trends() -> list[dict]:
    """Total wickets and runs conceded per season."""
    db = get_db()
    pipeline = [
        {
            "$group": {
                "_id": "$season",
                "wickets": {
                    "$sum": {"$cond": [{"$in": ["$wicket_kind", BOWLER_CREDITED]}, 1, 0]}
                },
                "runs": {"$sum": {"$add": ["$batter_runs", {"$ifNull": ["$extras.wides", 0]},
                                           {"$ifNull": ["$extras.noballs", 0]}]}},
            }
        },
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "season": "$_id", "wickets": 1, "runs": 1}},
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))
