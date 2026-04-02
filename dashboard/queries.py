"""All SQL queries for the IndieGameDrop dashboard.

Each query is a module-level constant. Parameterised queries use ``?``
placeholders — callers supply values at execution time.
"""

from scripts.database import NSFW_FILTER_SQL

# ── Overview ──────────────────────────────────────────────────────────────

GAME_COUNT_TOTAL: str = "SELECT COUNT(*) FROM games"
GAME_COUNT_COMPLETE: str = "SELECT COUNT(*) FROM games WHERE detail_status='complete'"
GAME_COUNT_PENDING: str = "SELECT COUNT(*) FROM games WHERE detail_status='pending'"
GAME_COUNT_FAILED: str = "SELECT COUNT(*) FROM games WHERE detail_status='failed'"

SNAPSHOT_TODAY: str = "SELECT COUNT(*) FROM game_snapshots WHERE snapshot_date >= ?"

NEW_GAMES_TODAY: str = "SELECT COUNT(*) FROM games WHERE DATE(first_seen) = ?"

# ── Enrichment ────────────────────────────────────────────────────────────

ENRICHMENT_RATE: str = (
    "SELECT COUNT(*) FROM games "
    "WHERE detail_status='complete' AND last_updated >= ?"
)

ENRICHMENT_HISTORY: str = (
    "SELECT DATE(last_updated) as d, COUNT(*) as c "
    "FROM games WHERE detail_status='complete' AND last_updated >= DATE('now', ?) "
    "GROUP BY DATE(last_updated) ORDER BY d"
)

RECENT_ENRICHMENTS: str = (
    "SELECT name, steam_app_id, last_updated, developer, price_usd "
    "FROM games WHERE detail_status='complete' "
    "ORDER BY last_updated DESC LIMIT ?"
)

# ── Snapshots ─────────────────────────────────────────────────────────────

SNAPSHOT_TOTAL: str = "SELECT COUNT(*) FROM game_snapshots"

SNAPSHOT_HISTORY: str = (
    "SELECT DATE(snapshot_date) as d, COUNT(*) as c "
    "FROM game_snapshots WHERE snapshot_date >= DATE('now', ?) "
    "GROUP BY DATE(snapshot_date) ORDER BY d"
)

TIER_BREAKDOWN: str = (
    "SELECT refresh_tier, COUNT(*) as c FROM game_scores "
    "WHERE refresh_tier IS NOT NULL GROUP BY refresh_tier"
)

# ── Games browser ─────────────────────────────────────────────────────────

def games_search(where_sql: str) -> str:
    """Build a paginated game-search query with optional WHERE clause.

    Args:
        where_sql: A ``WHERE …`` clause (including the keyword) or empty string.

    Returns:
        SQL string expecting ``[…filter_params, per_page, offset]``.
    """
    nsfw_clause = f"AND {NSFW_FILTER_SQL}"
    if where_sql.strip():
        full_where = f"{where_sql} {nsfw_clause}"
    else:
        full_where = f"WHERE {NSFW_FILTER_SQL}"
    return (
        "SELECT g.name, g.steam_app_id, g.detail_status, "
        "COALESCE(g.price_usd, 0) as price, "
        "gs.gem_score, gs.classification, gs.refresh_tier, "
        "snap.snapshot_date as last_snap "
        "FROM games g "
        "LEFT JOIN game_scores gs ON g.steam_app_id = gs.steam_app_id "
        "LEFT JOIN ("
        "  SELECT steam_app_id, MAX(snapshot_date) as snapshot_date "
        "  FROM game_snapshots GROUP BY steam_app_id"
        ") snap ON g.steam_app_id = snap.steam_app_id "
        f"{full_where} "
        "ORDER BY g.last_updated DESC NULLS LAST "
        "LIMIT ? OFFSET ?"
    )


def games_count(where_sql: str) -> str:
    """Build a count query for the games browser.

    Args:
        where_sql: A ``WHERE …`` clause (including the keyword) or empty string.

    Returns:
        SQL string expecting the same filter params as :func:`games_search` (minus LIMIT/OFFSET).
    """
    if where_sql.strip():
        full_where = f"{where_sql} AND {NSFW_FILTER_SQL}"
    else:
        full_where = f"WHERE {NSFW_FILTER_SQL}"
    return f"SELECT COUNT(*) FROM games g {full_where}"

# ── Scores ────────────────────────────────────────────────────────────────

TOP_GEMS: str = (
    "SELECT g.name, g.steam_app_id, gs.gem_score, gs.classification, gs.refresh_tier "
    "FROM game_scores gs JOIN games g ON gs.steam_app_id = g.steam_app_id "
    f"WHERE gs.gem_score > 0 AND {NSFW_FILTER_SQL} ORDER BY gs.gem_score DESC LIMIT 50"
)

TOP_RISING: str = (
    "SELECT g.name, g.steam_app_id, gs.rising_score, gs.classification "
    "FROM game_scores gs JOIN games g ON gs.steam_app_id = g.steam_app_id "
    f"WHERE gs.rising_score > 0 AND {NSFW_FILTER_SQL} ORDER BY gs.rising_score DESC LIMIT 50"
)

TOP_HYPED: str = (
    "SELECT g.name, g.steam_app_id, gs.hype_score, gs.classification "
    "FROM game_scores gs JOIN games g ON gs.steam_app_id = g.steam_app_id "
    f"WHERE gs.hype_score > 0 AND {NSFW_FILTER_SQL} ORDER BY gs.hype_score DESC LIMIT 50"
)

SCORE_DISTRIBUTION: str = (
    "SELECT "
    "CASE WHEN gem_score >= 60 THEN '60+' WHEN gem_score >= 50 THEN '50-59' "
    "     WHEN gem_score >= 40 THEN '40-49' WHEN gem_score >= 30 THEN '30-39' "
    "     WHEN gem_score >= 20 THEN '20-29' WHEN gem_score >= 10 THEN '10-19' "
    "     ELSE '0-9' END as bucket, COUNT(*) as c "
    "FROM game_scores WHERE gem_score > 0 GROUP BY bucket ORDER BY bucket DESC"
)
