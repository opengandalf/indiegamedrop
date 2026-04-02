"""Tests for the cron route."""


def test_cron_returns_200(client):
    """GET /cron should return 200."""
    resp = client.get("/cron")
    assert resp.status_code == 200


def test_cron_shows_job_names(client):
    """Cron page should display job names from mock data."""
    data = client.get("/cron").data.decode()
    assert "IGD Batch Enrich (morning)" in data
    assert "IGD Discover New Games" in data


def test_cron_shows_status_chips(client):
    """Cron page should show OK and ERROR status chips."""
    data = client.get("/cron").data.decode()
    assert "✓ OK" in data
    assert "✗ ERROR" in data


def test_cron_shows_timeline(client):
    """Cron page should include the timeline visualization."""
    data = client.get("/cron").data.decode()
    assert "Daily Timeline" in data


def test_cron_auto_refreshes(client):
    """Cron page should include meta refresh tag."""
    data = client.get("/cron").data.decode()
    assert 'http-equiv="refresh"' in data
