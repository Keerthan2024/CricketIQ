"""
analytics/team_mapping.py - Centralized IPL team and franchise normalization module.

Maps historical franchise names to official canonical names while ensuring distinct
franchises (e.g., Deccan Chargers vs Sunrisers Hyderabad, Pune Warriors vs Rising Pune Supergiant,
Gujarat Lions vs Gujarat Titans) remain separate.
"""
from __future__ import annotations

# Historical franchise renamings to canonical franchise names
FRANCHISE_MAPPINGS: dict[str, str] = {
    # Royal Challengers Bangalore rebranded to Royal Challengers Bengaluru in 2024
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Royal Challengers Bengaluru": "Royal Challengers Bengaluru",

    # Kings XI Punjab rebranded to Punjab Kings in 2021
    "Kings XI Punjab": "Punjab Kings",
    "Punjab Kings": "Punjab Kings",

    # Delhi Daredevils rebranded to Delhi Capitals in December 2018
    "Delhi Daredevils": "Delhi Capitals",
    "Delhi Capitals": "Delhi Capitals",

    # Rising Pune Supergiants dropped the plural 's' in 2017
    "Rising Pune Supergiants": "Rising Pune Supergiant",
    "Rising Pune Supergiant": "Rising Pune Supergiant",
}


def normalize_team_name(name: str | None) -> str | None:
    """
    Return the canonical franchise name for a given team name.
    If the name is not in the mapping or is None/empty, it returns the input as-is.
    """
    if not name:
        return name
    return FRANCHISE_MAPPINGS.get(name.strip(), name.strip())


def normalize_team_list(teams: list[str] | None) -> list[str]:
    """Normalize a list of team names to unique canonical team names."""
    if not teams:
        return []
    seen = set()
    result = []
    for t in teams:
        norm = normalize_team_name(t)
        if norm and norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


def get_historical_names(canonical_name: str) -> list[str]:
    """
    Return all historical and current names that correspond to the given canonical franchise.
    """
    norm = normalize_team_name(canonical_name)
    names = [raw for raw, target in FRANCHISE_MAPPINGS.items() if target == norm]
    if norm and norm not in names:
        names.append(norm)
    return sorted(list(set(names)))


def is_same_franchise(team_a: str | None, team_b: str | None) -> bool:
    """
    Return True if team_a and team_b represent the same franchise.
    """
    if not team_a or not team_b:
        return False
    return normalize_team_name(team_a) == normalize_team_name(team_b)


def get_canonical_team_expr(field_path: str = "$teams") -> dict:
    """
    Generate a MongoDB aggregation $switch expression that maps raw team fields
    to their canonical franchise name directly inside database aggregation pipelines.

    Usage in pipelines:
        {"$addFields": {"canonical_team": get_canonical_team_expr("$teams")}}
    """
    branches = [
        {"case": {"$eq": [field_path, raw]}, "then": canonical}
        for raw, canonical in FRANCHISE_MAPPINGS.items()
        if raw != canonical
    ]
    return {
        "$switch": {
            "branches": branches,
            "default": field_path,
        }
    }


def format_season(season_str: str | None) -> str:
    """
    Format Cricsheet split-season notation (e.g. '2007/08', '2009/10', '2020/21')
    to clean 4-digit IPL calendar years ('2008', '2010', '2020') to prevent Plotly axis breaks.
    """
    if not season_str:
        return ""
    s = str(season_str).strip()
    if s == "2007/08":
        return "2008"
    if s == "2009/10":
        return "2010"
    if s == "2020/21":
        return "2020"
    if "/" in s:
        parts = s.split("/")
        if len(parts) == 2 and len(parts[0]) == 4 and len(parts[1]) == 2:
            return parts[0][:2] + parts[1]
    return s


def season_sort_key(season_str: str | None) -> int:
    """Return integer year for chronological sorting."""
    clean = format_season(season_str)
    try:
        return int(clean)
    except (ValueError, TypeError):
        return 9999

