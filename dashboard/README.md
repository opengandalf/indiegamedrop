# IndieGameDrop Dashboard

Internal monitoring dashboard for the IndieGameDrop data pipeline.  
Tracks game enrichment, snapshots, scoring, cron jobs, and logs.

## Quick Start

```bash
# Run the server
python dashboard/app.py
# → http://localhost:8790

# Run tests
pytest dashboard/tests/ -v

# Run with coverage
pytest dashboard/tests/ --cov=dashboard --cov-report=term-missing
```

## Architecture

```
dashboard/
├── app.py           # Flask app factory + entry point
├── config.py        # Paths, ports, constants
├── db.py            # SQLite connection context manager
├── queries.py       # All SQL queries as named constants
├── helpers.py       # Formatting utilities (fmt, esc, relative_time, …)
├── cron_state.py    # Exports cron status from OpenClaw CLI → JSON
├── routes/          # One Blueprint per page
│   ├── overview.py  # /
│   ├── enrichment.py# /enrichment
│   ├── snapshots.py # /snapshots
│   ├── games.py     # /games (paginated, filterable)
│   ├── scores.py    # /scores (leaderboards)
│   ├── cron.py      # /cron (job status + timeline)
│   └── logs.py      # /logs (file viewer)
├── templates/       # Jinja2 templates (base + one per page)
├── static/css/      # Extracted CSS
└── tests/           # pytest suite with in-memory DB fixtures
```

## Adding a New Page

1. Create `routes/newpage.py` with a Blueprint:
   ```python
   from flask import Blueprint, render_template
   bp = Blueprint("newpage", __name__)

   @bp.route("/newpage")
   def newpage():
       return render_template("newpage.html")
   ```

2. Create `templates/newpage.html` extending `base.html`:
   ```html
   {% extends "base.html" %}
   {% block title %}New Page{% endblock %}
   {% block content %}<h2>New Page</h2>{% endblock %}
   ```

3. Register the blueprint in `routes/__init__.py`:
   ```python
   from routes.newpage import bp as newpage_bp
   app.register_blueprint(newpage_bp)
   ```

4. Add a nav entry in `templates/base.html` (the `nav_items` list).

## Configuration

All paths are set in `config.py` and loaded into `flask.current_app.config`.  
The DB is opened read-only; the dashboard never writes to the database.

| Key                  | Default                              |
|----------------------|--------------------------------------|
| `DB_PATH`            | `../data/indiegamedrop.db`           |
| `LOGS_DIR`           | `../logs`                            |
| `CRON_STATUS_FILE`   | `./cron_status.json`                 |
| `PORT`               | `8790`                               |
| `AUTO_REFRESH_SECONDS` | `60`                               |

## Deployment

Runs as a launchd service pointing at `dashboard/app.py`.  
Host: `0.0.0.0:8790`.
