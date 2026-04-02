"""Snapshots route — snapshot status at ``/snapshots``."""

from datetime import datetime
from flask import Blueprint, render_template

from db import get_db
from helpers import fmt
import queries

bp = Blueprint("snapshots", __name__)


@bp.route("/snapshots")
def snapshots() -> str:
    """Render the snapshot status page with tier breakdown and 14-day chart."""
    with get_db() as db:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        snaps_today = db.execute(queries.SNAPSHOT_TODAY, (today,)).fetchone()[0]
        total_snaps = db.execute(queries.SNAPSHOT_TOTAL).fetchone()[0]
        tiers = db.execute(queries.TIER_BREAKDOWN).fetchall()
        hist = db.execute(queries.SNAPSHOT_HISTORY, ("-14 days",)).fetchall()

    tier_map = {r["refresh_tier"]: r["c"] for r in tiers}

    return render_template(
        "snapshots.html",
        snaps_today=fmt(snaps_today),
        total_snaps=fmt(total_snaps),
        hot=fmt(tier_map.get("hot", 0)),
        warm=fmt(tier_map.get("warm", 0)),
        cool=fmt(tier_map.get("cool", 0)),
        cold=fmt(tier_map.get("cold", 0)),
        hist_labels=[r["d"] for r in hist],
        hist_data=[r["c"] for r in hist],
    )
