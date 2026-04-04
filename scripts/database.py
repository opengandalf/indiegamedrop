"""SQLite database management for IndieGameDrop."""

import json
import sqlite3
import logging
import re

logger = logging.getLogger(__name__)


def slugify(name, max_bytes=200):
    """Convert a game name to a URL-safe slug.

    Truncates to max_bytes UTF-8 bytes to avoid filesystem filename limits
    (ext4 allows 255 bytes; we leave room for the .json extension).
    """
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    # Truncate to max_bytes UTF-8 bytes, cutting at a character boundary
    encoded = slug.encode('utf-8')
    if len(encoded) > max_bytes:
        slug = encoded[:max_bytes].decode('utf-8', errors='ignore').rstrip('-')
    return slug


class Database:
    """SQLite database manager for game data."""

    def __init__(self, db_path=":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def _create_tables(self):
        """Create all required tables."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS games (
                steam_app_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                slug TEXT UNIQUE,
                developer TEXT,
                publisher TEXT,
                release_date TEXT,
                price_usd REAL,
                genres TEXT,
                tags TEXT,
                platforms TEXT,
                short_description TEXT,
                header_image_url TEXT,
                screenshots TEXT,
                is_indie BOOLEAN DEFAULT 1,
                first_seen TEXT DEFAULT (datetime('now')),
                last_updated TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS game_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                steam_app_id INTEGER NOT NULL,
                snapshot_date TEXT NOT NULL,
                review_count INTEGER DEFAULT 0,
                review_positive INTEGER DEFAULT 0,
                review_percentage REAL DEFAULT 0,
                owner_estimate INTEGER DEFAULT 0,
                ccu_estimate INTEGER DEFAULT 0,
                follower_count INTEGER DEFAULT 0,
                median_playtime_minutes INTEGER DEFAULT 0,
                price_usd REAL,
                discount_percent INTEGER DEFAULT 0,
                UNIQUE(steam_app_id, snapshot_date),
                FOREIGN KEY (steam_app_id) REFERENCES games(steam_app_id)
            );

            CREATE TABLE IF NOT EXISTS game_scores (
                steam_app_id INTEGER PRIMARY KEY,
                rising_score REAL DEFAULT 0,
                gem_score REAL DEFAULT 0,
                hype_score REAL DEFAULT 0,
                review_velocity_7d REAL DEFAULT 0,
                follower_velocity_7d REAL DEFAULT 0,
                ccu_growth_7d REAL DEFAULT 0,
                classification TEXT DEFAULT 'new_release',
                last_calculated TEXT,
                FOREIGN KEY (steam_app_id) REFERENCES games(steam_app_id)
            );

            CREATE TABLE IF NOT EXISTS published_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_type TEXT NOT NULL,
                steam_app_id INTEGER,
                slug TEXT,
                published_date TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (steam_app_id) REFERENCES games(steam_app_id)
            );
        """)
        self.conn.commit()

    def upsert_game(self, game_data):
        """Insert or update a game record."""
        slug = slugify(game_data.get("name", ""))
        # Handle slug collisions: if another game already owns this slug, append app_id
        app_id = game_data.get("steam_app_id")
        existing = self.conn.execute(
            "SELECT steam_app_id FROM games WHERE slug = ? AND steam_app_id != ?",
            (slug, app_id)
        ).fetchone()
        if existing:
            slug = f"{slug}-{app_id}"
        genres = json.dumps(game_data.get("genres", []))
        tags = json.dumps(game_data.get("tags", []))
        platforms = json.dumps(game_data.get("platforms", []))
        screenshots = json.dumps(game_data.get("screenshots", []))

        self.conn.execute("""
            INSERT INTO games (
                steam_app_id, name, slug, developer, publisher,
                release_date, price_usd, genres, tags, platforms,
                short_description, header_image_url, screenshots,
                is_indie, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(steam_app_id) DO UPDATE SET
                name=excluded.name,
                slug=excluded.slug,
                developer=excluded.developer,
                publisher=excluded.publisher,
                release_date=excluded.release_date,
                price_usd=excluded.price_usd,
                genres=excluded.genres,
                tags=excluded.tags,
                platforms=excluded.platforms,
                short_description=excluded.short_description,
                header_image_url=excluded.header_image_url,
                screenshots=excluded.screenshots,
                is_indie=excluded.is_indie,
                last_updated=datetime('now')
        """, (
            game_data["steam_app_id"],
            game_data.get("name", ""),
            slug,
            game_data.get("developer", ""),
            game_data.get("publisher", ""),
            game_data.get("release_date", ""),
            game_data.get("price_usd", 0.0),
            genres, tags, platforms,
            game_data.get("short_description", ""),
            game_data.get("header_image_url", ""),
            screenshots,
            game_data.get("is_indie", True),
        ))
        self.conn.commit()

    def insert_snapshot(self, snapshot_data):
        """Insert a game snapshot (daily data point).

        Returns True if inserted, False if duplicate.
        """
        try:
            self.conn.execute("""
                INSERT INTO game_snapshots (
                    steam_app_id, snapshot_date, review_count,
                    review_positive, review_percentage, owner_estimate,
                    ccu_estimate, follower_count, median_playtime_minutes,
                    price_usd, discount_percent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot_data["steam_app_id"],
                snapshot_data["snapshot_date"],
                snapshot_data.get("review_count", 0),
                snapshot_data.get("review_positive", 0),
                snapshot_data.get("review_percentage", 0.0),
                snapshot_data.get("owner_estimate", 0),
                snapshot_data.get("ccu_estimate", 0),
                snapshot_data.get("follower_count", 0),
                snapshot_data.get("median_playtime_minutes", 0),
                snapshot_data.get("price_usd"),
                snapshot_data.get("discount_percent", 0),
            ))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            logger.debug(
                "Duplicate snapshot for %s on %s",
                snapshot_data["steam_app_id"],
                snapshot_data["snapshot_date"]
            )
            return False

    def update_scores(self, steam_app_id, scores):
        """Insert or update game scores."""
        self.conn.execute("""
            INSERT INTO game_scores (
                steam_app_id, rising_score, gem_score, hype_score,
                review_velocity_7d, follower_velocity_7d, ccu_growth_7d,
                classification, last_calculated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(steam_app_id) DO UPDATE SET
                rising_score=excluded.rising_score,
                gem_score=excluded.gem_score,
                hype_score=excluded.hype_score,
                review_velocity_7d=excluded.review_velocity_7d,
                follower_velocity_7d=excluded.follower_velocity_7d,
                ccu_growth_7d=excluded.ccu_growth_7d,
                classification=excluded.classification,
                last_calculated=datetime('now')
        """, (
            steam_app_id,
            scores.get("rising_score", 0.0),
            scores.get("gem_score", 0.0),
            scores.get("hype_score", 0.0),
            scores.get("review_velocity_7d", 0.0),
            scores.get("follower_velocity_7d", 0.0),
            scores.get("ccu_growth_7d", 0.0),
            scores.get("classification", "new_release"),
        ))
        self.conn.commit()

    def insert_published_content(self, content_type, steam_app_id=None,
                                 slug=None):
        """Record published content."""
        self.conn.execute("""
            INSERT INTO published_content (content_type, steam_app_id, slug)
            VALUES (?, ?, ?)
        """, (content_type, steam_app_id, slug))
        self.conn.commit()

    def get_game(self, steam_app_id):
        """Get a single game by ID."""
        row = self.conn.execute(
            "SELECT * FROM games WHERE steam_app_id = ?",
            (steam_app_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_game_by_slug(self, slug):
        """Get a single game by slug."""
        row = self.conn.execute(
            "SELECT * FROM games WHERE slug = ?",
            (slug,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_games(self):
        """Get all games."""
        rows = self.conn.execute(
            "SELECT * FROM games ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_latest_snapshot(self, steam_app_id):
        """Get the most recent snapshot for a game."""
        row = self.conn.execute("""
            SELECT * FROM game_snapshots
            WHERE steam_app_id = ?
            ORDER BY snapshot_date DESC LIMIT 1
        """, (steam_app_id,)).fetchone()
        return dict(row) if row else None

    def get_snapshots(self, steam_app_id, days=7):
        """Get recent snapshots for a game."""
        rows = self.conn.execute("""
            SELECT * FROM game_snapshots
            WHERE steam_app_id = ?
            ORDER BY snapshot_date DESC LIMIT ?
        """, (steam_app_id, days)).fetchall()
        return [dict(r) for r in rows]

    def get_scores(self, steam_app_id):
        """Get scores for a game."""
        row = self.conn.execute(
            "SELECT * FROM game_scores WHERE steam_app_id = ?",
            (steam_app_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_top_rising(self, limit=20):
        """Get top games by rising score."""
        rows = self.conn.execute("""
            SELECT g.*, s.rising_score, s.gem_score, s.hype_score,
                   s.review_velocity_7d, s.classification
            FROM games g
            JOIN game_scores s ON g.steam_app_id = s.steam_app_id
            WHERE s.rising_score > 0
            ORDER BY s.rising_score DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_hidden_gems(self, limit=20):
        """Get top hidden gems."""
        rows = self.conn.execute("""
            SELECT g.*, s.gem_score, s.rising_score
            FROM games g
            JOIN game_scores s ON g.steam_app_id = s.steam_app_id
            WHERE s.gem_score > 0
            ORDER BY s.gem_score DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_new_releases(self, limit=20):
        """Get genuinely recent releases (last 30 days by actual release date)."""
        rows = self.conn.execute("""
            SELECT g.*, s.rising_score, s.gem_score
            FROM games g
            LEFT JOIN game_scores s ON g.steam_app_id = s.steam_app_id
            WHERE g.release_date != ''
              AND date(g.release_date) >= date('now', '-30 days')
              AND date(g.release_date) <= date('now')
            ORDER BY g.release_date DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_watchlist(self, limit=20):
        """Get unreleased/coming-soon games with highest hype."""
        rows = self.conn.execute("""
            SELECT g.*, s.hype_score, s.follower_velocity_7d
            FROM games g
            JOIN game_scores s ON g.steam_app_id = s.steam_app_id
            WHERE s.classification = 'upcoming'
            ORDER BY s.hype_score DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_all_scores(self):
        """Get all game scores."""
        rows = self.conn.execute(
            "SELECT * FROM game_scores"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_published_content(self, content_type=None):
        """Get published content records."""
        if content_type:
            rows = self.conn.execute(
                "SELECT * FROM published_content WHERE content_type = ?",
                (content_type,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM published_content"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_market_stats(self):
        """Get aggregate market statistics."""
        stats = {}

        # Total games tracked
        row = self.conn.execute(
            "SELECT COUNT(*) as count FROM games"
        ).fetchone()
        stats["total_games"] = row["count"]

        # Genre distribution
        rows = self.conn.execute("SELECT genres FROM games").fetchall()
        genre_counts = {}
        for r in rows:
            try:
                genres = json.loads(r["genres"])
                for g in genres:
                    genre_counts[g] = genre_counts.get(g, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass
        stats["genre_distribution"] = genre_counts

        # Price distribution
        rows = self.conn.execute(
            "SELECT price_usd FROM games WHERE price_usd IS NOT NULL"
        ).fetchall()
        prices = [r["price_usd"] for r in rows]
        stats["price_distribution"] = self._bucket_prices(prices)

        # Average review score
        row = self.conn.execute("""
            SELECT AVG(review_percentage) as avg_score
            FROM game_snapshots WHERE review_percentage > 0
        """).fetchone()
        stats["avg_review_score"] = round(row["avg_score"] or 0, 1)

        # Games this week
        row = self.conn.execute("""
            SELECT COUNT(*) as count FROM games
            WHERE first_seen >= datetime('now', '-7 days')
        """).fetchone()
        stats["new_this_week"] = row["count"]

        return stats

    def _bucket_prices(self, prices):
        """Bucket prices into ranges for histogram."""
        buckets = {
            "Free": 0, "$0-$5": 0, "$5-$10": 0,
            "$10-$20": 0, "$20-$30": 0, "$30+": 0
        }
        for p in prices:
            if p == 0:
                buckets["Free"] += 1
            elif p <= 5:
                buckets["$0-$5"] += 1
            elif p <= 10:
                buckets["$5-$10"] += 1
            elif p <= 20:
                buckets["$10-$20"] += 1
            elif p <= 30:
                buckets["$20-$30"] += 1
            else:
                buckets["$30+"] += 1
        return buckets

    def close(self):
        """Close the database connection."""
        self.conn.close()
