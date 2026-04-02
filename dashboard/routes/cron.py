"""Cron jobs route at ``/cron``."""

import json
import os
import subprocess
from datetime import datetime

from flask import Blueprint, render_template, current_app

from helpers import (
    job_type,
    log_name_for_job,
    relative_time,
    time_until,
    format_duration,
    JOB_TYPE_COLORS,
)

bp = Blueprint("cron", __name__)


@bp.route("/cron")
def cron_jobs() -> str:
    """Render the cron-jobs status page with timeline and table."""
    status_file: str = current_app.config["CRON_STATUS_FILE"]
    cron_script: str = current_app.config["CRON_STATE_SCRIPT"]

    # Refresh cron status
    try:
        subprocess.run(
            ["python3", cron_script],
            timeout=15,
            capture_output=True,
        )
    except Exception:
        pass

    jobs: list[dict] = []
    exported_at: str = ""
    if os.path.exists(status_file):
        with open(status_file) as f:
            data = json.load(f)
            jobs = data.get("jobs", [])
            exported_at = data.get("exported_at", "")

    jobs.sort(key=lambda j: j.get("state", {}).get("nextRunAtMs", 0))

    ok_count = sum(1 for j in jobs if j.get("state", {}).get("lastStatus") == "ok")
    err_count = sum(1 for j in jobs if j.get("state", {}).get("lastStatus") == "error")
    idle_count = sum(1 for j in jobs if not j.get("state", {}).get("lastRunAtMs"))

    # Annotate each job for the template
    annotated: list[dict] = []
    today = datetime.utcnow().strftime("%Y-%m-%d")
    logs_dir: str = current_app.config["LOGS_DIR"]

    for j in jobs:
        jtype = job_type(j["name"])
        color = JOB_TYPE_COLORS.get(jtype, "var(--muted)")
        state = j.get("state", {})

        sched = j.get("schedule", {})
        if sched.get("kind") == "cron":
            sched_str = f'{sched.get("expr", "")} ({sched.get("tz", "UTC")})'
        elif sched.get("kind") == "at":
            sched_str = f'one-shot: {sched.get("at", "")[:16]}'
        else:
            sched_str = str(sched)

        next_str = time_until(state.get("nextRunAtMs"), state=state)
        last_str = relative_time(state.get("lastRunAtMs"))
        dur_str = format_duration(state.get("lastDurationMs"))

        status = state.get("lastStatus", "idle")
        errs = state.get("consecutiveErrors", 0)
        last_error = state.get("lastError", "unknown error")

        ln = log_name_for_job(j["name"])
        log_file = os.path.join(logs_dir, f"{ln}-{today}.log")
        has_log = os.path.exists(log_file)

        # Timeline position (hour-based)
        timeline_pct: float | None = None
        if sched.get("kind") == "cron":
            parts = sched.get("expr", "").split()
            if len(parts) >= 2:
                try:
                    hour = int(parts[1])
                    minute = int(parts[0])
                    timeline_pct = ((hour + minute / 60) / 24) * 100
                except ValueError:
                    pass

        annotated.append(
            {
                "name": j["name"],
                "jtype": jtype,
                "color": color,
                "sched_str": sched_str,
                "next_str": next_str,
                "last_str": last_str,
                "dur_str": dur_str,
                "status": status,
                "errs": errs,
                "last_error": last_error,
                "ln": ln,
                "today": today,
                "has_log": has_log,
                "timeline_pct": timeline_pct,
            }
        )

    return render_template(
        "cron.html",
        jobs=annotated,
        total_jobs=len(jobs),
        ok_count=ok_count,
        err_count=err_count,
        idle_count=idle_count,
        exported_at=exported_at[:19] if exported_at else "unknown",
        auto_refresh=True,
    )
