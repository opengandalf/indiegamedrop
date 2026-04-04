"""Main data pipeline orchestrator for IndieGameDrop."""

import json
import os
import sys
import logging
from datetime import datetime, date

from scripts.steam_client import SteamClient
from scripts.steamspy_client import SteamSpyClient
from scripts.database import Database, slugify
from scripts.scorer import Scorer

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "indiegamedrop.db"
)
STATIC_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "static", "data"
)


def get_db(db_path=None):
    """Get database instance, creating data dir if needed."""
    path = db_path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return Database(path)


def cmd_gather(db_path=None):
    """Fetch new indie games from Steam, enrich with SteamSpy."""
    db = get_db(db_path)
    steam = SteamClient()
    spy = SteamSpyClient()

    try:
        # Get featured game IDs from Steam
        logger.info("Fetching featured games from Steam...")
        app_ids = steam.get_featured_indie_games()
        logger.info("Found %d featured apps", len(app_ids))

        # Get details for indie games
        logger.info("Fetching app details...")
        games = steam.get_indie_app_details(app_ids, max_games=30)
        logger.info("Found %d indie games", len(games))

        # Store games in database
        for game in games:
            db.upsert_game(game)
            logger.info("Stored: %s", game.get("name"))

        # Enrich with SteamSpy data
        logger.info("Enriching with SteamSpy data...")
        stored_ids = [g["steam_app_id"] for g in games]
        enrichment = spy.enrich_games(stored_ids)

        # Take initial snapshots with enrichment data
        today = date.today().isoformat()
        for app_id, enrich in enrichment.items():
            total_reviews = enrich.get("positive", 0) + enrich.get("negative", 0)
            positive = enrich.get("positive", 0)
            pct = (positive / total_reviews * 100) if total_reviews > 0 else 0

            snapshot = {
                "steam_app_id": app_id,
                "snapshot_date": today,
                "review_count": total_reviews,
                "review_positive": positive,
                "review_percentage": round(pct, 1),
                "owner_estimate": enrich.get("owners", 0),
                "ccu_estimate": enrich.get("ccu", 0),
                "follower_count": 0,  # Not available from SteamSpy
                "median_playtime_minutes": enrich.get("median_playtime", 0),
                "price_usd": None,
                "discount_percent": 0,
            }
            db.insert_snapshot(snapshot)

        logger.info("Gather complete: %d games processed", len(games))
    finally:
        db.close()


def cmd_snapshot(db_path=None):
    """Take daily snapshot of all tracked games."""
    db = get_db(db_path)
    spy = SteamSpyClient()

    try:
        games = db.get_all_games()
        today = date.today().isoformat()
        logger.info("Taking snapshots for %d games", len(games))

        for game in games:
            app_id = game["steam_app_id"]
            enrich = spy.get_app_details(app_id)

            total_reviews = enrich.get("positive", 0) + enrich.get("negative", 0)
            positive = enrich.get("positive", 0)
            pct = (positive / total_reviews * 100) if total_reviews > 0 else 0

            snapshot = {
                "steam_app_id": app_id,
                "snapshot_date": today,
                "review_count": total_reviews,
                "review_positive": positive,
                "review_percentage": round(pct, 1),
                "owner_estimate": enrich.get("owners", 0),
                "ccu_estimate": enrich.get("ccu", 0),
                "follower_count": 0,
                "median_playtime_minutes": enrich.get("median_playtime", 0),
                "price_usd": game.get("price_usd"),
                "discount_percent": 0,
            }
            inserted = db.insert_snapshot(snapshot)
            if inserted:
                logger.info("Snapshot: %s", game["name"])
            else:
                logger.debug("Skipped (duplicate): %s", game["name"])

        logger.info("Snapshot complete")
    finally:
        db.close()


def cmd_score(db_path=None):
    """Recalculate all game scores."""
    db = get_db(db_path)
    try:
        scorer = Scorer(db)
        scorer.calculate_all_scores()
        logger.info("Scoring complete")
    finally:
        db.close()


def _check_db_integrity(db):
    """Safety check: refuse to export if game count is suspiciously low."""
    MIN_GAME_COUNT = 1000
    count = db.conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    if count < MIN_GAME_COUNT:
        raise RuntimeError(
            f"🚨 DB INTEGRITY CHECK FAILED: only {count} games in database "
            f"(minimum: {MIN_GAME_COUNT}). Refusing to export to prevent "
            f"overwriting good browse.db.gz with broken data. "
            f"Run restore script or investigate data loss."
        )
    return count


def _check_anomaly(game_count, out_dir):
    """Anomaly detection: warn if game count dropped significantly."""
    stats_file = os.path.join(
        os.path.dirname(out_dir), "..", "data", "last_export_stats.json"
    )
    # Normalize path
    stats_file = os.path.normpath(stats_file)
    if not os.path.exists(os.path.dirname(stats_file)):
        stats_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "last_export_stats.json"
        )

    last_stats = {}
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r") as f:
                last_stats = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    last_count = last_stats.get("total_games", 0)
    if last_count > 0 and game_count < last_count * 0.5:
        raise RuntimeError(
            f"🚨 ANOMALY DETECTED: game count dropped from {last_count} to "
            f"{game_count} (>50% decrease). Refusing to export. "
            f"Investigate data loss before retrying."
        )

    # Save current stats for next run
    current_stats = {
        "total_games": game_count,
        "last_export": datetime.now().isoformat(),
    }
    os.makedirs(os.path.dirname(stats_file), exist_ok=True)
    with open(stats_file, "w") as f:
        json.dump(current_stats, f, indent=2)


def cmd_export(db_path=None, output_dir=None):
    """Generate JSON files for Hugo."""
    db = get_db(db_path)
    out_dir = output_dir or STATIC_DATA_DIR
    os.makedirs(out_dir, exist_ok=True)
    games_dir = os.path.join(out_dir, "games")
    os.makedirs(games_dir, exist_ok=True)

    try:
        # Safety checks before exporting
        game_count = _check_db_integrity(db)
        _check_anomaly(game_count, out_dir)
        logger.info("DB integrity OK: %d games", game_count)

        _export_rising(db, out_dir)
        _export_gems(db, out_dir)
        _export_new_releases(db, out_dir)
        _export_watchlist(db, out_dir)
        _export_market_stats(db, out_dir)
        _export_game_profiles(db, games_dir)
        logger.info("Export complete to %s", out_dir)
    finally:
        db.close()


def _game_to_json(game, scores=None):
    """Convert a game database row to JSON-serializable dict."""
    data = {
        "steam_app_id": game["steam_app_id"],
        "name": game["name"],
        "slug": game.get("slug", ""),
        "developer": game.get("developer", ""),
        "publisher": game.get("publisher", ""),
        "release_date": game.get("release_date", ""),
        "price_usd": game.get("price_usd", 0),
        "genres": _parse_json_field(game.get("genres", "[]")),
        "tags": _parse_json_field(game.get("tags", "[]")),
        "platforms": _parse_json_field(game.get("platforms", "[]")),
        "short_description": game.get("short_description", ""),
        "header_image_url": game.get("header_image_url", ""),
        "screenshots": _parse_json_field(game.get("screenshots", "[]")),
    }
    if scores:
        data.update({
            "rising_score": scores.get("rising_score", 0),
            "gem_score": scores.get("gem_score", 0),
            "hype_score": scores.get("hype_score", 0),
            "review_velocity_7d": scores.get("review_velocity_7d", 0),
            "follower_velocity_7d": scores.get("follower_velocity_7d", 0),
            "classification": scores.get("classification", ""),
        })
    return data


def _parse_json_field(value):
    """Safely parse a JSON string field."""
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def _enrich_with_snapshot(data, db):
    """Add latest snapshot data to a game dict."""
    snapshot = db.get_latest_snapshot(data["steam_app_id"])
    if snapshot:
        data["review_count"] = snapshot.get("review_count", 0)
        data["review_positive"] = snapshot.get("review_positive", 0)
        data["review_percentage"] = snapshot.get("review_percentage", 0)
        data["owner_estimate"] = snapshot.get("owner_estimate", 0)
        data["ccu_estimate"] = snapshot.get("ccu_estimate", 0)
        data["follower_count"] = snapshot.get("follower_count", 0)
        data["median_playtime_minutes"] = snapshot.get("median_playtime_minutes", 0)
    return data


def _export_rising(db, out_dir):
    """Export rising games JSON."""
    games = db.get_top_rising(limit=20)
    result = []
    for g in games:
        data = _game_to_json(g, g)
        data = _enrich_with_snapshot(data, db)
        result.append(data)
    _write_json(os.path.join(out_dir, "rising.json"), result)
    logger.info("Exported %d rising games", len(result))


def _export_gems(db, out_dir):
    """Export hidden gems JSON."""
    games = db.get_hidden_gems(limit=20)
    result = []
    for g in games:
        data = _game_to_json(g, g)
        data = _enrich_with_snapshot(data, db)
        result.append(data)
    _write_json(os.path.join(out_dir, "gems.json"), result)
    logger.info("Exported %d hidden gems", len(result))


def _export_new_releases(db, out_dir):
    """Export new releases JSON."""
    games = db.get_new_releases(limit=20)
    result = []
    for g in games:
        data = _game_to_json(g, g)
        data = _enrich_with_snapshot(data, db)
        result.append(data)
    _write_json(os.path.join(out_dir, "new_releases.json"), result)
    logger.info("Exported %d new releases", len(result))


def _export_watchlist(db, out_dir):
    """Export watchlist JSON."""
    games = db.get_watchlist(limit=20)
    result = []
    for g in games:
        data = _game_to_json(g, g)
        data = _enrich_with_snapshot(data, db)
        result.append(data)
    _write_json(os.path.join(out_dir, "watchlist.json"), result)
    logger.info("Exported %d watchlist games", len(result))


def _export_market_stats(db, out_dir):
    """Export aggregate market stats JSON."""
    stats = db.get_market_stats()
    gems = db.get_hidden_gems(limit=1000)
    stats["hidden_gems"] = len(gems)
    _write_json(os.path.join(out_dir, "market_stats.json"), stats)
    logger.info("Exported market stats")


def _export_game_profiles(db, games_dir):
    """Export individual game profile JSONs."""
    games = db.get_all_games()
    count = 0
    for game in games:
        slug = game.get("slug", "")
        if not slug:
            continue
        # Truncate overly long slugs to avoid filesystem errors
        # Use byte length (ext4 limit is 255 bytes; leave room for .json)
        encoded = slug.encode('utf-8')
        if len(encoded) > 200:
            slug = encoded[:200].decode('utf-8', errors='ignore').rstrip('-')
        scores = db.get_scores(game["steam_app_id"])
        data = _game_to_json(game, scores)
        data = _enrich_with_snapshot(data, db)

        # Add snapshot history for charts
        snapshots = db.get_snapshots(game["steam_app_id"], days=30)
        data["history"] = [
            {
                "date": s["snapshot_date"],
                "review_count": s.get("review_count", 0),
                "review_percentage": s.get("review_percentage", 0),
                "ccu_estimate": s.get("ccu_estimate", 0),
                "follower_count": s.get("follower_count", 0),
            }
            for s in reversed(snapshots)
        ]

        _write_json(os.path.join(games_dir, f"{slug}.json"), data)
        count += 1
    logger.info("Exported %d game profiles", count)


def _write_json(filepath, data):
    """Write JSON data to file with validation."""
    # Validate by round-tripping through json
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    # Validate it parses back
    json.loads(json_str)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(json_str)


def main():
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    if len(sys.argv) < 2:
        print("Usage: python -m scripts.generate_data <command>")
        print("Commands: gather, snapshot, score, export, all")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "gather":
        cmd_gather()
    elif command == "snapshot":
        cmd_snapshot()
    elif command == "score":
        cmd_score()
    elif command == "export":
        cmd_export()
    elif command == "all":
        cmd_gather()
        cmd_score()
        cmd_export()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
