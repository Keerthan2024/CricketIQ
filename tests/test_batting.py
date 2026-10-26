"""
tests/test_batting.py
Unit tests for batting statistics calculated from delivery fixtures.
No MongoDB connection required.
"""
import pytest

# -- Pure-function batting calculations --------------------------------------
# These mirror the aggregation logic so we can test offline.

def batting_stats_from_deliveries(deliveries: list[dict]) -> dict:
    """
    Compute per-batter totals from a list of delivery dicts.
    Mirrors the MongoDB $group logic in analytics/batting.py.
    """
    stats: dict = {}
    for d in deliveries:
        b = d["batter"]
        if b not in stats:
            stats[b] = {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "innings": set()}
        stats[b]["runs"] += d.get("batter_runs", 0)
        if not d.get("extras", {}).get("wides"):
            stats[b]["balls"] += 1
        if d.get("batter_runs") == 4:
            stats[b]["fours"] += 1
        if d.get("batter_runs") == 6:
            stats[b]["sixes"] += 1
        stats[b]["innings"].add((d.get("match_id", "m1"), d.get("innings", 1)))
    return stats


def strike_rate(runs: int, balls: int) -> float:
    return round((runs / balls) * 100, 2) if balls > 0 else 0.0


def batting_average(runs: int, innings: int) -> float:
    return round(runs / innings, 2) if innings > 0 else 0.0


# -- Fixtures -----------------------------------------------------------------

DELIVERIES = [
    # Rohit -- innings 1
    {"match_id":"m1","innings":1,"batter":"Rohit","bowler":"B1","batter_runs":4,"extras":{}},
    {"match_id":"m1","innings":1,"batter":"Rohit","bowler":"B1","batter_runs":6,"extras":{}},
    {"match_id":"m1","innings":1,"batter":"Rohit","bowler":"B1","batter_runs":1,"extras":{}},
    {"match_id":"m1","innings":1,"batter":"Rohit","bowler":"B1","batter_runs":0,"extras":{}},
    # Wide -- should not add to balls faced
    {"match_id":"m1","innings":1,"batter":"Rohit","bowler":"B1","batter_runs":0,"extras":{"wides":1}},
    # Virat -- innings 2 same match
    {"match_id":"m1","innings":2,"batter":"Virat","bowler":"B2","batter_runs":6,"extras":{}},
    {"match_id":"m1","innings":2,"batter":"Virat","bowler":"B2","batter_runs":6,"extras":{}},
    {"match_id":"m1","innings":2,"batter":"Virat","bowler":"B2","batter_runs":3,"extras":{}},
]


class TestBattingStatistics:
    def setup_method(self):
        self.stats = batting_stats_from_deliveries(DELIVERIES)

    def test_rohit_total_runs(self):
        assert self.stats["Rohit"]["runs"] == 11

    def test_rohit_balls_excludes_wides(self):
        # 4 normal balls, 1 wide -- only 4 count toward balls faced
        assert self.stats["Rohit"]["balls"] == 4

    def test_rohit_fours(self):
        assert self.stats["Rohit"]["fours"] == 1

    def test_rohit_sixes(self):
        assert self.stats["Rohit"]["sixes"] == 1

    def test_rohit_one_innings(self):
        assert len(self.stats["Rohit"]["innings"]) == 1

    def test_virat_total_runs(self):
        assert self.stats["Virat"]["runs"] == 15

    def test_virat_sixes(self):
        assert self.stats["Virat"]["sixes"] == 2

    def test_strike_rate_calculation(self):
        sr = strike_rate(self.stats["Rohit"]["runs"], self.stats["Rohit"]["balls"])
        assert sr == 275.0  # 11/4 * 100

    def test_strike_rate_zero_balls(self):
        assert strike_rate(10, 0) == 0.0

    def test_batting_average(self):
        avg = batting_average(self.stats["Rohit"]["runs"], len(self.stats["Rohit"]["innings"]))
        assert avg == 11.0

    def test_batting_average_zero_innings(self):
        assert batting_average(100, 0) == 0.0

    def test_empty_deliveries(self):
        s = batting_stats_from_deliveries([])
        assert s == {}

    def test_only_extras_no_runs(self):
        dels = [{"match_id":"m2","innings":1,"batter":"X","bowler":"B","batter_runs":0,
                 "extras":{"byes":4}}]
        s = batting_stats_from_deliveries(dels)
        assert s["X"]["runs"] == 0


class TestBoundaryStats:
    def test_boundary_count(self):
        stats = batting_stats_from_deliveries(DELIVERIES)
        rohit_boundaries = stats["Rohit"]["fours"] + stats["Rohit"]["sixes"]
        assert rohit_boundaries == 2

    def test_six_correctly_identified(self):
        dels = [{"match_id":"m","innings":1,"batter":"A","bowler":"B","batter_runs":6,"extras":{}}]
        s = batting_stats_from_deliveries(dels)
        assert s["A"]["sixes"] == 1
        assert s["A"]["fours"] == 0
