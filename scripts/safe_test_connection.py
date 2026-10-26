"""
scripts/safe_test_connection.py
Safe diagnostic: verifies connection and prints only SUCCESS or FAILURE.
Never logs or prints user credentials.
"""
import sys
from pathlib import Path
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_client, get_db, close_client
import config

try:
    print("Testing connection to MongoDB...")
    client = get_client()
    db = get_db()
    collections = db.list_collection_names()
    print("STATUS: SUCCESS")
    print(f"Database: {config.DATABASE_NAME}")
    print(f"Collections found: {collections}")
    if config.COLLECTION_MATCHES in collections:
        match_count = db[config.COLLECTION_MATCHES].count_documents({})
        delivery_count = db[config.COLLECTION_DELIVERIES].count_documents({})
        print(f"Matches count: {match_count}")
        print(f"Deliveries count: {delivery_count}")
    else:
        print("Database is currently clean and ready for setup.")
    close_client()
    sys.exit(0)
except Exception as e:
    print("STATUS: FAILED")
    print(f"Error category: {type(e).__name__}")
    sys.exit(1)
