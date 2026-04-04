"""Score calculator for IndieGameDrop games."""

import math
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def normalize(values):
    """Min-max normalize a list of values to 0-1 range.

    Returns list of normalized values. Empty list or all-same values return zeros.
    """
    if not values:
        return []
    min_val = min(values)
    max_val = max(values)
    if max_val == min_val:
        return [0.0] * len(values)
    return [(v - min_val) / (max_val - min_val) for v in values]


def normalize_single(value, all_values):
    """Normalize a single value against a list of all values.

    Returns the normalized value (0-1).
    """
    if not all_values:
        return 0.0
    min_val = min(all_values)
    max_val = max(all_values)
    if max_val == min_val:
        return 0.0
    return (value - min_val) / (max_val - min_val)


def calculate_rising_score(game_data, all_games_data):
    """Calculate rising score for a game.

    Args:
        game_data: Dict with review_velocity_7d, follower_velocity_7d,
                   ccu_growth_7d, review_count, review_percentage,
                   release_days_ago.
        all_games_data: List of similar dicts for all games (for normalization).

    Returns:
        Float rising score.
    """
    if not all_games_data:
        return 0.0

    # Collect all values for normalization
    all_review_vel = [g.get("review_velocity_7d", 0) for g in all_games_data]
    all_follower_vel = [g.get("follower_velocity_7d", 0) for g in all_games_data]
    all_ccu_growth = [g.get("ccu_growth_7d", 0) for g in all_games_data]

    # Normalize this game's values
    n_review_vel = normalize_single(
        game_data.get("review_velocity_7d", 0), all_review_vel
    )
    n_follower_vel = normalize_single(
        game_data.get("follower_velocity_7d", 0), all_follower_vel
    )
    n_ccu_growth = normalize_single(
        game_data.get("ccu_growth_7d", 0), all_ccu_growth
    )

    # Base score (reddit_mentions and streamer_pickup default to 0 for MVP)
    score = (
        n_review_vel * 0.30 +
        n_follower_vel * 0.25 +
        n_ccu_growth * 0.20 +
        0.0 * 0.15 +  # reddit_mentions placeholder
        0.0 * 0.10    # streamer_pickup placeholder
    )

    # Apply bonuses
    review_count = game_data.get("review_count", 0)
    review_percentage = game_data.get("review_percentage", 0)
    release_days_ago = game_data.get("release_days_ago", 0)

    if review_count < 1000:
        score *= 1.5  # catching early bonus
    if review_percentage > 90:
        score *= 1.3  # quality bonus
    if release_days_ago > 180:
        score *= 0.7  # older game penalty

    return round(score, 4)


def calculate_gem_score(review_percentage, review_count, owner_estimate):
    """Calculate hidden gem score.

    Only returns > 0 if:
    - review_percentage >= 90
    - 20 <= review_count <= 1000
    - owner_estimate < 50000

    Formula: (review_percentage * log(review_count + 1)) / log(owner_estimate + 1)
    """
    if review_percentage < 90:
        return 0.0
    if review_count < 20 or review_count > 1000:
        return 0.0
    if owner_estimate >= 50000:
        return 0.0

    # Avoid division by zero
    denominator = math.log(owner_estimate + 1)
    if denominator == 0:
        return 0.0

    score = (review_percentage * math.log(review_count + 1)) / denominator
    return round(score, 4)


def calculate_hype_score(follower_count, follower_velocity_7d,
                         all_follower_counts, all_velocities):
    """Calculate hype score for unreleased games.

    Formula: normalize(follower_count) * 0.5 + normalize(follower_velocity_7d) * 0.5
    """
    n_followers = normalize_single(follower_count, all_follower_counts)
    n_velocity = normalize_single(follower_velocity_7d, all_velocities)
    score = n_followers * 0.5 + n_velocity * 0.5
    return round(score, 4)


class Scorer:
    """Calculate and update scores for all games."""

    def __init__(self, db):
        self.db = db

    def calculate_all_scores(self):
        """Calculate scores for all games in the database."""
        games = self.db.get_all_games()
        if not games:
            logger.info("No games to score")
            return

        # Build game data with snapshots for scoring
        game_data_list = []
        for game in games:
            app_id = game["steam_app_id"]
            snapshots = self.db.get_snapshots(app_id, days=7)
            latest = snapshots[0] if snapshots else {}

            # Calculate velocities from snapshots
            review_velocity = self._calc_velocity(
                snapshots, "review_count"
            )
            follower_velocity = self._calc_velocity(
                snapshots, "follower_count"
            )
            ccu_growth = self._calc_velocity(
                snapshots, "ccu_estimate"
            )

            # Calculate release days ago
            release_days_ago = self._days_since_release(
                game.get("release_date", "")
            )

            # Determine if coming soon
            is_upcoming = release_days_ago < 0

            game_data_list.append({
                "steam_app_id": app_id,
                "review_velocity_7d": review_velocity,
                "follower_velocity_7d": follower_velocity,
                "ccu_growth_7d": ccu_growth,
                "review_count": latest.get("review_count", 0),
                "review_positive": latest.get("review_positive", 0),
                "review_percentage": latest.get("review_percentage", 0),
                "owner_estimate": latest.get("owner_estimate", 0),
                "follower_count": latest.get("follower_count", 0),
                "release_days_ago": release_days_ago,
                "is_upcoming": is_upcoming,
            })

        # Calculate scores for each game
        all_follower_counts = [
            g["follower_count"] for g in game_data_list
        ]
        all_velocities = [
            g["follower_velocity_7d"] for g in game_data_list
        ]

        for gd in game_data_list:
            rising = calculate_rising_score(gd, game_data_list)
            gem = calculate_gem_score(
                gd["review_percentage"],
                gd["review_count"],
                gd["owner_estimate"]
            )
            hype = calculate_hype_score(
                gd["follower_count"],
                gd["follower_velocity_7d"],
                all_follower_counts,
                all_velocities
            )

            # Classify the game
            if gd["is_upcoming"]:
                classification = "upcoming"
            elif gd["release_days_ago"] <= 14:
                classification = "new_release"
            elif gem > 0:
                classification = "hidden_gem"
            elif rising > 0.3:
                classification = "rising"
            else:
                classification = "tracked"

            scores = {
                "rising_score": rising,
                "gem_score": gem,
                "hype_score": hype,
                "review_velocity_7d": gd["review_velocity_7d"],
                "follower_velocity_7d": gd["follower_velocity_7d"],
                "ccu_growth_7d": gd["ccu_growth_7d"],
                "classification": classification,
            }
            self.db.update_scores(gd["steam_app_id"], scores)
            logger.info(
                "Scored %s: rising=%.3f gem=%.3f hype=%.3f [%s]",
                gd["steam_app_id"], rising, gem, hype, classification
            )

    def _calc_velocity(self, snapshots, field):
        """Calculate the change rate over available snapshots."""
        if len(snapshots) < 2:
            # MVP: with only one snapshot, estimate from review count
            if snapshots and field == "review_count":
                count = snapshots[0].get(field, 0)
                # Simulate velocity as a fraction of current count
                return count * 0.05
            return 0.0

        newest = snapshots[0].get(field, 0)
        oldest = snapshots[-1].get(field, 0)
        return max(0, newest - oldest)

    def _days_since_release(self, release_date_str):
        """Calculate days since release. Negative means upcoming."""
        if not release_date_str:
            return 0

        # Try common date formats
        for fmt in ["%d %b, %Y", "%b %d, %Y", "%Y-%m-%d", "%d %B, %Y"]:
            try:
                release_date = datetime.strptime(release_date_str, fmt)
                return (datetime.now() - release_date).days
            except ValueError:
                continue

        return 0
