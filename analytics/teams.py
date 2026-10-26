"""
analytics/teams.py - Team-level analytics aggregation pipelines with canonical franchise normalization.
"""
from __future__ import annotations
from database.connection import get_db
from analytics.team_mapping import (
    normalize_team_name,
    get_historical_names,
    get_canonical_team_expr,
)
import config


def get_team_records(season: str | None = None) -> list[dict]:
    """Matches played, wins, losses, win % per canonical team."""
    db = get_db()
    match_stage = {}
    if season and season != "All":
        match_stage["season"] = season
    pipeline = [
        {"$match": match_stage},
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
                        {
                            "$multiply": [
                                {"$divide": ["$wins", {"$max": ["$matches_played", 1]}]},
                                100,
                            ]
                        },
                        1,
                    ]
                },
            }
        },
        {"$sort": {"wins": -1, "win_pct": -1}},
        {"$project": {"_id": 0, "team": "$_id", "matches_played": 1, "wins": 1, "losses": 1, "win_pct": 1}},
    ]
    return list(db[config.COLLECTION_MATCHES].aggregate(pipeline))


def get_season_performance(team: str) -> list[dict]:
    """Season-by-season win record for a canonical franchise across all historical names."""
    db = get_db()
    canonical_team = normalize_team_name(team)
    historical_names = get_historical_names(team)
    pipeline = [
        {"$match": {"teams": {"$in": historical_names}}},
        {
            "$project": {
                "season": 1,
                "winner": get_canonical_team_expr("$winner"),
            }
        },
        {
            "$group": {
                "_id": "$season",
                "matches": {"$sum": 1},
                "wins": {"$sum": {"$cond": [{"$eq": ["$winner", canonical_team]}, 1, 0]}},
            }
        },
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "season": "$_id", "matches": 1, "wins": 1}},
    ]
    return list(db[config.COLLECTION_MATCHES].aggregate(pipeline))


def get_head_to_head(team1: str, team2: str) -> dict:
    """Match record between two canonical franchises across all historical encounters."""
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
        {"$project": {"_id": 0, "total_matches": "$total", "team1_wins": 1, "team2_wins": 1, "no_result": 1}},
    ]
    results = list(db[config.COLLECTION_MATCHES].aggregate(pipeline))
    return results[0] if results else {}


def get_all_teams() -> list[str]:
    """Distinct sorted list of all canonical IPL franchise names."""
    db = get_db()
    raw_teams = db[config.COLLECTION_MATCHES].distinct("teams")
    canonical_set = {normalize_team_name(t) for t in raw_teams if t}
    return sorted(list(canonical_set))


def get_all_seasons() -> list[str]:
    """Distinct sorted list of seasons."""
    db = get_db()
    seasons = db[config.COLLECTION_MATCHES].distinct("season")
    return sorted([s for s in seasons if s], key=lambda s: str(s))
