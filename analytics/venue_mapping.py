"""
analytics/venue_mapping.py
Centralized venue normalization and canonical mapping for CricketIQ.

Normalizes historical, sponsored, and city-suffixed stadium names to their
canonical identities (e.g. 'Eden Gardens, Kolkata' -> 'Eden Gardens',
'Feroz Shah Kotla' -> 'Arun Jaitley Stadium', 'Sardar Patel Stadium, Motera' -> 'Narendra Modi Stadium, Ahmedabad').
"""
from __future__ import annotations

# Canonical mapping of historical and variant venue names to canonical venue names
VENUE_MAPPINGS: dict[str, str] = {
    # Eden Gardens, Kolkata
    "Eden Gardens": "Eden Gardens",
    "Eden Gardens, Kolkata": "Eden Gardens",

    # Wankhede Stadium, Mumbai
    "Wankhede Stadium": "Wankhede Stadium",
    "Wankhede Stadium, Mumbai": "Wankhede Stadium",

    # M Chinnaswamy Stadium, Bengaluru
    "M Chinnaswamy Stadium": "M Chinnaswamy Stadium",
    "M.Chinnaswamy Stadium": "M Chinnaswamy Stadium",
    "M Chinnaswamy Stadium, Bengaluru": "M Chinnaswamy Stadium",

    # Arun Jaitley Stadium, Delhi (renamed from Feroz Shah Kotla in 2019)
    "Feroz Shah Kotla": "Arun Jaitley Stadium",
    "Arun Jaitley Stadium": "Arun Jaitley Stadium",
    "Arun Jaitley Stadium, Delhi": "Arun Jaitley Stadium",

    # Rajiv Gandhi International Stadium, Hyderabad
    "Rajiv Gandhi International Stadium": "Rajiv Gandhi International Stadium",
    "Rajiv Gandhi International Stadium, Uppal": "Rajiv Gandhi International Stadium",
    "Rajiv Gandhi International Stadium, Uppal, Hyderabad": "Rajiv Gandhi International Stadium",

    # MA Chidambaram Stadium, Chepauk, Chennai
    "MA Chidambaram Stadium": "MA Chidambaram Stadium, Chepauk",
    "MA Chidambaram Stadium, Chepauk": "MA Chidambaram Stadium, Chepauk",
    "MA Chidambaram Stadium, Chepauk, Chennai": "MA Chidambaram Stadium, Chepauk",

    # Sawai Mansingh Stadium, Jaipur
    "Sawai Mansingh Stadium": "Sawai Mansingh Stadium",
    "Sawai Mansingh Stadium, Jaipur": "Sawai Mansingh Stadium",

    # Punjab Cricket Association Stadium, Mohali (IS Bindra)
    "Punjab Cricket Association Stadium, Mohali": "IS Bindra Stadium, Mohali",
    "Punjab Cricket Association IS Bindra Stadium": "IS Bindra Stadium, Mohali",
    "Punjab Cricket Association IS Bindra Stadium, Mohali": "IS Bindra Stadium, Mohali",
    "Punjab Cricket Association IS Bindra Stadium, Mohali, Chandigarh": "IS Bindra Stadium, Mohali",

    # Narendra Modi Stadium, Ahmedabad (formerly Sardar Patel Stadium, Motera)
    "Narendra Modi Stadium, Ahmedabad": "Narendra Modi Stadium, Ahmedabad",
    "Sardar Patel Stadium, Motera": "Narendra Modi Stadium, Ahmedabad",

    # Maharashtra Cricket Association Stadium, Pune (formerly Subrata Roy Sahara Stadium)
    "Maharashtra Cricket Association Stadium": "Maharashtra Cricket Association Stadium",
    "Maharashtra Cricket Association Stadium, Pune": "Maharashtra Cricket Association Stadium",
    "Subrata Roy Sahara Stadium": "Maharashtra Cricket Association Stadium",

    # Dr DY Patil Sports Academy, Navi Mumbai
    "Dr DY Patil Sports Academy": "Dr DY Patil Sports Academy",
    "Dr DY Patil Sports Academy, Mumbai": "Dr DY Patil Sports Academy",

    # Brabourne Stadium, Mumbai
    "Brabourne Stadium": "Brabourne Stadium",
    "Brabourne Stadium, Mumbai": "Brabourne Stadium",

    # UAE Venues
    "Dubai International Cricket Stadium": "Dubai International Cricket Stadium",
    "Sheikh Zayed Stadium": "Sheikh Zayed Stadium",
    "Zayed Cricket Stadium, Abu Dhabi": "Sheikh Zayed Stadium",
    "Sharjah Cricket Stadium": "Sharjah Cricket Stadium",

    # Lucknow
    "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow": "BRSABV Ekana Cricket Stadium, Lucknow",
    "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium": "BRSABV Ekana Cricket Stadium, Lucknow",
    "Ekana Cricket Stadium": "BRSABV Ekana Cricket Stadium, Lucknow",

    # Dharamsala
    "Himachal Pradesh Cricket Association Stadium": "HPCA Stadium, Dharamsala",
    "Himachal Pradesh Cricket Association Stadium, Dharamsala": "HPCA Stadium, Dharamsala",

    # Visakhapatnam
    "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium": "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium",
    "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium, Visakhapatnam": "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium",

    # Mullanpur / New Chandigarh
    "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur": "Maharaja Yadavindra Singh Stadium, Mullanpur",
    "Maharaja Yadavindra Singh International Cricket Stadium, New Chandigarh": "Maharaja Yadavindra Singh Stadium, Mullanpur",

    # Raipur
    "Shaheed Veer Narayan Singh International Stadium": "Shaheed Veer Narayan Singh Stadium, Raipur",
    "Shaheed Veer Narayan Singh International Stadium, Raipur": "Shaheed Veer Narayan Singh Stadium, Raipur",

    # Other Indian Venues
    "Saurashtra Cricket Association Stadium": "Saurashtra Cricket Association Stadium, Rajkot",
    "Barsapara Cricket Stadium, Guwahati": "Barsapara Cricket Stadium, Guwahati",
    "Holkar Cricket Stadium": "Holkar Cricket Stadium, Indore",
    "Barabati Stadium": "Barabati Stadium, Cuttack",
    "JSCA International Stadium Complex": "JSCA International Stadium Complex, Ranchi",
    "Vidarbha Cricket Association Stadium, Jamtha": "Vidarbha Cricket Association Stadium, Jamtha",
    "Green Park": "Green Park, Kanpur",
    "Nehru Stadium": "Nehru Stadium, Kochi",

    # South Africa (2009 IPL)
    "Kingsmead": "Kingsmead, Durban",
    "SuperSport Park": "SuperSport Park, Centurion",
    "New Wanderers Stadium": "Wanderers Stadium, Johannesburg",
    "Newlands": "Newlands, Cape Town",
    "St George's Park": "St George's Park, Gqeberha",
    "Buffalo Park": "Buffalo Park, East London",
    "De Beers Diamond Oval": "De Beers Diamond Oval, Kimberley",
    "OUTsurance Oval": "OUTsurance Oval, Bloemfontein",
}


def normalize_venue_name(venue: str | None) -> str | None:
    """
    Return the canonical venue name for a given raw or variant venue string.
    Returns None if input is None, or stripped string if no mapping exists.
    """
    if venue is None:
        return None
    cleaned = venue.strip()
    if not cleaned:
        return ""
    return VENUE_MAPPINGS.get(cleaned, cleaned)


def get_canonical_venue_expr(field_path: str = "$venue") -> dict:
    """
    Generate a MongoDB aggregation $switch expression that maps raw venue fields
    to their canonical name directly inside database aggregation pipelines.

    Usage in pipelines:
        {"$addFields": {"canonical_venue": get_canonical_venue_expr("$venue")}}
    """
    branches = [
        {"case": {"$eq": [field_path, raw]}, "then": canonical}
        for raw, canonical in VENUE_MAPPINGS.items()
        if raw != canonical
    ]
    return {
        "$switch": {
            "branches": branches,
            "default": field_path,
        }
    }
