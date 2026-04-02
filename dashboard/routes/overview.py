"""Overview route — pipeline summary at ``/``."""

from datetime import datetime, timedelta
from flask import Blueprint, render_template

from db import get_db
from helpers import fmt
import queries

bp = Blueprint("overview", __name__)


@bp.route("/")
def overview() -> str:
    """Render the pipeline overview page with key metrics and a 7-day chart."""
    with get_db() as db:
        total = db.execute(queries.GAME_COUNT_TOTAL).fetchone()[0]
        complete = db.execute(queries.GAME_COUNT_COMPLETE).fetchone()[0]
        pending = db.execute(queries.GAME_COUNT_PENDING).fetchone()[0]
        failed = db.execute(queries.GAME_COUNT_FAILED).fetchone()[0]

        today = datetime.utcnow().strftime("%Y-%m-%d")
        snaps_today = db.execute(queries.SNAPSHOT_TODAY, (today,)).fetchone()[0]
        new_today = db.execute(queries.NEW_GAMES_TODAY, (today,)).fetchone()[0]

        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        enriched_24h = db.execute(queries.ENRICHMENT_RATE, (yesterday,)).fetchone()[0]

        hist = db.execute(queries.ENRICHMENT_HISTORY, ("-7 days",)).fetchall()

    pct = (complete / (complete + pending) * 100) if (complete + pending) > 0 else 0
    rate_per_day = enriched_24h if enriched_24h > 0 else 1
    est_days = pending / rate_per_day if rate_per_day > 0 else 999

    return render_template(
        "overview.html",
        total=fmt(total),
        complete=fmt(complete),
        pending=fmt(pending),
        failed=fmt(failed),
        snaps_today=fmt(snaps_today),
        new_today=fmt(new_today),
        pct=pct,
        enriched_24h=fmt(enriched_24h),
        rate_per_day=fmt(rate_per_day),
        est_days=f"{est_days:.0f}",
        hist_labels=[r["d"] for r in hist],
        hist_data=[r["c"] for r in hist],
        auto_refresh=True,
    )
