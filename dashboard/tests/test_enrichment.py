"""Tests for the enrichment route."""


def test_enrichment_returns_200(client):
    """GET /enrichment should return 200."""
    resp = client.get("/enrichment")
    assert resp.status_code == 200


def test_enrichment_shows_recent_games(client):
    """Enrichment page should list recently enriched games."""
    data = client.get("/enrichment").data.decode()
    assert "Game Alpha" in data
    assert "Game Beta" in data


def test_enrichment_has_chart(client):
    """Enrichment page should include the daily chart canvas."""
    data = client.get("/enrichment").data.decode()
    assert "enrichDaily" in data
