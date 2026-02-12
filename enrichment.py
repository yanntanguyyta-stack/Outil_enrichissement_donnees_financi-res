#!/usr/bin/env python3
"""
Unified enrichment module — DINUM API + SQLite finances.

Replaces the five former modules (enrichment_hybrid, enrichment_rne,
enrichment_rne_ondemand, enrichment_s3, enrichment_pappers).

Usage:
    from enrichment import enrich, enrich_batch, get_finances
"""

import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------- Configuration ----------

API_BASE_URL = "https://recherche-entreprises.api.gouv.fr"
API_DELAY = 0.5  # seconds between requests (rate limiting)
API_TIMEOUT = 10  # seconds
API_MAX_RETRIES = 3

DB_PATH = os.getenv("RNE_DB_PATH", "rne_finances.db")

# ---------- SQLite helpers ----------


def _ensure_db_decompressed() -> None:
    """Decompress rne_finances.db.xz if the .db is missing but the .xz exists."""
    db_path = Path(DB_PATH)
    xz_path = db_path.with_suffix(".db.xz")
    if not db_path.exists() and xz_path.exists():
        import lzma
        import shutil
        logger.info("Décompression de %s vers %s ...", xz_path, db_path)
        with lzma.open(xz_path, "rb") as src, open(db_path, "wb") as dst:
            shutil.copyfileobj(src, dst)
        logger.info("Décompression terminée (%d MB)", db_path.stat().st_size // (1024 * 1024))


def _get_db() -> Optional[sqlite3.Connection]:
    """Return a read-only connection to the finances DB, or None."""
    _ensure_db_decompressed()
    path = Path(DB_PATH)
    if not path.exists():
        logger.debug("SQLite DB not found at %s", DB_PATH)
        return None
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def db_available() -> bool:
    """Check whether the SQLite database is available (or can be decompressed)."""
    db_path = Path(DB_PATH)
    xz_path = db_path.with_suffix(".db.xz")
    return db_path.exists() or xz_path.exists()


def db_age_days() -> Optional[int]:
    """Return the age of the database in days, or None if missing."""
    path = Path(DB_PATH)
    if not path.exists():
        return None
    import datetime
    mtime = path.stat().st_mtime
    now = datetime.datetime.now(datetime.timezone.utc)
    modified = datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc)
    age = now - modified
    return age.days


def get_finances(siren: str, years: int = 7) -> Dict[str, Any]:
    """Retrieve financial history for a SIREN from SQLite.

    Returns:
        {
            "success": True/False,
            "siren": "...",
            "bilans": [ { date_cloture, chiffre_affaires, ... }, ... ],
            "count": N,
            "source": "sqlite",
        }
    """
    conn = _get_db()
    if conn is None:
        return {"success": False, "siren": siren, "error": "database_not_found"}

    try:
        cursor = conn.execute(
            "SELECT * FROM bilans WHERE siren = ? ORDER BY date_cloture DESC LIMIT ?",
            (str(siren).zfill(9), years),
        )
        rows = [dict(r) for r in cursor.fetchall()]
        return {
            "success": len(rows) > 0,
            "siren": siren,
            "bilans": rows,
            "count": len(rows),
            "source": "sqlite",
        }
    except sqlite3.Error as exc:
        logger.warning("SQLite error for %s: %s", siren, exc)
        return {"success": False, "siren": siren, "error": str(exc)}
    finally:
        conn.close()


# ---------- DINUM API ----------


def search_dinum(query: str) -> Optional[Dict[str, Any]]:
    """Search the DINUM API for a company by name/SIREN/SIRET."""
    import re

    search_query = query.strip()
    # If SIRET (14 digits), extract SIREN
    if re.match(r"^\d{14}$", search_query):
        search_query = search_query[:9]

    url = f"{API_BASE_URL}/search"
    params = {"q": search_query, "per_page": 1}

    for attempt in range(API_MAX_RETRIES):
        try:
            time.sleep(API_DELAY)
            resp = requests.get(url, params=params, timeout=API_TIMEOUT)

            if resp.status_code == 429:
                backoff = 2**attempt
                logger.warning("Rate limited, retrying in %ds", backoff)
                time.sleep(backoff)
                continue

            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            return results[0] if results else None
        except requests.RequestException as exc:
            logger.warning("DINUM API error (attempt %d): %s", attempt + 1, exc)

    return None


# ---------- Public API ----------


def enrich(siren: str, years: int = 7) -> Dict[str, Any]:
    """Enrich a single SIREN with DINUM data + SQLite finances.

    Returns a merged dict with company info and financial history.
    """
    result: Dict[str, Any] = {"siren": siren, "success": False}

    # DINUM lookup
    company = search_dinum(siren)
    if company:
        result["company"] = company
        result["success"] = True

    # SQLite finances
    finances = get_finances(siren, years)
    result["finances"] = finances

    return result


def enrich_batch(sirens: List[str], years: int = 7) -> Dict[str, Dict[str, Any]]:
    """Enrich multiple SIRENs. Returns {siren: enriched_data}."""
    results: Dict[str, Dict[str, Any]] = {}
    total = len(sirens)

    for idx, siren in enumerate(sirens, 1):
        if idx % 50 == 0:
            logger.info("Batch progress: %d/%d", idx, total)
        results[siren] = enrich(siren, years)

    return results
