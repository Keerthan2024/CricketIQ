"""
config.py - Centralised configuration loaded from environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()

def _get_setting(key: str, default: str = "") -> str:
    # 1. Check Streamlit Secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets:
            if key in st.secrets:
                return str(st.secrets[key]).strip()
            for k in st.secrets:
                if k.lower() == key.lower():
                    return str(st.secrets[k]).strip()
            for sec in ["mongo", "mongodb", "database", "db"]:
                if sec in st.secrets:
                    section = st.secrets[sec]
                    if key in section:
                        return str(section[key]).strip()
                    for k in section:
                        if k.lower() == key.lower():
                            return str(section[k]).strip()
    except Exception:
        pass
    # 2. Check environment variables
    env_val = os.getenv(key) or os.getenv(key.lower()) or os.getenv(key.upper())
    if env_val:
        return env_val.strip()
    return default

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
