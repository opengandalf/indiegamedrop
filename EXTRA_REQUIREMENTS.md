# EXTRA REQUIREMENTS — Read This!

## Richer Game Data

The user wants as much data about each game as possible. Update the pipeline to capture:

### From Steam appdetails API (already partially captured):
- `detailed_description` — full HTML description (store as-is, strip HTML for display)
- `about_the_game` — the "about this game" section
- `supported_languages` — language support
- `metacritic` — score and URL if available
- `categories` — multiplayer, controller support, workshop, etc.
- `movies` — trailer URLs (for future GIF extraction)
- `content_descriptors` — maturity ratings
- `recommendations` — total number of recommendations

### NEW: Top Reviews from Steam Review API
Add a method `get_top_reviews(app_id, count=5)` to steam_client.py:
- Endpoint: `https://store.steampowered.com/appreviews/{app_id}?json=1&filter=updated&language=english&num_per_page=5&purchase_type=all`
- Fetch the top 5 most helpful reviews
- For each review capture: author_steamid, voted_up (bool), votes_up, playtime_at_review, review text, timestamp_created
- Store in a new `game_reviews` table:
```sql
CREATE TABLE IF NOT EXISTS game_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_app_id INTEGER NOT NULL,
    review_id TEXT,
    author_steamid TEXT,
    voted_up BOOLEAN,
    votes_up INTEGER DEFAULT 0,
    playtime_at_review INTEGER DEFAULT 0,
    review_text TEXT,
    timestamp_created INTEGER,
    fetched_date TEXT DEFAULT (datetime('now')),
    UNIQUE(steam_app_id, review_id),
    FOREIGN KEY (steam_app_id) REFERENCES games(steam_app_id)
);
```
- Include top reviews in the game profile JSON export
- Refresh reviews weekly (not daily — they don't change fast)

### Update the games table schema
Add columns to the games table:
- `detailed_description TEXT`
- `about_the_game TEXT`  
- `supported_languages TEXT`
- `metacritic_score INTEGER`
- `metacritic_url TEXT`
- `categories TEXT` (JSON array)
- `trailer_url TEXT`
- `total_recommendations INTEGER`

### Update game profile JSON export
The `/data/games/{slug}.json` files should include ALL of this data so the game profile pages are rich and detailed.

### Display on Game Profile Page
Update `layouts/game/single.html` to show:
- Full "About This Game" section
- Top reviews (with playtime, thumbs up/down, vote count)
- Metacritic score badge if available
- Trailer embed if available
- Categories/features badges (multiplayer, controller, etc.)

## IMPORTANT
- Rate limit review fetches (1.5s between calls, same as other Steam API)
- Only fetch reviews during backfill and weekly refresh, not every daily snapshot
- Store review text — it's valuable for future AI analysis
- Add tests for all new functionality
- Update existing tests if schema changes break them
