"""
scripts/backfill_missing_deliveries.py
Safely backfill the missing 1,182 deliveries for the 5 interrupted matches
(1422125, 1422126, 1422127, 1422128, 1422129) without modifying existing data.
"""
from pathlib import Path
from pymongo import UpdateOne
from database.connection import get_db, close_client
from importer.parser import load_json_file, parse_deliveries
import config

TARGET_MATCH_IDS = ["1422125", "1422126", "1422127", "1422128", "1422129"]

db = get_db()
d_coll = db[config.COLLECTION_DELIVERIES]

print("Starting targeted delivery backfill...")
total_upserted = 0

for mid in TARGET_MATCH_IDS:
    file_path = Path(f"./data/{mid}.json")
    if not file_path.exists():
        print(f"File not found: {file_path}")
        continue

    raw = load_json_file(file_path)
    season = raw.get("info", {}).get("season", "")
    deliveries = parse_deliveries(raw, mid, season)

    ops = []
    for d in deliveries:
        ops.append(
            UpdateOne(
                {
                    "match_id": d["match_id"],
                    "innings": d["innings"],
                    "over": d["over"],
                    "delivery": d["delivery"],
                    "batter": d["batter"],
                },
                {"$setOnInsert": d},
                upsert=True,
            )
        )

    if ops:
        res = d_coll.bulk_write(ops, ordered=False)
        upserted_count = res.upserted_count
        matched_count = res.matched_count
        total_upserted += upserted_count
        print(f"Match {mid}: total={len(deliveries)}, already_present={matched_count}, newly_inserted={upserted_count}")

print(f"\nBackfill completed! Newly inserted deliveries: {total_upserted}")
final_count = d_coll.count_documents({})
print(f"Final Total Deliveries in MongoDB: {final_count:,}")
close_client()
