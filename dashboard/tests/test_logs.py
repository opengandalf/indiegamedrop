"""Tests for the logs route."""

from datetime import datetime


def test_logs_returns_200(client):
    """GET /logs should return 200."""
    resp = client.get("/logs")
    assert resp.status_code == 200


def test_logs_shows_file_list(client):
    """Logs page should list available log files."""
    data = client.get("/logs").data.decode()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    assert f"batch_enrich-{today}.log" in data
    assert f"gather-{today}.log" in data


def test_logs_shows_content(client):
    """Logs page should show file content when name is specified."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    data = client.get(f"/logs?name=batch_enrich&date={today}").data.decode()
    assert "Starting batch enrich" in data
    assert "Game 42 failed" in data


def test_logs_color_codes_levels(client):
    """Log viewer should colour-code ERROR and WARNING lines."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    data = client.get(f"/logs?name=batch_enrich&date={today}").data.decode()
    assert "color:var(--danger)" in data  # ERROR lines
    assert "color:var(--warn)" in data    # WARNING lines
    assert "color:var(--accent)" in data  # === heading lines


def test_logs_missing_file(client):
    """Logs page should handle missing log files gracefully."""
    data = client.get("/logs?name=nonexistent&date=2020-01-01").data.decode()
    assert "No log file found" in data
