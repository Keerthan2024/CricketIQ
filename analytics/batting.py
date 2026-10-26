"""
analytics/batting.py - Batting analytics aggregation pipelines.
"""
from __future__ import annotations
from database.connection import get_db
import config


def get_top_scorers(season: str | None = None, limit: int = 20) -> list[dict]:
    """Top run-scorers with strike rate and boundary counts."""
    db = get_db()
    match_stage = {"season": season} if season and season != "All" else {}
    pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": "$batter",
                "total_runs": {"$sum": "$batter_runs"},
                "balls_faced": {"$sum": 1},
                "fours": {"$sum": {"$cond": [{"$eq": ["$batter_runs", 4]}, 1, 0]}},
                "sixes": {"$sum": {"$cond": [{"$eq": ["$batter_runs", 6]}, 1, 0]}},
                "innings_set": {"$addToSet": {"m": "$match_id", "i": "$innings"}},
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
                "innings": {"$size": "$innings_set"},
                "fours": 1,
                "sixes": 1,
                "strike_rate": {
                    "$cond": [
                        {"$gt": ["$balls_faced", 0]},
                        {"$round": [{"$multiply": [{"$divide": ["$total_runs", "$balls_faced"]}, 100]}, 2]},
                        0,
                    ]
                },
                "batting_avg": {
                    "$cond": [
                        {"$gt": [{"$size": "$innings_set"}, 0]},
                        {"$round": [{"$divide": ["$total_runs", {"$size": "$innings_set"}]}, 2]},
                        0,
                    ]
                },
            }
        },
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))


def get_highest_innings(season: str | None = None, limit: int = 20) -> list[dict]:
    """Highest individual innings scores."""
    db = get_db()
    match_stage = {"season": season} if season and season != "All" else {}
    pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": {"batter": "$batter", "match_id": "$match_id", "innings": "$innings"},
                "runs": {"$sum": "$batter_runs"},
                "balls": {"$sum": 1},
                "fours": {"$sum": {"$cond": [{"$eq": ["$batter_runs", 4]}, 1, 0]}},
                "sixes": {"$sum": {"$cond": [{"$eq": ["$batter_runs", 6]}, 1, 0]}},
                "batting_team": {"$first": "$batting_team"},
                "season": {"$first": "$season"},
            }
        },
        {"$sort": {"runs": -1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 0,
                "batter": "$_id.batter",
                "match_id": "$_id.match_id",
                "innings": "$_id.innings",
                "runs": 1,
                "balls": 1,
                "fours": 1,
                "sixes": 1,
                "batting_team": 1,
                "season": 1,
                "strike_rate": {
                    "$cond": [
                        {"$gt": ["$balls", 0]},
                        {"$round": [{"$multiply": [{"$divide": ["$runs", "$balls"]}, 100]}, 2]},
                        0,
                    ]
                },
            }
        },
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))


def get_boundary_leaders(season: str | None = None, limit: int = 20) -> list[dict]:
    """Players with most boundaries (4s + 6s)."""
    db = get_db()
    match_stage = {"season": season} if season and season != "All" else {}
    pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": "$batter",
                "fours": {"$sum": {"$cond": [{"$eq": ["$batter_runs", 4]}, 1, 0]}},
                "sixes": {"$sum": {"$cond": [{"$eq": ["$batter_runs", 6]}, 1, 0]}},
            }
        },
        {"$addFields": {"boundaries": {"$add": ["$fours", "$sixes"]}}},
        {"$sort": {"boundaries": -1}},
        {"$limit": limit},
        {"$project": {"_id": 0, "batter": "$_id", "fours": 1, "sixes": 1, "boundaries": 1}},
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))


def get_season_batting_trends() -> list[dict]:
    """Total runs scored per season."""
    db = get_db()
    pipeline = [
        {
            "$group": {
                "_id": "$season",
                "total_runs": {"$sum": "$batter_runs"},
                "sixes": {"$sum": {"$cond": [{"$eq": ["$batter_runs", 6]}, 1, 0]}},
                "fours": {"$sum": {"$cond": [{"$eq": ["$batter_runs", 4]}, 1, 0]}},
            }
        },
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "season": "$_id", "total_runs": 1, "sixes": 1, "fours": 1}},
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))
