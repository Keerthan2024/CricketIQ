"""
tests/test_team_mapping.py
Comprehensive unit tests for franchise name normalization, mapping rules,
and analytical aggregation consistency across franchise renames.
No MongoDB connection required.
"""
import pytest
from analytics.team_mapping import (
    FRANCHISE_MAPPINGS,
    normalize_team_name,
    normalize_team_list,
    get_historical_names,
    is_same_franchise,
    get_canonical_team_expr,
)


class TestFranchiseNormalization:
    """Verify historical franchise renamings map to canonical names."""

    def test_rcb_bangalore_to_bengaluru(self):
        assert normalize_team_name("Royal Challengers Bangalore") == "Royal Challengers Bengaluru"

    def test_rcb_bengaluru_stays_bengaluru(self):
        assert normalize_team_name("Royal Challengers Bengaluru") == "Royal Challengers Bengaluru"

    def test_kxip_to_punjab_kings(self):
        assert normalize_team_name("Kings XI Punjab") == "Punjab Kings"

    def test_punjab_kings_stays_punjab_kings(self):
        assert normalize_team_name("Punjab Kings") == "Punjab Kings"

    def test_delhi_daredevils_to_delhi_capitals(self):
        assert normalize_team_name("Delhi Daredevils") == "Delhi Capitals"

    def test_delhi_capitals_stays_delhi_capitals(self):
        assert normalize_team_name("Delhi Capitals") == "Delhi Capitals"

    def test_rising_pune_supergiants_to_singular(self):
        assert normalize_team_name("Rising Pune Supergiants") == "Rising Pune Supergiant"

    def test_rising_pune_supergiant_stays_singular(self):
        assert normalize_team_name("Rising Pune Supergiant") == "Rising Pune Supergiant"

    def test_none_and_empty_handling(self):
        assert normalize_team_name(None) is None
        assert normalize_team_name("") == ""

    def test_whitespace_handling(self):
        assert normalize_team_name("  Kings XI Punjab  ") == "Punjab Kings"


class TestUnrelatedFranchisesSeparation:
    """Verify different franchises sharing cities/regions remain strictly separate."""

    def test_deccan_chargers_and_sunrisers_hyderabad_separate(self):
        assert normalize_team_name("Deccan Chargers") == "Deccan Chargers"
        assert normalize_team_name("Sunrisers Hyderabad") == "Sunrisers Hyderabad"
        assert not is_same_franchise("Deccan Chargers", "Sunrisers Hyderabad")

    def test_pune_warriors_and_rising_pune_supergiant_separate(self):
        assert normalize_team_name("Pune Warriors") == "Pune Warriors"
        assert not is_same_franchise("Pune Warriors", "Rising Pune Supergiant")

    def test_gujarat_lions_and_gujarat_titans_separate(self):
        assert normalize_team_name("Gujarat Lions") == "Gujarat Lions"
        assert normalize_team_name("Gujarat Titans") == "Gujarat Titans"
        assert not is_same_franchise("Gujarat Lions", "Gujarat Titans")

    def test_other_standard_teams_unchanged(self):
        standard = [
            "Mumbai Indians",
            "Chennai Super Kings",
            "Kolkata Knight Riders",
            "Rajasthan Royals",
            "Lucknow Super Giants",
            "Kochi Tuskers Kerala",
        ]
        for team in standard:
            assert normalize_team_name(team) == team


class TestHistoricalNamesResolution:
    """Verify retrieval of all historical aliases for a franchise."""

    def test_rcb_historical_names(self):
        names = get_historical_names("Royal Challengers Bengaluru")
        assert "Royal Challengers Bangalore" in names
        assert "Royal Challengers Bengaluru" in names
        assert len(names) == 2

    def test_punjab_historical_names(self):
        names = get_historical_names("Punjab Kings")
        assert "Kings XI Punjab" in names
        assert "Punjab Kings" in names
        assert len(names) == 2

    def test_delhi_historical_names(self):
        names = get_historical_names("Delhi Capitals")
        assert "Delhi Daredevils" in names
        assert "Delhi Capitals" in names
        assert len(names) == 2

    def test_srh_does_not_contain_deccan_chargers(self):
        names = get_historical_names("Sunrisers Hyderabad")
        assert "Deccan Chargers" not in names
        assert names == ["Sunrisers Hyderabad"]

    def test_titans_does_not_contain_lions(self):
        names = get_historical_names("Gujarat Titans")
        assert "Gujarat Lions" not in names
        assert names == ["Gujarat Titans"]


class TestAggregationConsistency:
    """Verify match and delivery statistics correctly aggregate across franchise renamings."""

    SAMPLE_MATCHES = [
        # Match 1: Delhi Daredevils win in 2012
        {"match_id": "1", "season": "2012", "teams": ["Delhi Daredevils", "Kings XI Punjab"], "winner": "Delhi Daredevils"},
        # Match 2: Kings XI Punjab win in 2015
        {"match_id": "2", "season": "2015", "teams": ["Delhi Daredevils", "Kings XI Punjab"], "winner": "Kings XI Punjab"},
        # Match 3: Delhi Capitals win in 2021
        {"match_id": "3", "season": "2021", "teams": ["Delhi Capitals", "Punjab Kings"], "winner": "Delhi Capitals"},
        # Match 4: Punjab Kings win in 2023
        {"match_id": "4", "season": "2023", "teams": ["Delhi Capitals", "Punjab Kings"], "winner": "Punjab Kings"},
        # Match 5: RCB Bangalore win in 2016
        {"match_id": "5", "season": "2016", "teams": ["Royal Challengers Bangalore", "Delhi Daredevils"], "winner": "Royal Challengers Bangalore"},
        # Match 6: RCB Bengaluru win in 2024
        {"match_id": "6", "season": "2024", "teams": ["Royal Challengers Bengaluru", "Delhi Capitals"], "winner": "Royal Challengers Bengaluru"},
    ]

    def _aggregate_team_records(self, matches: list[dict]) -> dict:
        records: dict = {}
        for m in matches:
            canonical_winner = normalize_team_name(m.get("winner"))
            for team in m.get("teams", []):
                canon_team = normalize_team_name(team)
                if canon_team not in records:
                    records[canon_team] = {"matches": 0, "wins": 0}
                records[canon_team]["matches"] += 1
                if canonical_winner == canon_team:
                    records[canon_team]["wins"] += 1
        for team, r in records.items():
            r["losses"] = r["matches"] - r["wins"]
            r["win_pct"] = round((r["wins"] / r["matches"]) * 100, 1)
        return records

    def _aggregate_head_to_head(self, matches: list[dict], team_a: str, team_b: str) -> dict:
        canon_a = normalize_team_name(team_a)
        canon_b = normalize_team_name(team_b)
        names_a = set(get_historical_names(team_a))
        names_b = set(get_historical_names(team_b))

        relevant = [
            m for m in matches
            if any(t in names_a for t in m.get("teams", [])) and any(t in names_b for t in m.get("teams", []))
        ]
        a_wins = sum(1 for m in relevant if normalize_team_name(m.get("winner")) == canon_a)
        b_wins = sum(1 for m in relevant if normalize_team_name(m.get("winner")) == canon_b)
        return {"total": len(relevant), "team_a_wins": a_wins, "team_b_wins": b_wins}

    def test_delhi_capitals_aggregated_stats(self):
        records = self._aggregate_team_records(self.SAMPLE_MATCHES)
        # Delhi appears in all 6 matches (4 vs Punjab, 2 vs RCB)
        assert records["Delhi Capitals"]["matches"] == 6
        # Delhi won Match 1 and Match 3
        assert records["Delhi Capitals"]["wins"] == 2
        assert records["Delhi Capitals"]["losses"] == 4
        # Delhi Daredevils does NOT appear as a distinct key
        assert "Delhi Daredevils" not in records

    def test_punjab_kings_aggregated_stats(self):
        records = self._aggregate_team_records(self.SAMPLE_MATCHES)
        # Punjab appears in 4 matches
        assert records["Punjab Kings"]["matches"] == 4
        # Punjab won Match 2 and Match 4
        assert records["Punjab Kings"]["wins"] == 2
        assert records["Punjab Kings"]["losses"] == 2
        # Kings XI Punjab does NOT appear as a distinct key
        assert "Kings XI Punjab" not in records

    def test_rcb_aggregated_stats(self):
        records = self._aggregate_team_records(self.SAMPLE_MATCHES)
        # RCB played Match 5 and Match 6
        assert records["Royal Challengers Bengaluru"]["matches"] == 2
        assert records["Royal Challengers Bengaluru"]["wins"] == 2
        assert "Royal Challengers Bangalore" not in records

    def test_head_to_head_across_renames(self):
        # Delhi Capitals vs Punjab Kings across 2012-2023
        h2h = self._aggregate_head_to_head(self.SAMPLE_MATCHES, "Delhi Capitals", "Punjab Kings")
        assert h2h["total"] == 4
        assert h2h["team_a_wins"] == 2  # 1 as Daredevils, 1 as Capitals
        assert h2h["team_b_wins"] == 2  # 1 as KXIP, 1 as Punjab Kings

    def test_head_to_head_works_with_historical_name_inputs(self):
        # Querying with old names should resolve to the exact same head-to-head record
        h2h_old = self._aggregate_head_to_head(self.SAMPLE_MATCHES, "Delhi Daredevils", "Kings XI Punjab")
        h2h_new = self._aggregate_head_to_head(self.SAMPLE_MATCHES, "Delhi Capitals", "Punjab Kings")
        assert h2h_old == h2h_new

    def test_team_runs_aggregation(self):
        deliveries = [
            {"batting_team": "Delhi Daredevils", "runs": 150},
            {"batting_team": "Delhi Capitals", "runs": 180},
            {"batting_team": "Kings XI Punjab", "runs": 140},
            {"batting_team": "Punjab Kings", "runs": 170},
        ]
        totals = {}
        for d in deliveries:
            team = normalize_team_name(d["batting_team"])
            totals[team] = totals.get(team, 0) + d["runs"]

        assert totals["Delhi Capitals"] == 330
        assert totals["Punjab Kings"] == 310
        assert "Delhi Daredevils" not in totals
        assert "Kings XI Punjab" not in totals


class TestMongoExpressionBuilder:
    """Verify MongoDB $switch aggregation expression generates valid syntax."""

    def test_expression_structure(self):
        expr = get_canonical_team_expr("$teams")
        assert "$switch" in expr
        assert "branches" in expr["$switch"]
        assert expr["$switch"]["default"] == "$teams"
        assert len(expr["$switch"]["branches"]) >= 4

    def test_expression_handles_custom_field_path(self):
        expr = get_canonical_team_expr("$winner")
        assert expr["$switch"]["default"] == "$winner"
        case_0 = expr["$switch"]["branches"][0]["case"]
        assert "$eq" in case_0
        assert case_0["$eq"][0] == "$winner"
