"""
tests/test_parser.py
Unit tests for importer/parser.py.
Uses small in-memory fixtures -- no MongoDB connection required.
"""
import pytest
from importer.parser import (
    parse_match,
    parse_deliveries,
    _build_result_detail,
    _derive_match_id,
    _other_team,
    load_json_file,
)
from pathlib import Path
import json
import tempfile
import os

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

SAMPLE_MATCH = {
    "meta": {"data_version": "1.3.0", "created": "2023-01-01", "revision": 1},
    "info": {
        "balls_per_over": 6,
        "dates": ["2023-04-15"],
        "teams": ["Mumbai Indians", "Chennai Super Kings"],
        "venue": "Wankhede Stadium",
        "city": "Mumbai",
        "toss": {"winner": "Mumbai Indians", "decision": "bat"},
        "outcome": {"winner": "Chennai Super Kings", "by": {"runs": 15}},
        "player_of_match": ["MS Dhoni"],
        "match_type": "T20",
        "season": "2023",
        "event": {"name": "Indian Premier League", "match_number": 1},
    },
    "innings": [
        {
            "team": "Mumbai Indians",
            "overs": [
                {
                    "over": 0,
                    "deliveries": [
                        {
                            "batter": "Rohit Sharma",
                            "non_striker": "Ishan Kishan",
                            "bowler": "Deepak Chahar",
                            "runs": {"batter": 4, "extras": 0, "total": 4},
                        },
                        {
                            "batter": "Rohit Sharma",
                            "non_striker": "Ishan Kishan",
                            "bowler": "Deepak Chahar",
                            "runs": {"batter": 0, "extras": 1, "total": 1},
                            "extras": {"wides": 1},
                        },
                        {
                            "batter": "Rohit Sharma",
                            "non_striker": "Ishan Kishan",
                            "bowler": "Deepak Chahar",
                            "runs": {"batter": 0, "extras": 0, "total": 0},
                            "wickets": [
                                {"kind": "bowled", "player_out": "Rohit Sharma", "fielders": []}
                            ],
                        },
                    ],
                }
            ],
        },
        {
            "team": "Chennai Super Kings",
            "overs": [
                {
                    "over": 0,
                    "deliveries": [
                        {
                            "batter": "Ruturaj Gaikwad",
                            "non_striker": "Devon Conway",
                            "bowler": "Jasprit Bumrah",
                            "runs": {"batter": 6, "extras": 0, "total": 6},
                        }
                    ],
                }
            ],
        },
    ],
}


# ---------------------------------------------------------------------------
# parse_match tests
# ---------------------------------------------------------------------------

class TestParseMatch:
    def test_returns_dict_for_valid_input(self):
        doc = parse_match(SAMPLE_MATCH, source_file="test_335982.json")
        assert doc is not None
        assert isinstance(doc, dict)

    def test_match_id_uses_numeric_stem(self):
        doc = parse_match(SAMPLE_MATCH, source_file="335982.json")
        assert doc["match_id"] == "335982"

    def test_match_id_hashes_non_numeric_stem(self):
        doc = parse_match(SAMPLE_MATCH, source_file="some_match.json")
        assert len(doc["match_id"]) == 16  # SHA-1 hex[:16]

    def test_teams_preserved(self):
        doc = parse_match(SAMPLE_MATCH)
        assert doc["teams"] == ["Mumbai Indians", "Chennai Super Kings"]

    def test_winner_extracted(self):
        doc = parse_match(SAMPLE_MATCH)
        assert doc["winner"] == "Chennai Super Kings"

    def test_season_extracted(self):
        doc = parse_match(SAMPLE_MATCH)
        assert doc["season"] == "2023"

    def test_season_falls_back_to_year(self):
        raw = {k: v for k, v in SAMPLE_MATCH.items()}
        info = {k: v for k, v in SAMPLE_MATCH["info"].items()}
        info.pop("season", None)
        raw["info"] = info
        doc = parse_match(raw)
        assert doc["season"] == "2023"  # from date 2023-04-15

    def test_player_of_match(self):
        doc = parse_match(SAMPLE_MATCH)
        assert "MS Dhoni" in doc["player_of_match"]

    def test_toss_info(self):
        doc = parse_match(SAMPLE_MATCH)
        assert doc["toss_winner"] == "Mumbai Indians"
        assert doc["toss_decision"] == "bat"

    def test_venue(self):
        doc = parse_match(SAMPLE_MATCH)
        assert doc["venue"] == "Wankhede Stadium"

    def test_returns_none_without_dates(self):
        raw = json.loads(json.dumps(SAMPLE_MATCH))
        raw["info"]["dates"] = []
        assert parse_match(raw) is None

    def test_returns_none_without_teams(self):
        raw = json.loads(json.dumps(SAMPLE_MATCH))
        raw["info"]["teams"] = []
        assert parse_match(raw) is None

    def test_returns_none_without_info(self):
        assert parse_match({}) is None

    def test_missing_optional_city(self):
        raw = json.loads(json.dumps(SAMPLE_MATCH))
        raw["info"].pop("city", None)
        doc = parse_match(raw)
        assert doc is not None
        assert doc.get("city") is None

    def test_missing_player_of_match(self):
        raw = json.loads(json.dumps(SAMPLE_MATCH))
        raw["info"].pop("player_of_match", None)
        doc = parse_match(raw)
        assert doc["player_of_match"] == []


# ---------------------------------------------------------------------------
# parse_deliveries tests
# ---------------------------------------------------------------------------

class TestParseDeliveries:
    def test_returns_list(self):
        doc = parse_match(SAMPLE_MATCH, "12345.json")
        dels = parse_deliveries(SAMPLE_MATCH, doc["match_id"], doc["season"])
        assert isinstance(dels, list)

    def test_delivery_count(self):
        doc = parse_match(SAMPLE_MATCH, "12345.json")
        dels = parse_deliveries(SAMPLE_MATCH, doc["match_id"], doc["season"])
        assert len(dels) == 4  # 3 in innings 1 + 1 in innings 2

    def test_innings_numbering(self):
        doc = parse_match(SAMPLE_MATCH, "12345.json")
        dels = parse_deliveries(SAMPLE_MATCH, doc["match_id"], doc["season"])
        innings_nums = {d["innings"] for d in dels}
        assert innings_nums == {1, 2}

    def test_batting_team_correct(self):
        doc = parse_match(SAMPLE_MATCH, "12345.json")
        dels = parse_deliveries(SAMPLE_MATCH, doc["match_id"], doc["season"])
        inn1 = [d for d in dels if d["innings"] == 1]
        assert all(d["batting_team"] == "Mumbai Indians" for d in inn1)

    def test_bowling_team_correct(self):
        doc = parse_match(SAMPLE_MATCH, "12345.json")
        dels = parse_deliveries(SAMPLE_MATCH, doc["match_id"], doc["season"])
        inn1 = [d for d in dels if d["innings"] == 1]
        assert all(d["bowling_team"] == "Chennai Super Kings" for d in inn1)

    def test_batter_runs_parsed(self):
        doc = parse_match(SAMPLE_MATCH, "12345.json")
        dels = parse_deliveries(SAMPLE_MATCH, doc["match_id"], doc["season"])
        first = [d for d in dels if d["innings"] == 1 and d["over"] == 0 and d["delivery"] == 1][0]
        assert first["batter_runs"] == 4

    def test_wide_extras_parsed(self):
        doc = parse_match(SAMPLE_MATCH, "12345.json")
        dels = parse_deliveries(SAMPLE_MATCH, doc["match_id"], doc["season"])
        wide_ball = [d for d in dels if d["innings"] == 1 and d["delivery"] == 2][0]
        assert wide_ball["extras"].get("wides") == 1

    def test_wicket_kind_parsed(self):
        doc = parse_match(SAMPLE_MATCH, "12345.json")
        dels = parse_deliveries(SAMPLE_MATCH, doc["match_id"], doc["season"])
        wkt_ball = [d for d in dels if d["wicket_kind"] is not None]
        assert len(wkt_ball) == 1
        assert wkt_ball[0]["wicket_kind"] == "bowled"
        assert wkt_ball[0]["dismissed_batter"] == "Rohit Sharma"

    def test_no_wicket_is_none(self):
        doc = parse_match(SAMPLE_MATCH, "12345.json")
        dels = parse_deliveries(SAMPLE_MATCH, doc["match_id"], doc["season"])
        no_wkt = [d for d in dels if d["innings"] == 2]
        assert all(d["wicket_kind"] is None for d in no_wkt)

    def test_season_propagated(self):
        doc = parse_match(SAMPLE_MATCH, "12345.json")
        dels = parse_deliveries(SAMPLE_MATCH, doc["match_id"], "2023")
        assert all(d["season"] == "2023" for d in dels)

    def test_empty_innings(self):
        raw = json.loads(json.dumps(SAMPLE_MATCH))
        raw["innings"] = []
        dels = parse_deliveries(raw, "test", "2023")
        assert dels == []


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_result_detail_runs(self):
        outcome = {"winner": "MI", "by": {"runs": 20}}
        assert _build_result_detail(outcome) == "MI won by 20 runs"

    def test_result_detail_wickets(self):
        outcome = {"winner": "CSK", "by": {"wickets": 5}}
        assert _build_result_detail(outcome) == "CSK won by 5 wickets"

    def test_result_detail_no_winner(self):
        assert _build_result_detail({}) == "no result"

    def test_result_detail_result_field(self):
        outcome = {"result": "tie"}
        assert _build_result_detail(outcome) == "tie"

    def test_other_team(self):
        assert _other_team(["MI", "CSK"], "MI") == "CSK"

    def test_other_team_same(self):
        # If both teams same (bad data), returns ""
        assert _other_team(["MI", "MI"], "MI") == ""

    def test_derive_match_id_numeric(self):
        mid = _derive_match_id({}, "335982.json")
        assert mid == "335982"

    def test_derive_match_id_hash(self):
        mid = _derive_match_id({"info": {"dates": ["2023-01-01"]}}, "abc.json")
        assert len(mid) == 16


# ---------------------------------------------------------------------------
# load_json_file tests
# ---------------------------------------------------------------------------

class TestLoadJsonFile:
    def test_valid_json(self, tmp_path):
        p = tmp_path / "valid.json"
        p.write_text('{"key": "value"}', encoding="utf-8")
        result = load_json_file(p)
        assert result == {"key": "value"}

    def test_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{invalid json", encoding="utf-8")
        result = load_json_file(p)
        assert result is None

    def test_missing_file(self, tmp_path):
        result = load_json_file(tmp_path / "nonexistent.json")
        assert result is None
