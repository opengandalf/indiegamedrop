"""Enrichment route — enrichment progress at ``/enrichment``."""

from datetime import datetime, timedelta
from flask import Blueprint, render_template

from db import get_db
from helpers import fmt
import queries

bp = Blueprint("enrichment", __name__)


@bp.route("/enrichment")
def enrichment() -> str:
    """Render the enrichment progress page with a 30-day chart and recent table."""
    with get_db() as db:
        hist = db.execute(queries.ENRICHMENT_HISTORY, ("-30 days",)).fetchall()

        recent = db.execute(queries.RECENT_ENRICHMENTS, (100,)).fetchall()

        now = datetime.utcnow()
        h1 = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        h24 = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        rate_1h = db.execute(queries.ENRICHMENT_RATE, (h1,)).fetchone()[0]
        rate_24h = db.execute(queries.ENRICHMENT_RATE, (h24,)).fetchone()[0]

    return render_template(
        "enrichment.html",
        rate_1h=fmt(rate_1h),
        rate_24h=fmt(rate_24h),
        hist_labels=[r["d"] for r in hist],
        hist_data=[r["c"] for r in hist],
        recent=recent,
    )
