"""Tests for the snapshots route."""


def test_snapshots_returns_200(client):
    """GET /snapshots should return 200."""
    resp = client.get("/snapshots")
    assert resp.status_code == 200


def test_snapshots_shows_tier_counts(client):
    """Snapshots page should show tier breakdown."""
    data = client.get("/snapshots").data.decode()
    # Should show HOT, WARM, COOL, COLD tier labels
    assert "HOT Tier" in data
    assert "WARM Tier" in data


def test_snapshots_has_chart(client):
    """Snapshots page should include the daily chart canvas."""
    data = client.get("/snapshots").data.decode()
    assert "snapChart" in data
