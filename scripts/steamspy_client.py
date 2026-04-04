"""SteamSpy API client for enrichment data."""

import time
import logging
import requests

logger = logging.getLogger(__name__)

STEAMSPY_APP_URL = "https://steamspy.com/api.php"
RATE_LIMIT_DELAY = 1.0  # seconds between general requests
TAG_RATE_LIMIT_DELAY = 60.0  # seconds between tag queries


class SteamSpyClient:
    """Client for SteamSpy API with rate limiting."""

    def __init__(self, rate_limit_delay=RATE_LIMIT_DELAY,
                 tag_rate_limit_delay=TAG_RATE_LIMIT_DELAY):
        self.rate_limit_delay = rate_limit_delay
        self.tag_rate_limit_delay = tag_rate_limit_delay
        self._last_request_time = 0.0
        self._last_tag_request_time = 0.0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "IndieGameDrop/1.0"
        })

    def _rate_limit(self, is_tag_query=False):
        """Enforce rate limiting between requests."""
        if is_tag_query:
            elapsed = time.time() - self._last_tag_request_time
            if elapsed < self.tag_rate_limit_delay:
                time.sleep(self.tag_rate_limit_delay - elapsed)
            self._last_tag_request_time = time.time()
        else:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)
            self._last_request_time = time.time()

    def _get(self, params, is_tag_query=False):
        """Make a rate-limited GET request to SteamSpy."""
        self._rate_limit(is_tag_query=is_tag_query)
        try:
            response = self.session.get(
                STEAMSPY_APP_URL, params=params, timeout=15
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error("SteamSpy request timed out")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error("SteamSpy HTTP error: %s", e.response.status_code)
            return None
        except requests.exceptions.RequestException as e:
            logger.error("SteamSpy request failed: %s", e)
            return None
        except ValueError:
            logger.error("Invalid JSON from SteamSpy")
            return None

    def get_app_details(self, app_id):
        """Fetch enrichment data for a specific app.

        Returns dict with owner estimates, CCU, playtime data.
        """
        data = self._get({"request": "appdetails", "appid": str(app_id)})
        if not data:
            return self._empty_enrichment(app_id)

        return {
            "steam_app_id": app_id,
            "owners": self._parse_owner_range(data.get("owners", "0 .. 0")),
            "ccu": data.get("ccu", 0),
            "median_playtime": data.get("median_forever", 0),
            "average_playtime": data.get("average_forever", 0),
            "positive": data.get("positive", 0),
            "negative": data.get("negative", 0),
            "score_rank": data.get("score_rank", ""),
        }

    def get_indie_games_by_tag(self):
        """Fetch list of indie games from SteamSpy tag endpoint.

        Returns dict of {app_id: basic_data}.
        """
        data = self._get(
            {"request": "tag", "tag": "Indie"},
            is_tag_query=True
        )
        if not data:
            return {}

        result = {}
        for app_id_str, game_data in data.items():
            try:
                app_id = int(app_id_str)
            except (ValueError, TypeError):
                continue
            result[app_id] = {
                "name": game_data.get("name", ""),
                "positive": game_data.get("positive", 0),
                "negative": game_data.get("negative", 0),
                "owners": self._parse_owner_range(
                    game_data.get("owners", "0 .. 0")
                ),
            }
        return result

    def _parse_owner_range(self, owners_str):
        """Parse SteamSpy owner range string like '20,000 .. 50,000'.

        Returns the midpoint estimate as an integer.
        """
        if not owners_str or not isinstance(owners_str, str):
            return 0
        try:
            parts = owners_str.split("..")
            if len(parts) != 2:
                return 0
            low = int(parts[0].strip().replace(",", ""))
            high = int(parts[1].strip().replace(",", ""))
            return (low + high) // 2
        except (ValueError, IndexError):
            return 0

    def _empty_enrichment(self, app_id):
        """Return empty enrichment data when API fails."""
        return {
            "steam_app_id": app_id,
            "owners": 0,
            "ccu": 0,
            "median_playtime": 0,
            "average_playtime": 0,
            "positive": 0,
            "negative": 0,
            "score_rank": "",
        }

    def enrich_games(self, app_ids):
        """Fetch enrichment data for multiple apps.

        Args:
            app_ids: List of Steam app IDs.

        Returns:
            Dict mapping app_id to enrichment data.
        """
        enrichment = {}
        for app_id in app_ids:
            data = self.get_app_details(app_id)
            enrichment[app_id] = data
            logger.info("Enriched app %s", app_id)
        return enrichment
