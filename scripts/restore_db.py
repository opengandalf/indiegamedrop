#!/usr/bin/env python3
"""Database restore utility for IndieGameDrop.

Restore from a dated backup or rebuild from browse.db.gz.

Usage:
    python3 scripts/restore_db.py                          # restore latest backup
    python3 scripts/restore_db.py --from-backup 2026-04-04 # specific date
    python3 scripts/restore_db.py --from-browse             # rebuild from browse.db.gz
    python3 scripts/restore_db.py --list                    # list available backups
"""

import os
import sys
import glob
import gzip
import shutil
import sqlite3
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
BROWSE_GZ_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "static", "data", "browse.db.gz"
)

MIN_EXPECTED_GAMES = 1000


def list_backups():
    """List available backups."""
    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "indiegamedrop-*.db")))
    if not backups:
        print("No backups found.")
        return
    for b in backups:
        size_mb = os.path.getsize(b) / (1024 * 1024)
        name = os.path.basename(b)
        print(f"  {name}  ({size_mb:.1f} MB)")


def validate_db(db_path):
    """Check the restored DB has a reasonable game count."""
    conn = sqlite3.connect(db_path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
        if count < MIN_EXPECTED_GAMES:
            print(f"⚠️  WARNING: Only {count} games in restored DB (expected {MIN_EXPECTED_GAMES}+)")
            return False
        print(f"✅ Validation passed: {count} games")
        return True
    except sqlite3.OperationalError as e:
        print(f"❌ Validation failed: {e}")
        return False
    finally:
        conn.close()


def restore_from_backup(date_str=None, db_path=None):
    """Restore from a dated backup file."""
    db_path = db_path or DEFAULT_DB_PATH
    if date_str:
        backup_path = os.path.join(BACKUP_DIR, f"indiegamedrop-{date_str}.db")
    else:
        backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "indiegamedrop-*.db")))
        if not backups:
            print("❌ No backups found.")
            return False
        backup_path = backups[-1]
        print(f"Using latest backup: {os.path.basename(backup_path)}")

    if not os.path.exists(backup_path):
        print(f"❌ Backup not found: {backup_path}")
        return False

    # Back up current DB first
    if os.path.exists(db_path):
        shutil.copy2(db_path, db_path + ".pre-restore")
        print(f"Saved current DB to {db_path}.pre-restore")

    shutil.copy2(backup_path, db_path)
    print(f"Restored from {os.path.basename(backup_path)}")
    return validate_db(db_path)


def restore_from_browse(db_path=None, browse_gz=None):
    """Rebuild the main DB from browse.db.gz."""
    db_path = db_path or DEFAULT_DB_PATH
    browse_gz = browse_gz or BROWSE_GZ_PATH

    if not os.path.exists(browse_gz):
        print(f"❌ browse.db.gz not found: {browse_gz}")
        return False

    # Decompress browse.db.gz to temp
    tmp_browse = "/tmp/browse_restore.db"
    with gzip.open(browse_gz, 'rb') as f_in:
        with open(tmp_browse, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    browse_count = sqlite3.connect(tmp_browse).execute(
        "SELECT COUNT(*) FROM games"
    ).fetchone()[0]
    print(f"browse.db.gz contains {browse_count} games")

    if browse_count < MIN_EXPECTED_GAMES:
        print(f"❌ browse.db.gz has too few games ({browse_count}). Aborting.")
        os.remove(tmp_browse)
        return False

    # Back up current DB
    if os.path.exists(db_path):
        shutil.copy2(db_path, db_path + ".pre-restore")
        print(f"Saved current DB to {db_path}.pre-restore")

    # Open main DB and import
    conn = sqlite3.connect(db_path)
    conn.execute("ATTACH DATABASE ? AS browse", (tmp_browse,))

    # Preserve existing tables that browse.db doesn't have
    existing_snapshots = conn.execute(
        "SELECT COUNT(*) FROM game_snapshots"
    ).fetchone()[0]
    existing_content = conn.execute(
        "SELECT COUNT(*) FROM published_content"
    ).fetchone()[0]

    conn.execute("BEGIN TRANSACTION")

    # Clear and reimport games
    conn.execute("DELETE FROM games")
    conn.execute("""
        INSERT INTO games (steam_app_id, name, slug, developer, release_date,
                          genres, tags, platforms, header_image_url,
                          short_description, price_usd, publisher, screenshots, is_indie)
        SELECT steam_app_id, name, slug, developer, release_date,
               genres, tags, platforms, header_image_url,
               short_description, price_usd, '', '', 1
        FROM browse.games
    """)

    # Import scores
    conn.execute("DELETE FROM game_scores")
    conn.execute("""
        INSERT OR REPLACE INTO game_scores (steam_app_id, gem_score, rising_score, last_calculated)
        SELECT steam_app_id, gem_score, rising_score, datetime('now')
        FROM browse.games
        WHERE gem_score > 0 OR rising_score > 0
    """)

    # Import review data as snapshots (only if we don't already have snapshots)
    if existing_snapshots == 0:
        conn.execute("""
            INSERT OR IGNORE INTO game_snapshots
                (steam_app_id, snapshot_date, review_count, review_percentage, owner_estimate, price_usd)
            SELECT steam_app_id, date('now'), review_count, review_percentage, owner_estimate, price_usd
            FROM browse.games
            WHERE review_count > 0
        """)

    conn.execute("COMMIT")
    conn.execute("DETACH DATABASE browse")

    new_count = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    conn.close()
    os.remove(tmp_browse)

    print(f"Restored {new_count} games from browse.db.gz")
    print(f"Preserved: {existing_snapshots} snapshots, {existing_content} published_content rows")
    return validate_db(db_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore IndieGameDrop database")
    parser.add_argument("--from-backup", nargs="?", const="latest",
                       help="Restore from backup (optionally specify date YYYY-MM-DD)")
    parser.add_argument("--from-browse", action="store_true",
                       help="Rebuild from browse.db.gz")
    parser.add_argument("--list", action="store_true",
                       help="List available backups")
    parser.add_argument("--db", default=None, help="Path to target database")

    args = parser.parse_args()

    if args.list:
        list_backups()
    elif args.from_browse:
        ok = restore_from_browse(db_path=args.db)
        sys.exit(0 if ok else 1)
    elif args.from_backup is not None:
        date_str = None if args.from_backup == "latest" else args.from_backup
        ok = restore_from_backup(date_str=date_str, db_path=args.db)
        sys.exit(0 if ok else 1)
    else:
        parser.print_help()
