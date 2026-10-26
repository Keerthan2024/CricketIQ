"""
config.py - Centralised configuration loaded from environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB
MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DATABASE_NAME: str = os.getenv("DATABASE_NAME", "CricketIQ")

# Importer
DATA_DIR: str = os.getenv("DATA_DIR", "./data")
BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "500"))

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
