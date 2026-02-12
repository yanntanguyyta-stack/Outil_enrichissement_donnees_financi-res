#!/usr/bin/env python3
"""
Build the SQLite database of financial data from RNE JSON files.

Can work from:
  1. Local cache (rne_cache/ directory with JSON files)
  2. FTP download (streaming from INPI ZIP)

Extracts 6 key financial metrics (FA, HN, GC, BJ, DL, HY) with m1/m2 values.
Only keeps records since 2019.

Usage:
    python build_rne_db.py                  # from local cache
    python build_rne_db.py --from-ftp       # from FTP (downloads ZIP)
    python build_rne_db.py --db mydb.db     # custom output path
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
import zipfile
from ftplib import FTP
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Financial metric codes to extract
LIASSE_CODES = {"FA", "HN", "GC", "BJ", "DL", "HY"}
LIASSE_MAP = {
    "FA": ("chiffre_affaires", "ca_precedent"),
    "HN": ("resultat_net", "rn_precedent"),
    "GC": ("resultat_exploitation", "re_precedent"),
    "BJ": ("total_actif", "ta_precedent"),
    "DL": ("capitaux_propres", "cp_precedent"),
    "HY": ("effectif", "eff_precedent"),
}

MIN_DATE = "2019-01-01"

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS bilans (
    id INTEGER PRIMARY KEY,
    siren TEXT NOT NULL,
    date_cloture TEXT NOT NULL,
    date_depot TEXT,
    type_bilan TEXT,
    chiffre_affaires INTEGER,
    resultat_net INTEGER,
    resultat_exploitation INTEGER,
    total_actif INTEGER,
    capitaux_propres INTEGER,
    effectif INTEGER,
    ca_precedent INTEGER,
    rn_precedent INTEGER,
    re_precedent INTEGER,
    ta_precedent INTEGER,
    cp_precedent INTEGER,
    eff_precedent INTEGER
);
CREATE INDEX IF NOT EXISTS idx_siren ON bilans(siren);
CREATE INDEX IF NOT EXISTS idx_siren_date ON bilans(siren, date_cloture DESC);
"""

INSERT_SQL = """
INSERT INTO bilans (
    siren, date_cloture, date_depot, type_bilan,
    chiffre_affaires, resultat_net, resultat_exploitation,
    total_actif, capitaux_propres, effectif,
    ca_precedent, rn_precedent, re_precedent,
    ta_precedent, cp_precedent, eff_precedent
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _parse_amount(value: Any) -> Optional[int]:
    """Parse a financial amount, handling string/int/float and trailing zeros."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        value = value.strip().replace(" ", "").replace("\u00a0", "")
        if not value or value in ("", "-", "N/A"):
            return None
        try:
            return int(float(value))
        except (ValueError, OverflowError):
            return None
    return None


def extract_bilans_from_json(data: Any) -> List[Tuple]:
    """Extract financial records from a single RNE JSON structure.

    Returns list of tuples ready for INSERT.
    """
    rows: List[Tuple] = []

    if isinstance(data, dict):
        items = data.get("bilans", data.get("results", [data]))
        if not isinstance(items, list):
            items = [data]
    elif isinstance(data, list):
        items = data
    else:
        return rows

    for item in items:
        siren = item.get("siren", "")
        if not siren or len(str(siren)) != 9:
            continue

        date_cloture = item.get("dateCloture", item.get("date_cloture", ""))
        if not date_cloture or date_cloture < MIN_DATE:
            continue

        date_depot = item.get("dateDepot", item.get("date_depot", ""))
        type_bilan = item.get("typeBilan", item.get("type_bilan", ""))

        # Extract the 6 metrics from liasse data
        metrics: Dict[str, Optional[int]] = {}
        metrics_prev: Dict[str, Optional[int]] = {}

        # Try "metrics" structure first (common in cache files)
        metrics_dict = item.get("metrics", {})
        if isinstance(metrics_dict, dict):
            for code, (col_n, col_n1) in LIASSE_MAP.items():
                metric_data = metrics_dict.get(code, {})
                if isinstance(metric_data, dict):
                    m1 = _parse_amount(metric_data.get("m1"))
                    m2 = _parse_amount(metric_data.get("m2"))
                    if m1 is not None:
                        metrics[col_n] = m1
                    if m2 is not None:
                        metrics_prev[col_n1] = m2

        # Try bilanSaisi.bilan.detail.pages structure (alternative format)
        if not metrics:
            pages = []
            bilan_saisi = item.get("bilanSaisi", {})
            if isinstance(bilan_saisi, dict):
                bilan = bilan_saisi.get("bilan", {})
                if isinstance(bilan, dict):
                    detail = bilan.get("detail", {})
                    if isinstance(detail, dict):
                        pages = detail.get("pages", [])

            for page in pages:
                if not isinstance(page, dict):
                    continue
                liasses = page.get("lignes", [])
                if not isinstance(liasses, list):
                    continue
                for liasse in liasses:
                    if not isinstance(liasse, dict):
                        continue
                    code = liasse.get("code", "")
                    if code in LIASSE_CODES:
                        m1 = _parse_amount(liasse.get("m1"))
                        m2 = _parse_amount(liasse.get("m2"))
                        col_n, col_n1 = LIASSE_MAP[code]
                        if m1 is not None:
                            metrics[col_n] = m1
                        if m2 is not None:
                            metrics_prev[col_n1] = m2

        # Also try flat structure (already extracted data)
        for code, (col_n, col_n1) in LIASSE_MAP.items():
            if col_n not in metrics:
                val = item.get(col_n)
                if val is not None:
                    metrics[col_n] = _parse_amount(val)
            if col_n1 not in metrics_prev:
                val = item.get(col_n1)
                if val is not None:
                    metrics_prev[col_n1] = _parse_amount(val)

        row = (
            str(siren),
            date_cloture,
            date_depot or None,
            type_bilan or None,
            metrics.get("chiffre_affaires"),
            metrics.get("resultat_net"),
            metrics.get("resultat_exploitation"),
            metrics.get("total_actif"),
            metrics.get("capitaux_propres"),
            metrics.get("effectif"),
            metrics_prev.get("ca_precedent"),
            metrics_prev.get("rn_precedent"),
            metrics_prev.get("re_precedent"),
            metrics_prev.get("ta_precedent"),
            metrics_prev.get("cp_precedent"),
            metrics_prev.get("eff_precedent"),
        )
        rows.append(row)

    return rows


def init_db(db_path: str) -> sqlite3.Connection:
    """Create or reset the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.executescript(DB_SCHEMA)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def build_from_cache(db_path: str, cache_dir: str) -> int:
    """Build the database from local JSON cache files."""
    cache = Path(cache_dir)
    if not cache.exists():
        logger.error("Cache directory not found: %s", cache_dir)
        return 0

    json_files = sorted(cache.glob("*.json"))
    if not json_files:
        logger.error("No JSON files found in %s", cache_dir)
        return 0

    logger.info("Found %d JSON files in cache", len(json_files))

    conn = init_db(db_path)
    total_rows = 0
    batch: List[Tuple] = []
    batch_size = 10_000

    for idx, filepath in enumerate(json_files, 1):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            rows = extract_bilans_from_json(data)
            batch.extend(rows)

            if len(batch) >= batch_size:
                conn.executemany(INSERT_SQL, batch)
                conn.commit()
                total_rows += len(batch)
                batch.clear()

            if idx % 100 == 0 or idx == len(json_files):
                logger.info(
                    "Progress: %d/%d files, %d rows inserted",
                    idx,
                    len(json_files),
                    total_rows + len(batch),
                )
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Skipping %s: %s", filepath.name, exc)

    if batch:
        conn.executemany(INSERT_SQL, batch)
        conn.commit()
        total_rows += len(batch)

    conn.close()
    logger.info("Build complete: %d rows in %s", total_rows, db_path)
    return total_rows


def build_from_ftp(db_path: str) -> int:
    """Build the database by streaming from the FTP ZIP."""
    host = os.getenv("FTP_HOST", "www.inpi.net")
    user = os.getenv("FTP_USER", "")
    password = os.getenv("FTP_PASSWORD", "")

    if not user or not password:
        logger.error(
            "FTP credentials not set. Create a .env file with FTP_USER and FTP_PASSWORD."
        )
        return 0

    logger.info("Connecting to FTP %s@%s ...", user, host)
    ftp = FTP(host, timeout=120)
    ftp.login(user, password)

    # Find the most recent ZIP
    files = ftp.nlst()
    zip_files = [f for f in files if "comptes_annuels" in f and f.endswith(".zip")]
    if not zip_files:
        logger.error("No comptes_annuels ZIP found on FTP")
        ftp.quit()
        return 0

    zip_name = sorted(zip_files)[-1]
    logger.info("Downloading %s ...", zip_name)

    # Download to temporary file
    tmp_zip = Path(db_path).parent / f"_tmp_{zip_name}"
    with open(tmp_zip, "wb") as f:
        ftp.retrbinary(f"RETR {zip_name}", f.write)
    ftp.quit()

    logger.info("Download complete. Extracting data ...")

    conn = init_db(db_path)
    total_rows = 0
    batch: List[Tuple] = []
    batch_size = 10_000

    try:
        with zipfile.ZipFile(str(tmp_zip), "r") as zf:
            json_names = [n for n in zf.namelist() if n.endswith(".json")]
            logger.info("ZIP contains %d JSON files", len(json_names))

            for idx, name in enumerate(json_names, 1):
                try:
                    with zf.open(name) as entry:
                        data = json.load(entry)
                    rows = extract_bilans_from_json(data)
                    batch.extend(rows)

                    if len(batch) >= batch_size:
                        conn.executemany(INSERT_SQL, batch)
                        conn.commit()
                        total_rows += len(batch)
                        batch.clear()

                    if idx % 100 == 0 or idx == len(json_names):
                        logger.info(
                            "Progress: %d/%d files, %d rows",
                            idx,
                            len(json_names),
                            total_rows + len(batch),
                        )
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning("Skipping %s: %s", name, exc)
    finally:
        if tmp_zip.exists():
            tmp_zip.unlink()
            logger.info("Temporary ZIP removed")

    if batch:
        conn.executemany(INSERT_SQL, batch)
        conn.commit()
        total_rows += len(batch)

    conn.close()
    logger.info("Build complete: %d rows in %s", total_rows, db_path)
    return total_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build RNE finances SQLite database")
    parser.add_argument(
        "--db",
        default="rne_finances.db",
        help="Output database path (default: rne_finances.db)",
    )
    parser.add_argument(
        "--from-ftp",
        action="store_true",
        help="Download from FTP instead of using local cache",
    )
    parser.add_argument(
        "--cache-dir",
        default="rne_cache",
        help="Local cache directory (default: rne_cache)",
    )
    args = parser.parse_args()

    start = time.time()

    if args.from_ftp:
        total = build_from_ftp(args.db)
    else:
        total = build_from_cache(args.db, args.cache_dir)

    elapsed = time.time() - start
    logger.info("Done in %.1fs — %d records", elapsed, total)

    if total == 0:
        logger.warning("No data was imported. Check your source.")
        sys.exit(1)

    # Print DB size
    db_size = Path(args.db).stat().st_size / (1024 * 1024)
    logger.info("Database size: %.1f MB", db_size)


if __name__ == "__main__":
    main()
