"""Logs route at ``/logs``."""

import glob
import os
from datetime import datetime

from flask import Blueprint, render_template, request, current_app

bp = Blueprint("logs", __name__)


@bp.route("/logs")
def logs() -> str:
    """Render the pipeline logs page — file list and optional content viewer."""
    name: str = request.args.get("name", "")
    date: str = request.args.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
    lines_limit: int = int(request.args.get("lines", 200))

    logs_dir: str = current_app.config["LOGS_DIR"]
    os.makedirs(logs_dir, exist_ok=True)

    # Gather log file metadata
    all_logs = sorted(glob.glob(os.path.join(logs_dir, "*.log")), reverse=True)
    log_files: list[dict] = []
    for lf in all_logs[:50]:
        fname = os.path.basename(lf)
        size = os.path.getsize(lf)
        size_str = (
            f"{size / 1024:.1f} KB"
            if size < 1024 * 1024
            else f"{size / (1024 * 1024):.1f} MB"
        )
        mtime = datetime.fromtimestamp(os.path.getmtime(lf)).strftime("%Y-%m-%d %H:%M")
        parts = fname.rsplit("-", 3)
        if len(parts) >= 4:
            log_name = parts[0]
            log_date = "-".join(parts[1:]).replace(".log", "")
        else:
            log_name = fname.replace(".log", "")
            log_date = ""

        active = log_name == name and log_date == date
        log_files.append(
            {
                "fname": fname,
                "log_name": log_name,
                "log_date": log_date,
                "size_str": size_str,
                "mtime": mtime,
                "active": active,
            }
        )

    # Read selected log content
    content_lines: list[dict] = []
    total_lines: int = 0
    log_error: str = ""
    if name:
        log_file = os.path.join(logs_dir, f"{name}-{date}.log")
        if os.path.exists(log_file):
            try:
                with open(log_file, "r") as f:
                    all_lines = f.readlines()
                total_lines = len(all_lines)
                for line in all_lines[-lines_limit:]:
                    line = line.rstrip()
                    if "[ERROR]" in line:
                        level = "error"
                    elif "[WARNING]" in line:
                        level = "warning"
                    elif "===" in line:
                        level = "heading"
                    else:
                        level = "normal"
                    content_lines.append({"text": line, "level": level})
            except Exception as e:
                log_error = str(e)
        else:
            log_error = f"No log file found: {name}-{date}.log"

    return render_template(
        "logs.html",
        name=name,
        date=date,
        lines_limit=lines_limit,
        total_lines=total_lines,
        content_lines=content_lines,
        log_error=log_error,
        log_files=log_files,
    )
