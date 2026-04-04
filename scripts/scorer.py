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
    Note: Prefer NormalizationBounds for batch scoring (avoids O(n²)).
    """
    if not all_values:
        return 0.0
    min_val = min(all_values)
    max_val = max(all_values)
    if max_val == min_val:
        return 0.0
    return (value - min_val) / (max_val - min_val)


class NormalizationBounds:
    """Pre-computed min/max bounds for normalization.
    
    Compute once, use for all games — avoids O(n²) in scoring.
    """

    def __init__(self, all_games_data):
        if not all_games_data:
            self.review_vel_min = self.review_vel_max = 0
            self.follower_vel_min = self.follower_vel_max = 0
            self.ccu_growth_min = self.ccu_growth_max = 0
            self.follower_min = self.follower_max = 0
            return

        review_vels = [g.get("review_velocity_7d", 0) for g in all_games_data]
        follower_vels = [g.get("follower_velocity_7d", 0) for g in all_games_data]
        ccu_growths = [g.get("ccu_growth_7d", 0) for g in all_games_data]
        followers = [g.get("follower_count", 0) for g in all_games_data]

        self.review_vel_min, self.review_vel_max = min(review_vels), max(review_vels)
        self.follower_vel_min, self.follower_vel_max = min(follower_vels), max(follower_vels)
        self.ccu_growth_min, self.ccu_growth_max = min(ccu_growths), max(ccu_growths)
        self.follower_min, self.follower_max = min(followers), max(followers)

    def normalize_review_vel(self, value):
        return _norm(value, self.review_vel_min, self.review_vel_max)

    def normalize_follower_vel(self, value):
        return _norm(value, self.follower_vel_min, self.follower_vel_max)

    def normalize_ccu_growth(self, value):
        return _norm(value, self.ccu_growth_min, self.ccu_growth_max)

    def normalize_follower_count(self, value):
        return _norm(value, self.follower_min, self.follower_max)


def _norm(value, min_val, max_val):
    """Normalize a value given pre-computed min/max."""
    if max_val == min_val:
        return 0.0
    return (value - min_val) / (max_val - min_val)


def calculate_rising_score(game_data, bounds):
    """Calculate rising score for a game.

    Args:
        game_data: Dict with review_velocity_7d, follower_velocity_7d,
                   ccu_growth_7d, review_count, review_percentage,
                   release_days_ago.
        bounds: NormalizationBounds instance (pre-computed from all games).

    Returns:
        Float rising score.
    """
    if bounds is None:
        return 0.0

    # Normalize using pre-computed bounds (O(1) per game)
    n_review_vel = bounds.normalize_review_vel(
        game_data.get("review_velocity_7d", 0)
    )
    n_follower_vel = bounds.normalize_follower_vel(
        game_data.get("follower_velocity_7d", 0)
    )
    n_ccu_growth = bounds.normalize_ccu_growth(
        game_data.get("ccu_growth_7d", 0)
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


def calculate_hype_score(follower_count, follower_velocity_7d, bounds):
    """Calculate hype score for unreleased games.

    Formula: normalize(follower_count) * 0.5 + normalize(follower_velocity_7d) * 0.5
    """
    if bounds is None:
        return 0.0
    n_followers = bounds.normalize_follower_count(follower_count)
    n_velocity = bounds.normalize_follower_vel(follower_velocity_7d)
    score = n_followers * 0.5 + n_velocity * 0.5
    return round(score, 4)


class Scorer:
    """Calculate and update scores for all games."""

    def __init__(self, db):
        self.db = db

    def calculate_all_scores(self):
        """Calculate scores for all games in the database.
        
        Optimized: pre-loads all snapshots in one query instead of
        82K individual queries, and pre-computes normalization bounds
        once instead of per-game (O(n) instead of O(n²)).
        """
        games = self.db.get_all_games()
        if not games:
            logger.info("No games to score")
            return

        # Batch-load latest snapshots for all games (1 query instead of 82K)
        latest_snapshots = self._batch_load_latest_snapshots()
        logger.info(
            "Loaded snapshots for %d games in batch", len(latest_snapshots)
        )

        # Build game data with snapshots for scoring
        game_data_list = []
        for game in games:
            app_id = game["steam_app_id"]
            latest = latest_snapshots.get(app_id, {})

            # With batch loading we only have the latest snapshot,
            # so velocity is estimated from single snapshot
            review_velocity = latest.get("review_count", 0) * 0.05
            follower_velocity = latest.get("follower_count", 0) * 0.05
            ccu_growth = latest.get("ccu_estimate", 0) * 0.05

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

        # Pre-compute normalization bounds ONCE — O(n) instead of O(n²)
        bounds = NormalizationBounds(game_data_list)
        logger.info(
            "Normalization bounds computed for %d games", len(game_data_list)
        )

        for gd in game_data_list:
            rising = calculate_rising_score(gd, bounds)
            gem = calculate_gem_score(
                gd["review_percentage"],
                gd["review_count"],
                gd["owner_estimate"]
            )
            hype = calculate_hype_score(
                gd["follower_count"],
                gd["follower_velocity_7d"],
                bounds
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
            "Scored %d games total", len(game_data_list)
        )

    def _batch_load_latest_snapshots(self):
        """Load the latest snapshot for each game in a single query.
        
        Returns dict mapping steam_app_id -> snapshot dict.
        """
        try:
            cursor = self.db.conn.execute("""
                SELECT gs.*
                FROM game_snapshots gs
                INNER JOIN (
                    SELECT steam_app_id, MAX(snapshot_date) as max_date
                    FROM game_snapshots
                    GROUP BY steam_app_id
                ) latest ON gs.steam_app_id = latest.steam_app_id
                           AND gs.snapshot_date = latest.max_date
            """)
            results = {}
            for row in cursor:
                results[row["steam_app_id"]] = dict(row)
            return results
        except Exception as e:
            logger.warning("Batch snapshot load failed: %s", e)
            return {}

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
