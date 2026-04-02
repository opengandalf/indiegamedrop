# IndieGameDrop Quality Checklist

Based on learnings from The Dice Drop project.

## Image Rules

- [x] All game images sourced from Steam CDN: `https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg`
- [x] Never use Bing, Google, or scraped image sources
- [x] All `<img>` tags have `onerror` fallback handlers
- [x] All images use `loading="lazy"` for performance
- [x] Screenshot URLs validated before storage in database

## Data Pipeline Rules

- [x] Steam API rate limited to 1 request per 1.5 seconds
- [x] SteamSpy API rate limited to 1 request per second (general)
- [x] SteamSpy tag queries rate limited to 1 request per 60 seconds
- [x] SteamSpy tag results cached to avoid redundant queries
- [x] All API responses validated before database insertion
- [x] Duplicate snapshots rejected via UNIQUE constraint
- [x] Graceful fallback when APIs are unavailable (empty data, not crashes)
- [x] JSON exports validated (round-trip through json.loads) before writing
- [x] Database uses WAL mode and foreign keys enabled
- [x] Schema migration handles adding new columns to existing databases
- [x] Multiple discovery sources: Steam search, featured, SteamSpy tags
- [x] Reviews fetched during backfill and weekly, not every daily snapshot

## Rich Data Rules

- [x] detailed_description and about_the_game captured from Steam
- [x] Metacritic score and URL captured when available
- [x] Categories (multiplayer, controller, workshop) captured as JSON
- [x] Trailer URL extracted from movies array
- [x] Supported languages stored
- [x] Total recommendations count stored
- [x] Top 5 reviews with full text stored in game_reviews table
- [x] Reviews include author playtime, vote counts, timestamps

## Scoring Rules

- [x] Rising score uses normalized values (min-max across all games)
- [x] Gem score only applies to games meeting all criteria (90%+ reviews, 20-1000 count, <50k owners)
- [x] Hype score only applies to unreleased games
- [x] Bonus multipliers applied correctly (1.5x early, 1.3x quality, 0.7x old)
- [x] Zero/missing values handled without crashes or NaN
- [x] Priority-based snapshot system (HIGH/MEDIUM/LOW)

## Content Rules

- [x] Tone: data-driven, opinionated but factual
- [x] All statistics sourced from real API data (no fabricated numbers)
- [x] AI involvement disclosed on About page
- [x] Game names and developer names match Steam exactly
- [x] Prices displayed in USD with 2 decimal places
- [x] Review percentages rounded to nearest integer for display

## Frontend Rules

- [x] All pages work with empty data (graceful empty states)
- [x] Filters work client-side (no server calls needed)
- [x] Chart.js loaded from CDN (no local copy)
- [x] Custom CSS uses CSS variables for theming consistency
- [x] All interactive elements work without JavaScript (progressive enhancement)
- [x] External links use `target="_blank" rel="noopener"`
- [x] Game profile shows About This Game section
- [x] Game profile shows top reviews with playtime and thumbs up/down
- [x] Game profile shows Metacritic badge (colour-coded) when available
- [x] Game profile shows trailer video embed when available
- [x] Game profile shows category/feature badges

## Pre-Deploy Checklist

- [x] `pytest --cov` passes with 90%+ coverage
- [x] `hugo --minify` builds without errors or warnings
- [x] All JSON files in `static/data/` are valid JSON
- [x] No API keys or secrets in committed files
- [x] `.gitignore` excludes database files and Python cache
- [x] GitHub Actions workflow configured for auto-deploy
- [x] Base URL in `config.toml` matches deployment target
- [x] `data/indiegamedrop.db` is gitignored
- [x] `static/data/*.json` is committed (not gitignored)

## Test Requirements

- [x] All HTTP requests mocked in tests (never hit real APIs)
- [x] Database tests use in-memory SQLite
- [x] Score calculations tested with known inputs and expected outputs
- [x] Edge cases covered: zero values, missing data, empty lists
- [x] JSON export format validated in tests
- [x] Article generation tested for frontmatter and content structure
- [x] New methods tested: search_indie_releases, get_top_reviews, get_top_by_tag
- [x] New DB methods tested: upsert_review, get_reviews, get_games_by_priority, get_games_needing_snapshot
- [x] Tag caching tested (cache hit avoids HTTP request)
- [x] Rich data fields tested in upsert and export
- [x] get_games_needing_snapshot returns priority-grouped games, excludes already-snapshotted
