"""Tests for the overview route."""


def test_overview_returns_200(client):
    """GET / should return 200."""
    resp = client.get("/")
    assert resp.status_code == 200


def test_overview_shows_counts(client):
    """Overview should display correct game counts."""
    data = client.get("/").data.decode()
    # 10 total games
    assert "10" in data
    # 6 complete
    assert "6" in data  # complete count (games 1,2,3,8,9,10)
    # 3 pending
    assert "3" in data
    # 1 failed
    assert "1" in data


def test_overview_has_chart(client):
    """Overview should include the enrichment chart canvas."""
    data = client.get("/").data.decode()
    assert "enrichChart" in data


def test_overview_auto_refreshes(client):
    """Overview page should include meta refresh tag."""
    data = client.get("/").data.decode()
    assert 'http-equiv="refresh"' in data
