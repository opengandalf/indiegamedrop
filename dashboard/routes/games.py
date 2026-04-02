"""Games browser route at ``/games``."""

from flask import Blueprint, render_template, request, current_app

from db import get_db
from helpers import fmt
import queries

bp = Blueprint("games", __name__)


@bp.route("/games")
def games() -> str:
    """Render a paginated, filterable games table."""
    page_num: int = int(request.args.get("page", 1))
    status: str = request.args.get("status", "")
    search: str = request.args.get("q", "")
    per_page: int = current_app.config.get("PER_PAGE", 50)
    offset: int = (page_num - 1) * per_page

    where_parts: list[str] = []
    params: list[str] = []
    if status:
        where_parts.append("g.detail_status = ?")
        params.append(status)
    if search:
        where_parts.append("g.name LIKE ?")
        params.append(f"%{search}%")
    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    with get_db() as db:
        total = db.execute(queries.games_count(where_sql), params).fetchone()[0]
        rows = db.execute(
            queries.games_search(where_sql), params + [per_page, offset]
        ).fetchall()

    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        "games.html",
        rows=rows,
        total=fmt(total),
        page_num=page_num,
        total_pages=total_pages,
        status=status,
        search=search,
    )
