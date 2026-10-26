"""
importer/migrate_canonical_teams.py
Idempotent migration utility to populate canonical franchise fields in existing
matches and deliveries collections in MongoDB.

Preserves all original raw team names while creating:
- matches.canonical_teams
- matches.canonical_winner
- matches.canonical_toss_winner
- deliveries.canonical_batting_team
- deliveries.canonical_bowling_team
"""
from __future__ import annotations

import time
from database.connection import get_db, close_client
from analytics.team_mapping import (
    FRANCHISE_MAPPINGS,
    normalize_team_name,
    normalize_team_list,
    get_canonical_team_expr,
)
import config


def migrate_matches() -> dict:
    """Idempotently add canonical team fields to matches."""
    db = get_db()
    matches_coll = db[config.COLLECTION_MATCHES]
    total = matches_coll.count_documents({})
    print(f"Migrating {total} match documents...")

    # Update using aggregation pipeline update
    res = matches_coll.update_many(
        {},
        [
            {
                "$set": {
                    "canonical_teams": {
                        "$map": {
                            "input": "$teams",
                            "as": "t",
                            "in": get_canonical_team_expr("$$t"),
                        }
                    },
                    "canonical_winner": get_canonical_team_expr("$winner"),
                    "canonical_toss_winner": get_canonical_team_expr("$toss_winner"),
                }
            }
        ],
    )
    print(f"Matches migration complete: {res.modified_count} documents updated.")
    return {"total": total, "modified": res.modified_count}


def migrate_deliveries() -> dict:
    """Idempotently add canonical team fields to deliveries."""
    db = get_db()
    deliveries_coll = db[config.COLLECTION_DELIVERIES]
    print("Migrating delivery documents with historical franchise names...")

    # Step 1: Update specifically the historical renamed franchises
    renamed_pairs = [
        (raw, canonical)
        for raw, canonical in FRANCHISE_MAPPINGS.items()
        if raw != canonical
    ]

    updated_count = 0
    for raw, canonical in renamed_pairs:
        # Update batting team
        r_bat = deliveries_coll.update_many(
            {"batting_team": raw},
            {"$set": {"canonical_batting_team": canonical}},
        )
        # Update bowling team
        r_bowl = deliveries_coll.update_many(
            {"bowling_team": raw},
            {"$set": {"canonical_bowling_team": canonical}},
        )
        updated_count += r_bat.modified_count + r_bowl.modified_count
        print(f"  Mapped '{raw}' -> '{canonical}' (bat: {r_bat.modified_count}, bowl: {r_bowl.modified_count})")

    # Step 2: For remaining teams, set canonical to raw name using indexed lookup
    remaining_teams = deliveries_coll.distinct("batting_team")
    for t in remaining_teams:
        if t in FRANCHISE_MAPPINGS and FRANCHISE_MAPPINGS[t] != t:
            continue
        deliveries_coll.update_many(
            {"batting_team": t, "canonical_batting_team": {"$exists": False}},
            {"$set": {"canonical_batting_team": t}},
        )
        deliveries_coll.update_many(
            {"bowling_team": t, "canonical_bowling_team": {"$exists": False}},
            {"$set": {"canonical_bowling_team": t}},
        )
    print("  All deliveries canonical team fields verified.")

    return {"renamed_updates": updated_count}


def run_migration() -> None:
    t0 = time.perf_counter()
    print("=" * 60)
    print("  Starting CricketIQ Canonical Franchise Migration")
    print("=" * 60)
    try:
        migrate_matches()
        migrate_deliveries()
        elapsed = round(time.perf_counter() - t0, 2)
        print("=" * 60)
        print(f"  Migration finished successfully in {elapsed}s")
        print("=" * 60)
    finally:
        close_client()


if __name__ == "__main__":
    run_migration()
