"""Tests for the games route."""


def test_games_returns_200(client):
    """GET /games should return 200."""
    resp = client.get("/games")
    assert resp.status_code == 200


def test_games_shows_all(client):
    """Games page should show all 10 test games by default."""
    data = client.get("/games").data.decode()
    assert "10" in data  # total count
    assert "Game Alpha" in data


def test_games_pagination(client):
    """Games pagination should render page indicator."""
    data = client.get("/games?page=1").data.decode()
    assert "1 / 1" in data  # 10 games, 50 per page = 1 page


def test_games_filter_by_status(client):
    """Games page should filter by status."""
    data = client.get("/games?status=failed").data.decode()
    assert "Game Eta" in data
    assert "1" in data  # 1 failed game


def test_games_search(client):
    """Games page should filter by search query."""
    data = client.get("/games?q=Alpha").data.decode()
    assert "Game Alpha" in data
    # Other games should not appear
    assert "Game Kappa" not in data


def test_games_combined_filter(client):
    """Games page should support combined status + search filters."""
    data = client.get("/games?status=complete&q=Beta").data.decode()
    assert "Game Beta" in data
    assert "Game Delta" not in data
