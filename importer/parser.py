"""
importer/parser.py
Parse a single Cricsheet IPL JSON match file into match and delivery documents
suitable for insertion into MongoDB.

Cricsheet JSON v1.3.0 format (https://cricsheet.org/format/json/).
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any
from analytics.team_mapping import normalize_team_name, normalize_team_list
from analytics.venue_mapping import normalize_venue_name


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def load_json_file(path: Path) -> dict | None:
    """
    Load and parse a JSON file.  Returns None on any parse/IO error so
    callers can skip bad files gracefully.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  [SKIP] {path.name}: {exc}")
        return None


def parse_match(raw: dict, source_file: str = "") -> dict | None:
    """
    Convert a raw Cricsheet JSON document into a match record.
    Returns None if required fields are missing.
    """
    info = raw.get("info")
    if not info:
        return None

    dates = info.get("dates", [])
    if not dates:
        return None
    match_date = dates[0]  # Use first date as canonical

    teams = info.get("teams", [])
    if len(teams) < 2:
        return None

    # Derive a stable match_id from file name or content hash
    match_id = _derive_match_id(raw, source_file)

    # Toss
    toss = info.get("toss", {})

    # Outcome
    outcome = info.get("outcome", {})
    winner = outcome.get("winner", None)
    result_detail = _build_result_detail(outcome)

    # Season: Cricsheet IPL files usually carry event.season or season field
    season = (
        info.get("season")
        or info.get("event", {}).get("season")
        or match_date[:4]  # Fall back to year from date
    )
    if season:
        season = str(season)

    doc = {
        "match_id": match_id,
        "date": match_date,
        "season": season,
        "teams": teams,
        "canonical_teams": normalize_team_list(teams),
        "venue": info.get("venue", "Unknown"),
        "canonical_venue": normalize_venue_name(info.get("venue", "Unknown")),
        "city": info.get("city"),
        "toss_winner": toss.get("winner"),
        "canonical_toss_winner": normalize_team_name(toss.get("winner")),
        "toss_decision": toss.get("decision"),
        "winner": winner,
        "canonical_winner": normalize_team_name(winner),
        "result": result_detail,
        "player_of_match": info.get("player_of_match", []),
        "match_type": info.get("match_type", "T20"),
        "event_name": info.get("event", {}).get("name"),
        "source_file": source_file,
        "meta_data_version": raw.get("meta", {}).get("data_version"),
    }
    return doc


def parse_deliveries(raw: dict, match_id: str, season: str) -> list[dict]:
    """
    Flatten all deliveries from all innings into a list of delivery documents.
    Each document contains match context fields needed for efficient aggregation.
    """
    deliveries: list[dict] = []
    info = raw.get("info", {})
    teams = info.get("teams", [])

    innings_list = raw.get("innings", [])
    for innings_index, innings in enumerate(innings_list):
        innings_num = innings_index + 1  # 1-indexed

        # Determine batting/bowling teams
        batting_team = innings.get("team", "")
        bowling_team = _other_team(teams, batting_team)

        overs = innings.get("overs", [])
        for over_data in overs:
            over_num = int(over_data.get("over", 0))
            balls = over_data.get("deliveries", [])
            for ball_index, ball in enumerate(balls):
                doc = _parse_delivery(
                    ball, match_id, season,
                    innings_num, batting_team, bowling_team,
                    over_num, ball_index + 1,
                )
                deliveries.append(doc)

    return deliveries


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_delivery(
    ball: dict,
    match_id: str,
    season: str,
    innings: int,
    batting_team: str,
    bowling_team: str,
    over: int,
    delivery: int,
) -> dict:
    runs = ball.get("runs", {})
    batter_runs = runs.get("batter", 0)
    extras_runs = runs.get("extras", 0)
    total_runs = runs.get("total", batter_runs + extras_runs)

    extras = ball.get("extras", {})

    # Wicket information
    wickets = ball.get("wickets", [])
    wicket_kind = None
    dismissed_batter = None
    fielders = []
    if wickets:
        first = wickets[0]
        wicket_kind = first.get("kind")
        dismissed_batter = first.get("player_out")
        fielders = [f.get("name") for f in first.get("fielders", []) if f.get("name")]

    doc = {
        "match_id": match_id,
        "season": season,
        "innings": innings,
        "batting_team": batting_team,
        "canonical_batting_team": normalize_team_name(batting_team),
        "bowling_team": bowling_team,
        "canonical_bowling_team": normalize_team_name(bowling_team),
        "over": over,
        "delivery": delivery,
        "batter": ball.get("batter", ""),
        "non_striker": ball.get("non_striker"),
        "bowler": ball.get("bowler", ""),
        "batter_runs": batter_runs,
        "extras_runs": extras_runs,
        "total_runs": total_runs,
        "extras": extras,
        "wicket_kind": wicket_kind,
        "dismissed_batter": dismissed_batter,
        "fielders": fielders,
    }
    return doc


def _build_result_detail(outcome: dict) -> str:
    if not outcome:
        return "no result"
    if "winner" not in outcome:
        result_type = outcome.get("result", "no result")
        return result_type
    winner = outcome["winner"]
    by = outcome.get("by", {})
    if "runs" in by:
        return f"{winner} won by {by['runs']} runs"
    if "wickets" in by:
        return f"{winner} won by {by['wickets']} wickets"
    if "innings" in by and "runs" in by:
        return f"{winner} won by an innings and {by['runs']} runs"
    return f"{winner} won"


def _other_team(teams: list[str], batting_team: str) -> str:
    for t in teams:
        if t != batting_team:
            return t
    return ""


def _derive_match_id(raw: dict, source_file: str) -> str:
    """
    Prefer the Cricsheet file stem as match_id (e.g. '335982').
    Fall back to a SHA-1 hash of info content for files without a clear stem.
    """
    stem = Path(source_file).stem if source_file else ""
    if stem and stem.isdigit():
        return stem
    # Hash the info block for stability across re-imports
    info_bytes = json.dumps(raw.get("info", {}), sort_keys=True).encode()
    return hashlib.sha1(info_bytes).hexdigest()[:16]
