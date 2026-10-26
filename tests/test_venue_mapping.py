"""
tests/test_venue_mapping.py
Unit tests for venue normalization, historical renamings, and canonical mapping.
No MongoDB connection required.
"""
import pytest
from analytics.venue_mapping import (
    VENUE_MAPPINGS,
    normalize_venue_name,
    get_canonical_venue_expr,
)


class TestVenueNormalization:
    """Verify city suffixes and spelling variations normalize to canonical venue names."""

    def test_eden_gardens(self):
        assert normalize_venue_name("Eden Gardens") == "Eden Gardens"
        assert normalize_venue_name("Eden Gardens, Kolkata") == "Eden Gardens"

    def test_wankhede(self):
        assert normalize_venue_name("Wankhede Stadium") == "Wankhede Stadium"
        assert normalize_venue_name("Wankhede Stadium, Mumbai") == "Wankhede Stadium"

    def test_chinnaswamy(self):
        assert normalize_venue_name("M Chinnaswamy Stadium") == "M Chinnaswamy Stadium"
        assert normalize_venue_name("M.Chinnaswamy Stadium") == "M Chinnaswamy Stadium"
        assert normalize_venue_name("M Chinnaswamy Stadium, Bengaluru") == "M Chinnaswamy Stadium"

    def test_chepauk(self):
        assert normalize_venue_name("MA Chidambaram Stadium") == "MA Chidambaram Stadium, Chepauk"
        assert normalize_venue_name("MA Chidambaram Stadium, Chepauk") == "MA Chidambaram Stadium, Chepauk"
        assert normalize_venue_name("MA Chidambaram Stadium, Chepauk, Chennai") == "MA Chidambaram Stadium, Chepauk"

    def test_rajiv_gandhi(self):
        assert normalize_venue_name("Rajiv Gandhi International Stadium") == "Rajiv Gandhi International Stadium"
        assert normalize_venue_name("Rajiv Gandhi International Stadium, Uppal") == "Rajiv Gandhi International Stadium"
        assert normalize_venue_name("Rajiv Gandhi International Stadium, Uppal, Hyderabad") == "Rajiv Gandhi International Stadium"

    def test_sawai_mansingh(self):
        assert normalize_venue_name("Sawai Mansingh Stadium") == "Sawai Mansingh Stadium"
        assert normalize_venue_name("Sawai Mansingh Stadium, Jaipur") == "Sawai Mansingh Stadium"

    def test_dy_patil(self):
        assert normalize_venue_name("Dr DY Patil Sports Academy") == "Dr DY Patil Sports Academy"
        assert normalize_venue_name("Dr DY Patil Sports Academy, Mumbai") == "Dr DY Patil Sports Academy"

    def test_brabourne(self):
        assert normalize_venue_name("Brabourne Stadium") == "Brabourne Stadium"
        assert normalize_venue_name("Brabourne Stadium, Mumbai") == "Brabourne Stadium"


class TestHistoricalStadiumRenamings:
    """Verify historical stadium renamings map to canonical names."""

    def test_feroz_shah_kotla_to_arun_jaitley(self):
        assert normalize_venue_name("Feroz Shah Kotla") == "Arun Jaitley Stadium"
        assert normalize_venue_name("Arun Jaitley Stadium, Delhi") == "Arun Jaitley Stadium"
        assert normalize_venue_name("Arun Jaitley Stadium") == "Arun Jaitley Stadium"

    def test_motera_to_narendra_modi(self):
        assert normalize_venue_name("Sardar Patel Stadium, Motera") == "Narendra Modi Stadium, Ahmedabad"
        assert normalize_venue_name("Narendra Modi Stadium, Ahmedabad") == "Narendra Modi Stadium, Ahmedabad"

    def test_subrata_roy_to_mca(self):
        assert normalize_venue_name("Subrata Roy Sahara Stadium") == "Maharashtra Cricket Association Stadium"
        assert normalize_venue_name("Maharashtra Cricket Association Stadium, Pune") == "Maharashtra Cricket Association Stadium"
        assert normalize_venue_name("Maharashtra Cricket Association Stadium") == "Maharashtra Cricket Association Stadium"

    def test_pca_to_is_bindra(self):
        assert normalize_venue_name("Punjab Cricket Association Stadium, Mohali") == "IS Bindra Stadium, Mohali"
        assert normalize_venue_name("Punjab Cricket Association IS Bindra Stadium, Mohali") == "IS Bindra Stadium, Mohali"
        assert normalize_venue_name("Punjab Cricket Association IS Bindra Stadium") == "IS Bindra Stadium, Mohali"


class TestEdgeCases:
    """Verify null, empty, whitespace, and unknown venues."""

    def test_none_and_empty(self):
        assert normalize_venue_name(None) is None
        assert normalize_venue_name("") == ""

    def test_whitespace_trimming(self):
        assert normalize_venue_name("  Eden Gardens, Kolkata  ") == "Eden Gardens"

    def test_unknown_venue_passthrough(self):
        assert normalize_venue_name("Some New Stadium") == "Some New Stadium"

    def test_aggregation_switch_expr(self):
        expr = get_canonical_venue_expr("$venue")
        assert "$switch" in expr
        assert "branches" in expr["$switch"]
        assert len(expr["$switch"]["branches"]) > 0
