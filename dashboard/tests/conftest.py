"""Shared pytest fixtures for the IndieGameDrop dashboard tests."""

import json
import os
import sqlite3
import tempfile
from typing import Generator

import pytest
from flask import Flask

# Ensure the dashboard package is importable
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture()
def db_path(tmp_path: os.PathLike) -> str:
    """Create an in-memory-style temp SQLite DB with sample data.

    Returns:
        Path to the temporary database file.
    """
    db_file = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE games (
            steam_app_id INTEGER PRIMARY KEY,
            name TEXT,
            detail_status TEXT,
            price_usd REAL,
            first_seen TEXT,
            last_updated TEXT,
            developer TEXT,
            publisher TEXT,
            genres TEXT,
            tags TEXT,
            release_date TEXT,
            header_image_url TEXT,
            short_description TEXT,
            about_the_game TEXT
        )
    """)

    c.execute("""
        CREATE TABLE game_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            steam_app_id INTEGER,
            snapshot_date TEXT,
            review_count INTEGER,
            review_positive INTEGER,
            review_percentage REAL,
            owner_estimate INTEGER,
            ccu_estimate INTEGER,
            follower_count INTEGER,
            price_usd REAL,
            discount_percent INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE game_scores (
            steam_app_id INTEGER PRIMARY KEY,
            rising_score REAL,
            gem_score REAL,
            hype_score REAL,
            classification TEXT,
            refresh_tier TEXT,
            last_calculated TEXT,
            last_refreshed TEXT,
            review_velocity_7d REAL,
            follower_velocity_7d REAL,
            ccu_growth_7d REAL
        )
    """)

    # Insert 10 games
    from datetime import datetime, timedelta
    today = datetime.utcnow().strftime("%Y-%m-%d")
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

    games = [
        (1, "Game Alpha", "complete", 9.99, today, yesterday, "DevA", "PubA"),
        (2, "Game Beta", "complete", 14.99, today, yesterday, "DevB", "PubB"),
        (3, "Game Gamma", "complete", 0.0, today, yesterday, "DevC", "PubC"),
        (4, "Game Delta", "pending", 19.99, today, None, "DevD", "PubD"),
        (5, "Game Epsilon", "pending", 4.99, today, None, "DevE", "PubE"),
        (6, "Game Zeta", "pending", 24.99, today, None, "DevF", "PubF"),
        (7, "Game Eta", "failed", 7.99, today, None, "DevG", "PubG"),
        (8, "Game Theta", "complete", 12.99, today, yesterday, "DevH", "PubH"),
        (9, "Game Iota", "complete", None, today, yesterday, "DevI", "PubI"),
        (10, "Game Kappa", "complete", 29.99, today, yesterday, "DevJ", "PubJ"),
    ]
    c.executemany(
        "INSERT INTO games (steam_app_id, name, detail_status, price_usd, first_seen, last_updated, developer, publisher) VALUES (?,?,?,?,?,?,?,?)",
        games,
    )

    # Insert 5 snapshots
    for i in range(1, 6):
        c.execute(
            "INSERT INTO game_snapshots (steam_app_id, snapshot_date, review_count, review_positive, review_percentage, owner_estimate, ccu_estimate, follower_count, price_usd, discount_percent) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (i, today, 100 * i, 80 * i, 80.0, 5000 * i, 50 * i, 200 * i, 9.99, 0),
        )

    # Insert 3 scores
    scores = [
        (1, 15.0, 45.5, 30.0, "hidden_gem", "hot"),
        (2, 25.0, 55.2, 10.0, "rising_star", "warm"),
        (3, 5.0, 12.0, 60.0, "hyped", "cool"),
    ]
    for s in scores:
        c.execute(
            "INSERT INTO game_scores (steam_app_id, rising_score, gem_score, hype_score, classification, refresh_tier) VALUES (?,?,?,?,?,?)",
            s,
        )

    conn.commit()
    conn.close()
    return db_file


@pytest.fixture()
def logs_dir(tmp_path: os.PathLike) -> str:
    """Create a temp logs directory with sample log files.

    Returns:
        Path to the temporary logs directory.
    """
    logs = tmp_path / "logs"
    logs.mkdir()

    from datetime import datetime
    today = datetime.utcnow().strftime("%Y-%m-%d")

    log_file = logs / f"batch_enrich-{today}.log"
    log_file.write_text(
        "[INFO] Starting batch enrich\n"
        "[INFO] Processing game 1\n"
        "[WARNING] Rate limit approaching\n"
        "=== Summary ===\n"
        "[ERROR] Game 42 failed to enrich\n"
        "[INFO] Completed 4/5 games\n"
    )

    log_file2 = logs / f"gather-{today}.log"
    log_file2.write_text("[INFO] Gathering new games\n[INFO] Found 10 new games\n")

    return str(logs)


@pytest.fixture()
def cron_status_file(tmp_path: os.PathLike) -> str:
    """Create a mock cron_status.json.

    Returns:
        Path to the mock cron status file.
    """
    from datetime import datetime
    import time

    now_ms = int(time.time() * 1000)
    data = {
        "jobs": [
            {
                "id": "test-1",
                "name": "IGD Batch Enrich (morning)",
                "schedule": {"kind": "cron", "expr": "0 8 * * *", "tz": "Europe/London"},
                "state": {
                    "nextRunAtMs": now_ms + 3600000,
                    "lastRunAtMs": now_ms - 1800000,
                    "lastDurationMs": 45000,
                    "lastStatus": "ok",
                    "consecutiveErrors": 0,
                },
            },
            {
                "id": "test-2",
                "name": "IGD Discover New Games",
                "schedule": {"kind": "cron", "expr": "30 6 * * *", "tz": "Europe/London"},
                "state": {
                    "nextRunAtMs": now_ms + 7200000,
                    "lastRunAtMs": now_ms - 86400000,
                    "lastDurationMs": 120000,
                    "lastStatus": "error",
                    "lastError": "Connection timeout",
                    "consecutiveErrors": 2,
                },
            },
            {
                "id": "test-3",
                "name": "IGD Daily Snapshot + Score",
                "schedule": {"kind": "cron", "expr": "0 12 * * *", "tz": "Europe/London"},
                "state": {},
            },
        ],
        "exported_at": datetime.utcnow().isoformat(),
    }

    path = str(tmp_path / "cron_status.json")
    with open(path, "w") as f:
        json.dump(data, f)
    return path


@pytest.fixture()
def app(db_path: str, logs_dir: str, cron_status_file: str) -> Flask:
    """Create a test Flask application with mock config.

    Returns:
        A configured Flask app.
    """
    from app import create_app

    test_app = create_app()
    test_app.config["DB_PATH"] = db_path
    test_app.config["LOGS_DIR"] = logs_dir
    test_app.config["CRON_STATUS_FILE"] = cron_status_file
    # Point cron script to a non-existent path so subprocess is a no-op
    test_app.config["CRON_STATE_SCRIPT"] = "/dev/null"
    test_app.config["TESTING"] = True

    return test_app


@pytest.fixture()
def client(app: Flask):
    """Create a Flask test client.

    Returns:
        A test client for making requests.
    """
    return app.test_client()
