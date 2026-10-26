"""
scripts/diagnose_connection.py
MongoDB connection diagnostic for CricketIQ.
Safe: never prints credentials or sensitive values.
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote
from dotenv import dotenv_values

ENV_PATH = Path(__file__).parent.parent / ".env"

print("=" * 50)
print("CricketIQ MongoDB Connection Diagnostic")
print("=" * 50)

# ── Step 1: Verify .env file ───────────────────────────────────────────────
print("\n[1] .env file check")
if not ENV_PATH.exists():
    print("  ERROR: .env file not found!")
    sys.exit(1)

raw_bytes = ENV_PATH.read_bytes()
print(f"  Size: {len(raw_bytes)} bytes")

if raw_bytes[:3] == b'\xef\xbb\xbf':
    print("  WARNING: UTF-8 BOM detected - can corrupt first variable!")
else:
    print("  Encoding: clean (no BOM)")

# ── Step 2: Load .env freshly (bypass any cached env) ────────────────────
vals = dotenv_values(ENV_PATH)
uri = vals.get("MONGODB_URI", "")

print("\n[2] MONGODB_URI from .env")
print(f"  Present: {'MONGODB_URI' in vals}")
print(f"  Length: {len(uri)} chars")

if not uri:
    print("  ERROR: MONGODB_URI is empty or missing!")
    sys.exit(1)

# ── Step 3: Check for system env override ─────────────────────────────────
sys_uri = os.environ.get("MONGODB_URI", "")
print("\n[3] System environment override")
if sys_uri and sys_uri != uri:
    print("  CRITICAL: MONGODB_URI is ALSO defined as a system environment variable!")
    print("  The system variable OVERRIDES .env and may have DIFFERENT credentials.")
    print("  Fix: Remove the MONGODB_URI system environment variable.")
elif sys_uri == uri:
    print("  OK: System env var matches .env")
else:
    print("  OK: No conflicting system env var")

# ── Step 4: Parse URI ──────────────────────────────────────────────────────
print("\n[4] URI parsing")
try:
    parsed = urlparse(uri)
    scheme = parsed.scheme
    username = parsed.username or ""
    password = parsed.password or ""
    host = parsed.hostname or str(parsed.netloc)
    path = parsed.path
    query = parsed.query

    print(f"  Scheme: {scheme}")
    print(f"  Username: {repr(username)}")
    print(f"  Password length: {len(password)} chars")
    print(f"  Host: {host[:40]}")
    print(f"  Path (database): {repr(path)}")
    print(f"  Query params: {repr(query)}")

    # Special chars check
    specials = [c for c in password if not c.isalnum()]
    if specials:
        print(f"  WARNING: Password contains special characters: {specials}")
        print("  These MUST be percent-encoded in a URI.")
        print("  e.g. '@' -> %40, '#' -> %23, '?' -> %3F, ':' -> %3A, '/' -> %2F, '&' -> %26")
        import urllib.parse
        encoded_pass = urllib.parse.quote(password, safe="")
        if encoded_pass != password:
            print(f"  The password needs encoding. Length after encoding: {len(encoded_pass)} chars")
    else:
        print("  Password: alphanumeric only - no URL encoding needed")

    if scheme not in ("mongodb", "mongodb+srv"):
        print(f"  ERROR: Unexpected URI scheme '{scheme}'")

    if "authSource" in query:
        print(f"  authSource is set in query params")
    else:
        print("  authSource: not set (defaults to admin for mongodb+srv)")

except Exception as e:
    print(f"  ERROR parsing URI: {e}")
    sys.exit(1)

# ── Step 5: Network check ─────────────────────────────────────────────────
print("\n[5] Network reachability")
import socket
import ssl

try:
    socket.gethostbyname("google.com")
    print("  Internet: OK")
except Exception:
    print("  Internet: FAILED (no internet connection)")

# Try to resolve the Atlas cluster
cluster_host = host if host and "mongodb.net" in host else "cricketiq.acu22hg.mongodb.net"
try:
    ip = socket.gethostbyname(cluster_host)
    print(f"  Atlas DNS ({cluster_host[:35]}): OK -> {ip}")
    atlas_ip = ip
except Exception as e:
    print(f"  Atlas DNS: FAILED - {e}")
    print("  Likely cause: Campus/office firewall blocking UDP port 53 for this domain.")
    atlas_ip = "159.41.183.67"  # known fallback IP

# Port 27017 connectivity
try:
    s = socket.socket()
    s.settimeout(4)
    res = s.connect_ex((atlas_ip, 27017))
    s.close()
    if res == 0:
        print(f"  Port 27017 ({atlas_ip}): OPEN")
    else:
        print(f"  Port 27017 ({atlas_ip}): BLOCKED (error {res})")
        print("  Likely cause: Campus firewall blocking outbound port 27017.")
        sys.exit(1)
except Exception as e:
    print(f"  Port 27017 check: ERROR - {e}")

# TLS handshake test with SNI
sni_host = "mtm-aws-aps1-7-m0-16-shard-00-00.bmkjo.mongodb.net"
try:
    ctx = ssl.create_default_context()
    s2 = socket.create_connection((atlas_ip, 27017), timeout=5)
    ss = ctx.wrap_socket(s2, server_hostname=sni_host)
    tls_ver = ss.version()
    ss.close()
    print(f"  TLS handshake (SNI: {sni_host[:30]}...): OK ({tls_ver})")
    tls_ok = True
except Exception as e:
    print(f"  TLS handshake: FAILED - {e}")
    print("  This is a network/firewall issue, not a credential issue.")
    tls_ok = False

# ── Step 6: Authentication test ────────────────────────────────────────────
print("\n[6] MongoDB authentication test")
if not tls_ok:
    print("  SKIPPED: TLS connection failed - fix network issue first.")
    print("\n" + "=" * 50)
    print("ROOT CAUSE: Campus/office network is blocking outbound")
    print("port 27017 connections to MongoDB Atlas.")
    print("SOLUTION: Use a mobile hotspot or VPN.")
    print("=" * 50)
    sys.exit(1)

try:
    from pymongo import MongoClient
    from pymongo.errors import OperationFailure, ServerSelectionTimeoutError

    # Build URI using the effective SNI hosts
    if scheme == "mongodb+srv" and "acu22hg.mongodb.net" in uri:
        bmkjo_uri = (
            f"mongodb://{username}:{password}@"
            "mtm-aws-aps1-7-m0-16-shard-00-00.bmkjo.mongodb.net:27017,"
            "mtm-aws-aps1-7-m0-16-shard-00-01.bmkjo.mongodb.net:27017,"
            "mtm-aws-aps1-7-m0-16-shard-00-02.bmkjo.mongodb.net:27017"
            f"{path}?ssl=true&authSource=admin"
        )
    else:
        bmkjo_uri = uri

    client = MongoClient(bmkjo_uri, serverSelectionTimeoutMS=8000,
                         retryWrites=True, readPreference="secondaryPreferred")
    result = client.admin.command("ping")
    print(f"  Authentication: SUCCESS!")
    print(f"  Ping response: {result}")

    # Count records to confirm data integrity
    db = client[vals.get("DATABASE_NAME", "CricketIQ")]
    matches = db["matches"].count_documents({})
    deliveries = db["deliveries"].count_documents({})
    print(f"  matches collection: {matches:,} documents")
    print(f"  deliveries collection: {deliveries:,} documents")

except OperationFailure as e:
    print(f"  Authentication: FAILED")
    print(f"  Atlas error code: {e.code}")
    print(f"  Message: {e.details.get('errmsg', str(e))}")
    print()
    print("  ROOT CAUSE: Credentials rejected by Atlas.")
    print("  The username or password in .env does not match the")
    print("  database user in Atlas -> Security -> Database Access.")
    print()
    print("  DIAGNOSTICS:")
    print(f"  - Username length: {len(username)} chars")
    print(f"  - Password length: {len(password)} chars")
    specials_p = [c for c in password if not c.isalnum()]
    if specials_p:
        print(f"  - Password has special chars {specials_p} - needs URL encoding!")
    else:
        print("  - Password is alphanumeric - encoding is not the issue")
    print()
    print("  FIX:")
    print("  1. Go to cloud.mongodb.com -> Security -> Database Access")
    print("  2. Edit the database user and SET (not just view) a new password")
    print("  3. Click 'Update User' button at the bottom - wait for deployment")
    print("  4. Update MONGODB_URI in .env with exactly that username:password")
    sys.exit(1)

except ServerSelectionTimeoutError as e:
    print(f"  Connection: TIMED OUT")
    print("  Network is blocking the connection despite TLS test passing.")
    sys.exit(1)

print("\n" + "=" * 50)
print("ALL CHECKS PASSED - Connection is healthy!")
print("=" * 50)
