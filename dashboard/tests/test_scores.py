"""Tests for the scores route."""


def test_scores_returns_200(client):
    """GET /scores should return 200."""
    resp = client.get("/scores")
    assert resp.status_code == 200


def test_scores_shows_gems(client):
    """Scores page should list top gems."""
    data = client.get("/scores").data.decode()
    assert "Top Hidden Gems" in data
    assert "Game Beta" in data  # highest gem_score (55.2)


def test_scores_shows_rising(client):
    """Scores page should show rising stars when data exists."""
    data = client.get("/scores").data.decode()
    assert "Rising Stars" in data


def test_scores_shows_hyped(client):
    """Scores page should show hyped games when data exists."""
    data = client.get("/scores").data.decode()
    assert "Most Hyped" in data


def test_scores_hides_empty_sections(app):
    """Scores page should hide sections with no data."""
    import sqlite3
    # Remove all rising scores
    conn = sqlite3.connect(app.config["DB_PATH"])
    conn.execute("UPDATE game_scores SET rising_score = 0")
    conn.execute("UPDATE game_scores SET hype_score = 0")
    conn.commit()
    conn.close()

    with app.test_client() as client:
        data = client.get("/scores").data.decode()
        assert "Rising Stars" not in data
        assert "Most Hyped" not in data


def test_scores_has_distribution_chart(client):
    """Scores page should include the distribution chart."""
    data = client.get("/scores").data.decode()
    assert "distChart" in data
