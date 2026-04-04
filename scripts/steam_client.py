"""Steam Store API client for fetching indie game data."""

import time
import logging
import requests

logger = logging.getLogger(__name__)

FEATURED_URL = "https://store.steampowered.com/api/featuredcategories/"
APP_DETAILS_URL = "https://store.steampowered.com/api/appdetails"
RATE_LIMIT_DELAY = 1.5  # seconds between requests

INDIE_TAG = "Indie"


class SteamClient:
    """Client for Steam Store API with rate limiting."""

    def __init__(self, rate_limit_delay=RATE_LIMIT_DELAY):
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time = 0.0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "IndieGameDrop/1.0"
        })

    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _get(self, url, params=None):
        """Make a rate-limited GET request."""
        self._rate_limit()
        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error("Request timed out: %s", url)
            return None
        except requests.exceptions.HTTPError as e:
            logger.error("HTTP error %s: %s", e.response.status_code, url)
            return None
        except requests.exceptions.RequestException as e:
            logger.error("Request failed: %s", e)
            return None
        except ValueError:
            logger.error("Invalid JSON response from: %s", url)
            return None

    def get_featured_indie_games(self):
        """Fetch featured indie games from Steam.

        Returns a list of app IDs that are tagged as Indie.
        """
        data = self._get(FEATURED_URL)
        if not data:
            return []

        app_ids = []
        # Look through featured categories for indie games
        for category_key in ["0", "1", "2", "3", "specials", "coming_soon",
                             "top_sellers", "new_releases"]:
            category = data.get(category_key)
            if not category:
                continue
            items = category.get("items", [])
            for item in items:
                app_id = item.get("id")
                if app_id:
                    app_ids.append(app_id)

        return list(set(app_ids))  # deduplicate

    def get_app_details(self, app_id):
        """Fetch detailed information for a specific app.

        Returns structured game data or None if not found/not indie.
        """
        data = self._get(APP_DETAILS_URL, params={"appids": str(app_id)})
        if not data:
            return None

        app_data = data.get(str(app_id), {})
        if not app_data.get("success"):
            return None

        details = app_data.get("data", {})
        if not details:
            return None

        # Check if it's an indie game
        genres = [g.get("description", "") for g in details.get("genres", [])]
        categories_list = details.get("categories", [])
        tags = genres  # Steam genres serve as tags

        is_indie = self._is_indie(details)

        # Extract price
        price_usd = 0.0
        price_data = details.get("price_overview")
        if price_data:
            price_usd = price_data.get("final", 0) / 100.0
        elif details.get("is_free"):
            price_usd = 0.0

        # Extract screenshots
        screenshots = [
            s.get("path_thumbnail", "")
            for s in details.get("screenshots", [])
        ]

        # Extract platforms
        platforms_data = details.get("platforms", {})
        platforms = []
        if platforms_data.get("windows"):
            platforms.append("windows")
        if platforms_data.get("mac"):
            platforms.append("mac")
        if platforms_data.get("linux"):
            platforms.append("linux")

        # Extract release date
        release_info = details.get("release_date", {})
        release_date = release_info.get("date", "")
        coming_soon = release_info.get("coming_soon", False)

        return {
            "steam_app_id": app_id,
            "name": details.get("name", ""),
            "developer": ", ".join(details.get("developers", [])),
            "publisher": ", ".join(details.get("publishers", [])),
            "release_date": release_date,
            "coming_soon": coming_soon,
            "price_usd": price_usd,
            "genres": genres,
            "tags": tags,
            "platforms": platforms,
            "short_description": details.get("short_description", ""),
            "header_image_url": details.get("header_image", ""),
            "screenshots": screenshots,
            "is_indie": is_indie,
            "type": details.get("type", "game"),
        }

    def _is_indie(self, details):
        """Check if a game has the Indie tag."""
        genres = [g.get("description", "") for g in details.get("genres", [])]
        if INDIE_TAG in genres:
            return True
        # Also check categories for indie-related tags
        for genre in genres:
            if "indie" in genre.lower():
                return True
        return False

    def get_indie_app_details(self, app_ids, max_games=50):
        """Fetch details for multiple apps, filtering to indie games only.

        Args:
            app_ids: List of Steam app IDs to check.
            max_games: Maximum number of games to return.

        Returns:
            List of game data dicts for indie games.
        """
        games = []
        for app_id in app_ids:
            if len(games) >= max_games:
                break
            details = self.get_app_details(app_id)
            if details and details.get("is_indie") and details.get("type") == "game":
                games.append(details)
                logger.info("Found indie game: %s", details.get("name"))
        return games
