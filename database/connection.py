"""
database/connection.py - MongoDB connection management.
"""
import sys
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError, ServerSelectionTimeoutError
import config

import socket
try:
    import requests
    _orig_getaddrinfo = socket.getaddrinfo
    _dns_cache = {
        "ac-llmldbn-shard-00-00.acu22hg.mongodb.net": "159.41.183.67",
        "ac-llmldbn-shard-00-01.acu22hg.mongodb.net": "159.41.183.81",
        "ac-llmldbn-shard-00-02.acu22hg.mongodb.net": "159.41.183.103",
        "ac-1u9z7gh-shard-00-00.hta0f0h.mongodb.net": "159.41.242.92",
        "ac-1u9z7gh-shard-00-01.hta0f0h.mongodb.net": "159.41.242.103",
        "ac-1u9z7gh-shard-00-02.hta0f0h.mongodb.net": "159.41.242.120",
    }

    def _smart_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        try:
            return _orig_getaddrinfo(host, port, family, type, proto, flags)
        except Exception:
            if host in _dns_cache:
                return _orig_getaddrinfo(_dns_cache[host], port, family, type, proto, flags)
            try:
                r = requests.get(f"https://dns.google/resolve?name={host}&type=A", timeout=2.5).json()
                for a in r.get("Answer", []):
                    if a.get("type") == 1:
                        ip = a["data"]
                        _dns_cache[host] = ip
                        return _orig_getaddrinfo(ip, port, family, type, proto, flags)
            except Exception:
                pass
            raise

    socket.getaddrinfo = _smart_getaddrinfo
except Exception:
    pass


def _normalize_atlas_uri(uri: str) -> str:
    """
    Ensure robust connectivity across restrictive networks (e.g. campus Wi-Fi blocking UDP port 53)
    by expanding SRV to direct shard replica set endpoints when SRV resolution fails or is blocked.
    """
    if "hta0f0h.mongodb.net" in uri and uri.startswith("mongodb+srv://"):
        shards = (
            "ac-1u9z7gh-shard-00-00.hta0f0h.mongodb.net:27017,"
            "ac-1u9z7gh-shard-00-01.hta0f0h.mongodb.net:27017,"
            "ac-1u9z7gh-shard-00-02.hta0f0h.mongodb.net:27017"
        )
        prefix_end = uri.find("@")
        if prefix_end != -1:
            auth_part = uri[len("mongodb+srv://"):prefix_end]
            rest = uri[prefix_end + 1:]
            slash_idx = rest.find("/")
            db_and_params = rest[slash_idx:] if slash_idx != -1 else "/CricketIQ?retryWrites=true&w=majority"
            if not db_and_params.startswith("/"):
                db_and_params = "/" + db_and_params
            params_delimiter = "&" if "?" in db_and_params else "?"
            return f"mongodb://{auth_part}@{shards}{db_and_params}{params_delimiter}ssl=true&authSource=admin"

    if "acu22hg.mongodb.net" in uri:
        shards = (
            "mtm-aws-aps1-7-m0-16-shard-00-00.bmkjo.mongodb.net:27017,"
            "mtm-aws-aps1-7-m0-16-shard-00-01.bmkjo.mongodb.net:27017,"
            "mtm-aws-aps1-7-m0-16-shard-00-02.bmkjo.mongodb.net:27017"
        )
        if uri.startswith("mongodb+srv://"):
            prefix_end = uri.find("@")
            if prefix_end != -1:
                auth_part = uri[len("mongodb+srv://"):prefix_end]
                rest = uri[prefix_end + 1:]
                slash_idx = rest.find("/")
                db_and_params = rest[slash_idx:] if slash_idx != -1 else "/CricketIQ?retryWrites=true&w=majority"
                params_delimiter = "&" if "?" in db_and_params else "?"
                return f"mongodb://{auth_part}@{shards}{db_and_params}{params_delimiter}ssl=true&authSource=admin"
    return uri


_client: MongoClient | None = None


def get_client() -> MongoClient:
    """Return a shared MongoClient, creating one if needed."""
    global _client
    if _client is None:
        raw_uri = config.MONGODB_URI
        effective_uri = _normalize_atlas_uri(raw_uri)
        safe_uri = _mask_uri(raw_uri)
        try:
            _client = MongoClient(
                effective_uri,
                serverSelectionTimeoutMS=20_000,
                connectTimeoutMS=20_000,
                socketTimeoutMS=60_000,
                maxIdleTimeMS=45_000,
                retryWrites=True,
                retryReads=True,
                readPreference="secondaryPreferred",
            )
            # Ping to verify connection
            _client.admin.command("ping", read_preference=pymongo.ReadPreference.SECONDARY_PREFERRED)
        except pymongo.errors.OperationFailure as exc:
            print(
                f"ERROR: MongoDB authentication failed for {safe_uri}.\n"
                "Please verify your database username and password in MongoDB Atlas -> Security -> Database Access.",
                file=sys.stderr,
            )
            raise
        except ServerSelectionTimeoutError:
            print(
                f"ERROR: Could not reach MongoDB at {safe_uri}.\n"
                "Check that your MONGODB_URI in .env is correct, the cluster is reachable, and your IP is in Atlas Network Access.",
                file=sys.stderr,
            )
            raise
        except (ConnectionFailure, ConfigurationError) as exc:
            print(
                f"ERROR: MongoDB connection failed ({type(exc).__name__}) for {safe_uri}.\n"
                f"Details: {exc}",
                file=sys.stderr,
            )
            raise
    return _client


def get_db():
    """Return the CricketIQ database handle."""
    return get_client()[config.DATABASE_NAME]


def close_client() -> None:
    """Close the shared client if open."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


def _mask_uri(uri: str) -> str:
    """Replace password in URI with *** for safe logging."""
    try:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(uri)
        if parsed.password:
            netloc = parsed.netloc.replace(parsed.password, "***")
            return urlunparse(parsed._replace(netloc=netloc))
    except Exception:
        pass
    return "<uri hidden>"
