#!/usr/bin/env python3
"""
Update the RNE finances SQLite database.

Detects the most recent ZIP on the INPI FTP, downloads it,
and rebuilds the database. Keeps the previous DB as backup
during reconstruction.

Usage:
    python update_rne_db.py
    python update_rne_db.py --db rne_finances.db
"""

import argparse
import logging
import os
import shutil
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from build_rne_db import build_from_ftp

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def update_db(db_path: str) -> bool:
    """Download latest data and rebuild the database.

    1. Renames the current DB to .bak
    2. Builds a new DB from FTP
    3. On success, removes the backup
    4. On failure, restores the backup
    """
    db = Path(db_path)
    backup = db.with_suffix(".db.bak")

    # Backup existing DB
    if db.exists():
        logger.info("Backing up current DB to %s", backup)
        shutil.copy2(str(db), str(backup))

    start = time.time()
    try:
        total = build_from_ftp(db_path)
    except Exception as exc:
        logger.error("Build failed for %s: %s", db_path, exc)
        total = 0

    if total > 0:
        elapsed = time.time() - start
        db_size = db.stat().st_size / (1024 * 1024)
        logger.info(
            "Update successful: %d records, %.1f MB, %.0fs", total, db_size, elapsed
        )
        # Remove backup on success
        if backup.exists():
            backup.unlink()
            logger.info("Backup removed")
        return True
    else:
        logger.error("Update failed — no records imported")
        # Restore backup
        if backup.exists():
            shutil.move(str(backup), str(db))
            logger.info("Previous DB restored from backup")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Update RNE finances database")
    parser.add_argument(
        "--db",
        default="rne_finances.db",
        help="Database path (default: rne_finances.db)",
    )
    args = parser.parse_args()

    ok = update_db(args.db)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
