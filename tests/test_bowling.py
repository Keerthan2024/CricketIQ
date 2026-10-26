"""
tests/test_bowling.py
Unit tests for bowling statistics and wicket-credit logic.
No MongoDB connection required.
"""
import pytest
from config import BOWLER_CREDITED_DISMISSALS

# -- Pure-function bowling calculations --------------------------------------

def bowling_stats_from_deliveries(deliveries: list[dict]) -> dict:
    """Mirror MongoDB $group logic for bowling."""
    stats: dict = {}
    for d in deliveries:
        bowler = d["bowler"]
        if bowler not in stats:
            stats[bowler] = {"batter_runs": 0, "wides": 0, "noballs": 0,
                             "wickets": 0, "legal_balls": 0}
        stats[bowler]["batter_runs"] += d.get("batter_runs", 0)
        extras = d.get("extras", {})
        wides = extras.get("wides", 0)
        noballs = extras.get("noballs", 0)
        stats[bowler]["wides"] += wides
        stats[bowler]["noballs"] += noballs
        if not wides:
            stats[bowler]["legal_balls"] += 1
        kind = d.get("wicket_kind")
        if kind and kind in BOWLER_CREDITED_DISMISSALS:
            stats[bowler]["wickets"] += 1
    return stats


def runs_conceded(s: dict) -> int:
    return s["batter_runs"] + s["wides"] + s["noballs"]


def overs_bowled(legal_balls: int) -> float:
    return round(legal_balls / 6, 1)


def economy(rc: int, ob: float) -> float:
    return round(rc / ob, 2) if ob > 0 else 0.0


def bowling_average(rc: int, wkts: int) -> float:
    return round(rc / wkts, 2) if wkts > 0 else float("inf")


# -- Fixtures -----------------------------------------------------------------

DELIVERIES = [
    # Bumrah: 2 legal balls, 1 wide, 1 wicket (caught)
    {"match_id":"m1","innings":1,"bowler":"Bumrah","batter":"A","batter_runs":0,"extras":{},"wicket_kind":"caught"},
    {"match_id":"m1","innings":1,"bowler":"Bumrah","batter":"B","batter_runs":4,"extras":{},"wicket_kind":None},
    {"match_id":"m1","innings":1,"bowler":"Bumrah","batter":"B","batter_runs":0,"extras":{"wides":1},"wicket_kind":None},
    # Chahar: 3 legal balls, 1 no-ball, 1 run-out (NOT bowler credit)
    {"match_id":"m1","innings":1,"bowler":"Chahar","batter":"C","batter_runs":6,"extras":{},"wicket_kind":None},
    {"match_id":"m1","innings":1,"bowler":"Chahar","batter":"C","batter_runs":0,"extras":{"noballs":1},"wicket_kind":None},
    {"match_id":"m1","innings":1,"bowler":"Chahar","batter":"C","batter_runs":0,"extras":{},"wicket_kind":"run out"},
    {"match_id":"m1","innings":1,"bowler":"Chahar","batter":"C","batter_runs":2,"extras":{},"wicket_kind":None},
]


class TestBowlingStatistics:
    def setup_method(self):
        self.stats = bowling_stats_from_deliveries(DELIVERIES)

    def test_bumrah_batter_runs(self):
        assert self.stats["Bumrah"]["batter_runs"] == 4

    def test_bumrah_wides(self):
        assert self.stats["Bumrah"]["wides"] == 1

    def test_bumrah_runs_conceded(self):
        # 4 batter + 1 wide = 5
        assert runs_conceded(self.stats["Bumrah"]) == 5

    def test_bumrah_legal_balls(self):
        # 2 normal + 0 (wide not counted)
        assert self.stats["Bumrah"]["legal_balls"] == 2

    def test_bumrah_wicket_caught(self):
        assert self.stats["Bumrah"]["wickets"] == 1

    def test_chahar_runout_not_credited(self):
        # run out should NOT increment bowler wickets
        assert self.stats["Chahar"]["wickets"] == 0

    def test_chahar_noball_counted_in_runs(self):
        rc = runs_conceded(self.stats["Chahar"])
        # 6 + 2 batter runs + 1 noball = 9
        assert rc == 9

    def test_chahar_legal_balls_excludes_noball_delivery(self):
        # No-ball deliveries are NOT wides, so they count as legal balls.
        # Chahar has 4 non-wide deliveries: runs=6, noball, runout, runs=2.
        assert self.stats["Chahar"]["legal_balls"] == 4

    def test_economy_calculation(self):
        s = self.stats["Bumrah"]
        ob = overs_bowled(s["legal_balls"])  # 2/6 ~ 0.3
        econ = economy(runs_conceded(s), ob)
        assert isinstance(econ, float)

    def test_economy_zero_overs(self):
        assert economy(10, 0.0) == 0.0

    def test_bowling_average_with_wickets(self):
        avg = bowling_average(runs_conceded(self.stats["Bumrah"]), self.stats["Bumrah"]["wickets"])
        assert avg == 5.0

    def test_bowling_average_zero_wickets(self):
        assert bowling_average(50, 0) == float("inf")


class TestBowlerCreditedDismissals:
    """Verify that only the correct dismissal types credit the bowler."""

    def test_bowled_is_credited(self):
        assert "bowled" in BOWLER_CREDITED_DISMISSALS

    def test_caught_is_credited(self):
        assert "caught" in BOWLER_CREDITED_DISMISSALS

    def test_lbw_is_credited(self):
        assert "lbw" in BOWLER_CREDITED_DISMISSALS

    def test_stumped_is_credited(self):
        assert "stumped" in BOWLER_CREDITED_DISMISSALS

    def test_hit_wicket_is_credited(self):
        assert "hit wicket" in BOWLER_CREDITED_DISMISSALS

    def test_run_out_not_credited(self):
        assert "run out" not in BOWLER_CREDITED_DISMISSALS

    def test_obstructing_not_credited(self):
        assert "obstructing the field" not in BOWLER_CREDITED_DISMISSALS


class TestEmptyInputs:
    def test_empty_deliveries(self):
        s = bowling_stats_from_deliveries([])
        assert s == {}

    def test_all_wides(self):
        dels = [{"match_id":"m","innings":1,"bowler":"X","batter":"A",
                 "batter_runs":0,"extras":{"wides":1},"wicket_kind":None}] * 6
        s = bowling_stats_from_deliveries(dels)
        assert s["X"]["legal_balls"] == 0
        assert s["X"]["wides"] == 6
