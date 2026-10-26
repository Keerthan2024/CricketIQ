"""
config.py - Centralised configuration loaded from environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()

def _get_setting(key: str, default: str = "") -> str:
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, default)

# MongoDB
MONGODB_URI: str = _get_setting("MONGODB_URI", "mongodb://localhost:27017/")
DATABASE_NAME: str = _get_setting("DATABASE_NAME", "CricketIQ")

# Importer
DATA_DIR: str = _get_setting("DATA_DIR", "./data")
BATCH_SIZE: int = int(_get_setting("BATCH_SIZE", "500"))

# Collections
COLLECTION_MATCHES: str = "matches"
COLLECTION_DELIVERIES: str = "deliveries"

# Bowler-credited dismissal types (not run out, not obstructing the field)
BOWLER_CREDITED_DISMISSALS = {
    "bowled",
    "caught",
    "caught and bowled",
    "lbw",
    "stumped",
    "hit wicket",
    "hit the ball twice",
}

# Extra types that count as runs conceded by the bowler
# Byes and leg-byes are NOT charged to the bowler in cricket scoring.
BOWLER_EXTRAS = {"wides", "noballs"}
