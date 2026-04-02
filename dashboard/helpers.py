"""Shared utility functions for the IndieGameDrop dashboard."""

from datetime import datetime
from markupsafe import escape, Markup
from typing import Optional, Union


def fmt(n: Optional[Union[int, float, str]]) -> str:
    """Format a number with commas, or return '—' for *None*.

    Args:
        n: A numeric value or *None*.

    Returns:
        Formatted string like ``1,234`` or ``—``.
    """
    if n is None:
        return "—"
    return f"{n:,.0f}" if isinstance(n, (int, float)) else str(n)


def esc(s: Optional[str]) -> Markup:
    """HTML-escape a string, returning '—' for *None*.

    Args:
        s: Raw text to escape.

    Returns:
        An escaped :class:`~markupsafe.Markup` instance.
    """
    if s is None:
        return Markup("—")
    return escape(str(s))


def relative_time(ms_timestamp: Optional[int]) -> str:
    """Convert a millisecond UTC timestamp to a human-friendly relative string.

    Args:
        ms_timestamp: Epoch milliseconds, or *None*.

    Returns:
        A string like ``5m ago``, ``2h ago``, or ``3d ago``.
    """
    if not ms_timestamp:
        return "never"
    dt = datetime.utcfromtimestamp(ms_timestamp / 1000)
    ago = datetime.utcnow() - dt
    secs = ago.total_seconds()
    if secs < 0:
        return "just now"
    if secs < 3600:
        return f"{int(secs / 60)}m ago"
    if secs < 86400:
        return f"{secs / 3600:.1f}h ago"
    return f"{ago.days}d ago"


def time_until(ms_timestamp: Optional[int], state: Optional[dict] = None) -> str:
    """Convert a millisecond UTC timestamp to a human-friendly countdown.

    When the next-run time is in the past, checks the job state to
    distinguish between a genuinely overdue job and one that already
    ran successfully (stale ``nextRunAtMs`` from cached cron state).

    Args:
        ms_timestamp: Epoch milliseconds, or *None*.
        state: Optional job state dict with lastStatus, lastRunAtMs.

    Returns:
        A string like ``in 5m``, ``in 2.3h``, ``overdue``, or
        ``ran OK — awaiting refresh``.
    """
    if not ms_timestamp:
        return "—"
    dt = datetime.utcfromtimestamp(ms_timestamp / 1000)
    diff = dt - datetime.utcnow()
    secs = diff.total_seconds()
    if secs < 0:
        # Check if the job already ran successfully
        if state:
            last_run = state.get("lastRunAtMs")
            last_status = state.get("lastStatus")
            if last_run and last_status == "ok":
                # It ran — the nextRunAtMs is just stale
                return "ran OK — awaiting refresh"
            elif last_run and last_status == "error":
                return "last run failed"
        return "overdue"
    if secs < 3600:
        return f"in {int(secs / 60)}m"
    return f"in {secs / 3600:.1f}h"


def format_duration(ms: Optional[int]) -> str:
    """Format a duration in milliseconds to a short string.

    Args:
        ms: Duration in milliseconds, or *None*.

    Returns:
        ``45s``, ``3.2m``, ``1.5h``, or ``—``.
    """
    if not ms:
        return "—"
    if ms < 60000:
        return f"{ms / 1000:.0f}s"
    if ms < 3600000:
        return f"{ms / 60000:.1f}m"
    return f"{ms / 3600000:.1f}h"


def job_type(name: str) -> str:
    """Detect the cron-job category from its name.

    Args:
        name: The human-readable job name.

    Returns:
        One of ``enrich``, ``discover``, ``snapshot``, ``export``,
        ``article``, or ``other``.
    """
    n = name.lower()
    if "enrich" in n:
        return "enrich"
    if "discover" in n or "gather" in n:
        return "discover"
    if "snapshot" in n or "score" in n:
        return "snapshot"
    if "export" in n or "deploy" in n:
        return "export"
    if "article" in n or "trend" in n:
        return "article"
    return "other"


def log_name_for_job(name: str) -> str:
    """Map a cron-job name to the log-file prefix.

    Args:
        name: The human-readable job name.

    Returns:
        A prefix like ``batch_enrich``, ``gather``, ``snapshot``,
        ``export``, or ``unknown``.
    """
    n = name.lower()
    if "enrich" in n:
        return "batch_enrich"
    if "discover" in n or "gather" in n:
        return "gather"
    if "snapshot" in n:
        return "snapshot"
    if "export" in n:
        return "export"
    return "unknown"


# Colour map for job-type chips (used in cron template).
JOB_TYPE_COLORS: dict[str, str] = {
    "enrich": "var(--accent)",
    "discover": "var(--success)",
    "snapshot": "var(--warn)",
    "export": "#9b59b6",
    "article": "#e74c3c",
    "other": "var(--muted)",
}
