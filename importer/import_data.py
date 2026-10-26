"""
importer/import_data.py
CLI utility to import IPL JSON files into MongoDB.

Usage:
    python -m importer.import_data --data-dir ./data
    python -m importer.import_data --data-dir ./data --batch-size 250
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pymongo
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError, PyMongoError

import config
from database.connection import get_db, close_client
from database.indexes import create_indexes
from importer.parser import load_json_file, parse_match, parse_deliveries


def download_cricsheet_data(target_dir: str | Path) -> None:
    """Download official IPL JSON zip from Cricsheet and extract to target_dir."""
    import io
    import zipfile
    import requests

    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    url = "https://cricsheet.org/downloads/ipl_json.zip"
    print(f"Downloading IPL dataset from Cricsheet: {url} (~5.2 MB)...")
    resp = requests.get(url, timeout=45)
    resp.raise_for_status()
    print("Extracting match JSON files...")
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        z.extractall(target_dir)
    print(f"Extracted all JSON match files into {target_dir}")


def import_all(data_dir: str | Path, batch_size: int = config.BATCH_SIZE, limit: int | None = None) -> dict:
    """
    Import all JSON files from data_dir into MongoDB.
    Returns a summary dict with counts.
    """
    data_dir = Path(data_dir)
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(data_dir.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {data_dir}.")
        print("Tip: Run with --download to automatically fetch the official Cricsheet dataset:")
        print("     python -m importer.import_data --download")
        sys.exit(1)

    if limit and limit > 0:
        json_files = json_files[:limit]
        print(f"Limiting import to first {len(json_files)} matches")
    else:
        print(f"Found {len(json_files)} JSON files in {data_dir}")

    # Ensure indexes exist before import
    try:
        create_indexes()
    except PyMongoError as exc:
        print(f"ERROR creating indexes: {exc}", file=sys.stderr)
        sys.exit(1)

    db = get_db()
    matches_coll = db[config.COLLECTION_MATCHES]
    deliveries_coll = db[config.COLLECTION_DELIVERIES]

    total_files = len(json_files)
    imported_matches = 0
    skipped_matches = 0
    imported_deliveries = 0
    errors = 0
    start = time.perf_counter()

    match_ops: list[UpdateOne] = []
    delivery_ops: list[UpdateOne] = []

    # Fetch existing match_ids to allow instant resume without re-processing already imported matches
    existing_match_ids = set(matches_coll.distinct("match_id"))
    if existing_match_ids:
        print(f"Resuming import: {len(existing_match_ids)} matches already present in database.")

    for idx, path in enumerate(json_files, 1):
        if idx % 50 == 0 or idx == total_files:
            elapsed = time.perf_counter() - start
            print(f"  [{idx}/{total_files}] processed | "
                  f"matches: {imported_matches} | deliveries: {imported_deliveries} | "
                  f"elapsed: {elapsed:.1f}s", flush=True)

        # Quick check: filename usually starts with match_id (e.g. 123456.json)
        match_id_guess = path.stem
        if match_id_guess in existing_match_ids:
            skipped_matches += 1
            continue

        raw = load_json_file(path)
        if raw is None:
            errors += 1
            continue

        match_doc = parse_match(raw, source_file=str(path))
        if match_doc is None:
            errors += 1
            continue

        match_id = match_doc["match_id"]
        if match_id in existing_match_ids:
            skipped_matches += 1
            continue
        existing_match_ids.add(match_id)

        season = match_doc.get("season", "")

        # Upsert match (prevents duplicates on re-run)
        match_ops.append(
            UpdateOne({"match_id": match_id}, {"$setOnInsert": match_doc}, upsert=True)
        )

        # Parse deliveries
        dels = parse_deliveries(raw, match_id, season)
        for d in dels:
            delivery_ops.append(
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

        imported_matches += 1

        # Flush when batches reach threshold (flush every 20 matches or 3,000 deliveries)
        if len(match_ops) >= min(batch_size, 20) or len(delivery_ops) >= 3000:
            imported_matches_batch, imported_deliveries_batch, err = _flush(
                matches_coll, deliveries_coll, match_ops, delivery_ops
            )
            imported_deliveries += imported_deliveries_batch
            errors += err
            match_ops.clear()
            delivery_ops.clear()

    # Final flush
    if match_ops or delivery_ops:
        _, imported_deliveries_batch, err = _flush(
            matches_coll, deliveries_coll, match_ops, delivery_ops
        )
        imported_deliveries += imported_deliveries_batch
        errors += err

    elapsed = time.perf_counter() - start
    summary = {
        "total_files": total_files,
        "imported_matches": imported_matches,
        "skipped_matches": skipped_matches,
        "imported_deliveries": imported_deliveries,
        "errors": errors,
        "elapsed_seconds": round(elapsed, 2),
    }
    _print_summary(summary)
    return summary


def _flush(matches_coll, deliveries_coll, match_ops, delivery_ops) -> tuple[int, int, int]:
    """Execute bulk writes and return (match_count, delivery_count, error_count)."""
    m_count = d_count = err = 0
    if match_ops:
        try:
            result = matches_coll.bulk_write(match_ops, ordered=False)
            m_count = result.upserted_count + result.matched_count
        except BulkWriteError as exc:
            write_errors = [e for e in exc.details.get("writeErrors", []) if e.get("code") != 11000]
            if write_errors:
                print(f"  [WARN] {len(write_errors)} match write errors")
                err += len(write_errors)
        except Exception as exc:
            print(f"  [WARN] Match write failed: {exc}")
            err += 1

    if delivery_ops:
        # Write deliveries in small sub-batches of 1,000 documents to prevent cloud socket timeouts
        CHUNK_SIZE = 1000
        for i in range(0, len(delivery_ops), CHUNK_SIZE):
            chunk = delivery_ops[i:i + CHUNK_SIZE]
            try:
                res = deliveries_coll.bulk_write(chunk, ordered=False)
                d_count += res.upserted_count + res.matched_count
            except BulkWriteError as exc:
                write_errors = [e for e in exc.details.get("writeErrors", []) if e.get("code") != 11000]
                if write_errors:
                    print(f"  [WARN] {len(write_errors)} delivery write errors")
                    err += len(write_errors)
            except Exception as exc:
                print(f"  [WARN] Delivery chunk write failed: {exc}")
                err += 1

    return m_count, d_count, err


def _print_summary(s: dict) -> None:
    print("\n" + "=" * 55)
    print("  CricketIQ Import Summary")
    print("=" * 55)
    print(f"  Files processed   : {s['total_files']}")
    print(f"  Matches imported  : {s['imported_matches']}")
    print(f"  Deliveries stored : {s['imported_deliveries']}")
    print(f"  Errors            : {s['errors']}")
    print(f"  Time elapsed      : {s['elapsed_seconds']}s")
    print("=" * 55)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import IPL JSON data into CricketIQ MongoDB.")
    parser.add_argument("--data-dir", default=config.DATA_DIR, help="Directory of IPL JSON files")
    parser.add_argument("--batch-size", type=int, default=config.BATCH_SIZE, help="Bulk insert batch size")
    parser.add_argument("--download", action="store_true", help="Download official Cricsheet dataset to data-dir first")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of match files to import (e.g. 50)")
    args = parser.parse_args()

    if args.download:
        download_cricsheet_data(args.data_dir)

    try:
        import_all(args.data_dir, args.batch_size, args.limit)
    finally:
        close_client()


if __name__ == "__main__":
    main()
