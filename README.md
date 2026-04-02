# IndieGameDrop

Data-driven indie game discovery. Finding the next big indie before everyone else.

## What Is This?

IndieGameDrop tracks indie games across Steam and SteamSpy, calculating momentum scores, identifying hidden gems, and surfacing the most promising new releases. The site is built as a Hugo static site with a Python data pipeline feeding it JSON data.

**Live site:** [https://opengandalf.github.io/indiegamedrop/](https://opengandalf.github.io/indiegamedrop/)

## Architecture

```
indiegamedrop/
├── scripts/                    # Python data pipeline
│   ├── steam_client.py         # Steam Store API client (search, details, reviews)
│   ├── steamspy_client.py      # SteamSpy API client (enrichment, tag discovery)
│   ├── database.py             # SQLite database (games, snapshots, scores, reviews)
│   ├── scorer.py               # Score calculation (rising, gem, hype)
│   ├── generate_data.py        # Pipeline orchestrator (gather, backfill, snapshot, score, export)
│   └── generate_article.py     # Weekly roundup article generator
├── tests/                      # Pytest test suite (202 tests, 91% coverage)
├── layouts/                    # Hugo templates (game profiles, rising, gems, etc.)
├── static/
│   ├── css/custom.css          # Dark theme styling
│   ├── js/                     # Client-side filtering, charts, sparklines
│   └── data/                   # Generated JSON files for the site
├── content/                    # Hugo content pages
├── data/                       # SQLite database (gitignored)
└── themes/PaperMod/            # Hugo theme (dark mode)
```

## Data Pipeline

### Commands

```bash
# Discover and store new indie games from Steam + SteamSpy
python3 -m scripts.generate_data gather

# One-time seed of ~500 games from search + 10 genre tags
python3 -m scripts.generate_data backfill

# Daily snapshot of all tracked games (priority-based)
python3 -m scripts.generate_data snapshot

# Recalculate all scores (rising, gem, hype)
python3 -m scripts.generate_data score

# Export JSON files for Hugo site
python3 -m scripts.generate_data export

# Run gather + score + export in sequence
python3 -m scripts.generate_data all
```

### Data Sources

- **Steam Store API** — Game metadata, descriptions, screenshots, review counts, trailers, metacritic data
- **Steam Review API** — Top helpful reviews with full text, author playtime, vote counts
- **SteamSpy API** — Owner estimates, concurrent users (CCU), playtime statistics

### Rate Limits

| Source | Limit |
|--------|-------|
| Steam Store API | 1 request / 1.5 seconds |
| Steam Review API | 1 request / 1.5 seconds |
| SteamSpy (general) | 1 request / 1 second |
| SteamSpy (tag queries) | 1 request / 60 seconds |

### Scoring Algorithms

**Rising Score** — Measures momentum:
- Review velocity (30%) + Follower velocity (25%) + CCU growth (20%)
- Bonuses: 1.5x for <1000 reviews, 1.3x for >90% positive, 0.7x for >180 days old

**Gem Score** — Hidden gems with high quality, small audience:
- Formula: `(review_pct * log(review_count + 1)) / log(owners + 1)`
- Criteria: 90%+ positive, 20-1000 reviews, <50k owners

**Hype Score** — Unreleased games with anticipation:
- Formula: `normalize(followers) * 0.5 + normalize(velocity) * 0.5`

### Database Schema

- **games** — Core game metadata + rich data (descriptions, metacritic, categories, trailers)
- **game_snapshots** — Daily time-series data (reviews, CCU, owners, playtime)
- **game_scores** — Calculated scores and classification
- **game_reviews** — Top Steam reviews with full text
- **published_content** — Record of generated content

### Priority Snapshot System

- **HIGH** — Games with rising_score > 0.3 or classified as rising/new_release
- **MEDIUM** — Games updated within the last 30 days
- **LOW** — Older tracked games

Reviews are refreshed weekly, not on every daily snapshot.

`get_games_needing_snapshot(today)` returns all three priority tiers at once, filtering out games already snapshotted for the given date.

## Frontend

The site uses PaperMod theme in dark mode with custom CSS.

### Pages

| Page | Data Source | Description |
|------|-----------|-------------|
| `/` | Multiple JSONs | Homepage with rising preview, gem spotlight, stats |
| `/rising/` | `rising.json` | Top 20 by rising score with filters |
| `/hidden-gems/` | `gems.json` | 90%+ review games with <1000 reviews |
| `/new-releases/` | `new_releases.json` | This week's indie releases |
| `/watchlist/` | `watchlist.json` | Unreleased games by hype score |
| `/data-explorer/` | `market_stats.json` | Genre and price distribution charts |
| `/game/?slug=X` | `games/{slug}.json` | Full game profile with charts, reviews, trailers |
| `/about/` | Static | Methodology, data sources, AI disclosure |

### Game Profile Features

- Header image, info bar (dev, release, price, platforms, review %)
- Metacritic badge (colour-coded by score)
- Category/feature badges (multiplayer, controller, etc.)
- Trailer video embed
- "About This Game" section (full HTML from Steam)
- Charts: review count, CCU, review % over time
- Top 5 Steam reviews with playtime, thumbs up/down, vote counts
- Screenshots gallery
- AI-generated analysis paragraph

## Development

### Setup

```bash
pip3 install -r requirements.txt
```

### Running Tests

```bash
# All tests
python3 -m pytest tests/ -v

# With coverage
python3 -m pytest tests/ --cov=scripts --cov-report=term-missing
```

### Building the Site

```bash
hugo --minify
```

### Deployment

Push to `main` triggers GitHub Actions to build Hugo and deploy to GitHub Pages.

## Tech Stack

- **Hugo** + PaperMod theme (static site generation)
- **Python 3** + requests (data pipeline)
- **SQLite** with WAL mode (database)
- **Chart.js** from CDN (charts)
- **GitHub Actions** (CI/CD)
- **GitHub Pages** (hosting)

## Data Integrity

- All images sourced exclusively from Steam CDN
- All HTTP requests mocked in tests (never hits real APIs)
- JSON exports validated via round-trip before writing
- Database uses UNIQUE constraints to prevent duplicate snapshots
- Graceful degradation when APIs are unavailable
