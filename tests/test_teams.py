"""
tests/test_teams.py
Unit tests for team statistics and head-to-head calculations.
No MongoDB connection required.
"""
import pytest


def compute_team_records(matches: list[dict]) -> dict:
    """Mirror MongoDB aggregation logic for team records."""
    records: dict = {}
    for m in matches:
        for team in m.get("teams", []):
            if team not in records:
                records[team] = {"matches": 0, "wins": 0}
            records[team]["matches"] += 1
            if m.get("winner") == team:
                records[team]["wins"] += 1
    for team, r in records.items():
        r["losses"] = r["matches"] - r["wins"]
        played = r["matches"]
        r["win_pct"] = round((r["wins"] / played) * 100, 1) if played > 0 else 0.0
    return records


def compute_head_to_head(matches: list[dict], t1: str, t2: str) -> dict:
    relevant = [m for m in matches if t1 in m.get("teams",[]) and t2 in m.get("teams",[])]
    t1w = sum(1 for m in relevant if m.get("winner") == t1)
    t2w = sum(1 for m in relevant if m.get("winner") == t2)
    nr  = sum(1 for m in relevant if m.get("winner") is None)
    return {"total": len(relevant), "t1_wins": t1w, "t2_wins": t2w, "no_result": nr}


# -- Fixtures -----------------------------------------------------------------

MATCHES = [
    {"match_id":"1","teams":["MI","CSK"],"winner":"MI","season":"2023"},
    {"match_id":"2","teams":["MI","CSK"],"winner":"CSK","season":"2023"},
    {"match_id":"3","teams":["MI","RCB"],"winner":"MI","season":"2023"},
    {"match_id":"4","teams":["CSK","RCB"],"winner":"RCB","season":"2023"},
    {"match_id":"5","teams":["MI","CSK"],"winner":None,"season":"2022"},  # no result
    {"match_id":"6","teams":["RCB","KKR"],"winner":"KKR","season":"2022"},
]


class TestTeamRecords:
    def setup_method(self):
        self.records = compute_team_records(MATCHES)

    def test_mi_matches_played(self):
        assert self.records["MI"]["matches"] == 4

    def test_mi_wins(self):
        assert self.records["MI"]["wins"] == 2

    def test_mi_losses(self):
        assert self.records["MI"]["losses"] == 2  # 1 CSK win + 1 no-result + 0 others

    def test_csk_matches(self):
        # CSK appears in: m1(MI vs CSK), m2(MI vs CSK), m4(CSK vs RCB), m5(MI vs CSK no-result) = 4
        assert self.records["CSK"]["matches"] == 4

    def test_csk_wins(self):
        assert self.records["CSK"]["wins"] == 1

    def test_win_pct_nonzero(self):
        assert self.records["MI"]["win_pct"] == 50.0

    def test_team_with_one_win_all_played(self):
        assert self.records["RCB"]["wins"] == 1
        assert self.records["RCB"]["matches"] == 3

    def test_no_result_counts_as_match(self):
        # Match 5 (MI vs CSK, no result) increments both MI and CSK match counts
        assert self.records["MI"]["matches"] == 4
        assert self.records["CSK"]["matches"] == 4

    def test_kkr_one_match(self):
        assert self.records["KKR"]["matches"] == 1
        assert self.records["KKR"]["wins"] == 1

    def test_empty_matches(self):
        r = compute_team_records([])
        assert r == {}

    def test_win_pct_zero_wins(self):
        r = compute_team_records([
            {"teams":["A","B"],"winner":"B"},
            {"teams":["A","B"],"winner":"B"},
        ])
        assert r["A"]["win_pct"] == 0.0

    def test_win_pct_100(self):
        r = compute_team_records([
            {"teams":["A","B"],"winner":"A"},
            {"teams":["A","C"],"winner":"A"},
        ])
        assert r["A"]["win_pct"] == 100.0


class TestHeadToHead:
    def setup_method(self):
        self.h2h = compute_head_to_head(MATCHES, "MI", "CSK")

    def test_total_matches(self):
        assert self.h2h["total"] == 3  # matches 1,2,5

    def test_mi_wins(self):
        assert self.h2h["t1_wins"] == 1

    def test_csk_wins(self):
        assert self.h2h["t2_wins"] == 1

    def test_no_result(self):
        assert self.h2h["no_result"] == 1

    def test_teams_never_played(self):
        h2h = compute_head_to_head(MATCHES, "MI", "KKR")
        assert h2h["total"] == 0
        assert h2h["t1_wins"] == 0

    def test_single_match(self):
        h2h = compute_head_to_head(MATCHES, "RCB", "KKR")
        assert h2h["total"] == 1
        assert h2h["t2_wins"] == 1
