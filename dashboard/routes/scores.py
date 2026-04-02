"""Scores route — leaderboards at ``/scores``."""

from flask import Blueprint, render_template

from db import get_db
import queries

bp = Blueprint("scores", __name__)


@bp.route("/scores")
def scores() -> str:
    """Render top-gems, rising-stars, hyped, and score-distribution charts."""
    with get_db() as db:
        gems = db.execute(queries.TOP_GEMS).fetchall()
        rising = db.execute(queries.TOP_RISING).fetchall()
        hyped = db.execute(queries.TOP_HYPED).fetchall()
        dist = db.execute(queries.SCORE_DISTRIBUTION).fetchall()

    return render_template(
        "scores.html",
        gems=gems,
        rising=rising,
        hyped=hyped,
        dist_labels=[r["bucket"] for r in dist],
        dist_data=[r["c"] for r in dist],
    )
