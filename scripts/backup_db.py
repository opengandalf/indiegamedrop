#!/usr/bin/env python3
"""Database backup utility for IndieGameDrop.

Copies indiegamedrop.db to data/backups/ with date-stamped names.
Keeps last 7 daily backups, deletes older ones.

Usage:
    python3 scripts/backup_db.py
    python3 scripts/backup_db.py --keep 14  # keep 14 days instead of 7
"""

import os
import shutil
import glob
import argparse
from datetime import datetime

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "indiegamedrop.db"
)
BACKUP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "backups"
)


def backup_db(db_path=None, backup_dir=None, keep=7):
    """Create a dated backup of the database."""
    db_path = db_path or DEFAULT_DB_PATH
    backup_dir = backup_dir or BACKUP_DIR

    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False

    os.makedirs(backup_dir, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    backup_path = os.path.join(backup_dir, f"indiegamedrop-{today}.db")

    shutil.copy2(db_path, backup_path)
    size_mb = os.path.getsize(backup_path) / (1024 * 1024)
    print(f"✅ Backed up to {backup_path} ({size_mb:.1f} MB)")

    # Clean old backups
    backups = sorted(glob.glob(os.path.join(backup_dir, "indiegamedrop-*.db")))
    if len(backups) > keep:
        for old in backups[:-keep]:
            os.remove(old)
            print(f"🗑️  Removed old backup: {os.path.basename(old)}")

    remaining = glob.glob(os.path.join(backup_dir, "indiegamedrop-*.db"))
    print(f"📦 {len(remaining)} backup(s) retained")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup IndieGameDrop database")
    parser.add_argument("--db", default=None, help="Path to database")
    parser.add_argument("--keep", type=int, default=7, help="Number of backups to keep")
    args = parser.parse_args()
    backup_db(db_path=args.db, keep=args.keep)
