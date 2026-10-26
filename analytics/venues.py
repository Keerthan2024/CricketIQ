"""
analytics/venues.py - Venue-level analytics aggregation pipelines.
"""
from __future__ import annotations
from database.connection import get_db
from analytics.venue_mapping import normalize_venue_name, get_canonical_venue_expr
import config


def get_matches_by_venue(limit: int = 20) -> list[dict]:
    """Count of matches per canonical venue."""
    db = get_db()
    pipeline = [
        {"$addFields": {"canonical_venue": get_canonical_venue_expr("$venue")}},
        {"$group": {"_id": "$canonical_venue", "matches": {"$sum": 1}}},
        {"$sort": {"matches": -1}},
        {"$limit": limit},
        {"$project": {"_id": 0, "venue": "$_id", "matches": 1}},
    ]
    return list(db[config.COLLECTION_MATCHES].aggregate(pipeline))


def get_avg_first_innings_by_venue(min_matches: int = 5, limit: int = 20) -> list[dict]:
    """Average and highest first-innings score per canonical venue."""
    db = get_db()
    pipeline = [
        {"$match": {"innings": 1}},
        {
            "$group": {
                "_id": {"match_id": "$match_id"},
                "total": {"$sum": "$total_runs"},
                "match_id": {"$first": "$match_id"},
            }
        },
        {
            "$lookup": {
                "from": config.COLLECTION_MATCHES,
                "localField": "_id.match_id",
                "foreignField": "match_id",
                "as": "m",
            }
        },
        {"$unwind": "$m"},
        {"$addFields": {"canonical_venue": get_canonical_venue_expr("$m.venue")}},
        {
            "$group": {
                "_id": "$canonical_venue",
                "avg_score": {"$avg": "$total"},
                "highest": {"$max": "$total"},
                "matches": {"$sum": 1},
            }
        },
        {"$match": {"matches": {"$gte": min_matches}}},
        {"$sort": {"avg_score": -1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 0,
                "venue": "$_id",
                "avg_score": {"$round": ["$avg_score", 1]},
                "highest": 1,
                "matches": 1,
            }
        },
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))


def get_runs_by_venue(limit: int = 20) -> list[dict]:
    """Total runs scored at each canonical venue."""
    db = get_db()
    pipeline = [
        {
            "$lookup": {
                "from": config.COLLECTION_MATCHES,
                "localField": "match_id",
                "foreignField": "match_id",
                "as": "m",
            }
        },
        {"$unwind": "$m"},
        {"$addFields": {"canonical_venue": get_canonical_venue_expr("$m.venue")}},
        {
            "$group": {
                "_id": "$canonical_venue",
                "total_runs": {"$sum": "$total_runs"},
                "matches": {"$addToSet": "$match_id"},
            }
        },
        {"$sort": {"total_runs": -1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 0,
                "venue": "$_id",
                "total_runs": 1,
                "matches": {"$size": "$matches"},
            }
        },
    ]
    return list(db[config.COLLECTION_DELIVERIES].aggregate(pipeline))


def get_all_venues() -> list[str]:
    """List of all distinct canonical venues."""
    db = get_db()
    raw_venues = db[config.COLLECTION_MATCHES].distinct("venue")
    canonical = {normalize_venue_name(v) for v in raw_venues if v}
    return sorted(list(canonical))
