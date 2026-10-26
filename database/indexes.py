"""
database/indexes.py - Create and verify MongoDB indexes for CricketIQ.
"""
import pymongo
from pymongo import IndexModel, ASCENDING, DESCENDING
from database.connection import get_db
import config


def create_indexes() -> None:
    """Create all required indexes. Safe to call multiple times (idempotent)."""
    db = get_db()
    _create_match_indexes(db)
    _create_delivery_indexes(db)
    print("All indexes verified / created.")


def _create_match_indexes(db) -> None:
    coll = db[config.COLLECTION_MATCHES]
    indexes = [
        IndexModel([("match_id", ASCENDING)], unique=True, name="match_id_unique"),
        IndexModel([("season", ASCENDING)], name="season"),
        IndexModel([("teams", ASCENDING)], name="teams"),
        IndexModel([("venue", ASCENDING)], name="venue"),
        IndexModel([("date", ASCENDING)], name="date"),
        IndexModel([("winner", ASCENDING)], name="winner"),
    ]
    coll.create_indexes(indexes)


def _create_delivery_indexes(db) -> None:
    coll = db[config.COLLECTION_DELIVERIES]
    indexes = [
        IndexModel(
            [("match_id", ASCENDING), ("innings", ASCENDING),
             ("over", ASCENDING), ("delivery", ASCENDING)],
            unique=True,
            name="delivery_unique",
        ),
        IndexModel([("match_id", ASCENDING)], name="delivery_match_id"),
        IndexModel([("batter", ASCENDING)], name="batter"),
        IndexModel([("bowler", ASCENDING)], name="bowler"),
        IndexModel([("batting_team", ASCENDING)], name="batting_team"),
        IndexModel([("bowling_team", ASCENDING)], name="bowling_team"),
        IndexModel([("season", ASCENDING)], name="delivery_season"),
        IndexModel([("wicket_kind", ASCENDING)], name="wicket_kind"),
    ]
    coll.create_indexes(indexes)
