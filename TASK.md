# IndieGameDrop — Build Task

Build a complete data-driven indie game discovery website. This is a Hugo static site with a Python data pipeline.

## What To Build

### 1. Hugo Static Site (Dark Theme)

Use Hugo with PaperMod theme, configured for DARK MODE.

**Color scheme:**
- Background: `#0d1117` (GitHub dark)
- Card background: `#161b22`
- Accent: `#58a6ff` (electric blue)
- Text: `#c9d1d9`
- Green for positive: `#3fb950`
- Red for negative: `#f85149`

**Pages to create:**

#### Homepage (`/`)
- Hero section: "Finding the next big indie before everyone else"
- "Today's Fastest Rising" — top 3 game cards with sparkline-style indicators
- "Just Dropped" — latest releases sidebar
- "Hidden Gem of the Day" — featured card
- "This Week in Numbers" — key stats bar
- Latest articles section
- Navigation: Rising | New Releases | Hidden Gems | Watchlist | Data | About

#### Rising Page (`/rising/`)
- Grid of top 20 fastest-rising indie games
- Each card: screenshot, name, review %, review count, 7-day change (↑XX%), genre tags
- Filters: genre dropdown, price range, release date
- Sort options: Rising Score, Review Velocity, Follower Growth
- Data loaded from `/data/rising.json`

#### Hidden Gems (`/hidden-gems/`)
- Grid of games with 90%+ reviews but <1000 total reviews
- Each card: screenshot, name, review %, review count, price, "hours per £" value indicator
- Filterable by genre, price
- Data loaded from `/data/gems.json`

#### New Releases (`/new-releases/`)
- This week's indie releases
- Each entry: screenshot, name, release date, review % (or "Too early"), price, genre tags, dev info
- Data loaded from `/data/new_releases.json`

#### Watchlist (`/watchlist/`)
- Unreleased games with highest follower counts / growth
- Each card: screenshot, name, expected release, follower count, 7-day follower growth
- Data loaded from `/data/watchlist.json`

#### Game Profile (`/game/`)
- Template page that loads individual game data
- Hero: header image, name, developer, release date, price, platforms, Steam link
- Charts section (Chart.js): review count over time, player count, follower growth
- "The Data Says" — analysis paragraph
- Screenshots gallery
- Similar games section
- Buy links section (placeholder for affiliates)

#### Data Explorer (`/data-explorer/`)
- Interactive page with Chart.js charts:
  - Genre popularity (bar chart)
  - New releases per week trend (line chart)
  - Average review scores trend (line chart)
  - Price distribution (histogram)
- Data loaded from `/data/market_stats.json`

#### About (`/about/`)
- What IndieGameDrop is
- Methodology explanation (how scores are calculated)
- Data sources credited
- "Not a human, still opinionated" AI disclosure

#### Weekly Roundup (Hugo content type)
- Article template for weekly roundup posts
- Archetype in `archetypes/weekly.md`

### 2. Python Data Pipeline (`scripts/`)

#### `scripts/steam_client.py`
- Fetch new indie releases from Steam Store API
  - Endpoint: `https://store.steampowered.com/api/featuredcategories/`
  - Also: `https://store.steampowered.com/api/appdetails?appids={appid}`
  - Filter by "Indie" tag
- Fetch app details: name, developer, publisher, release date, price, genres, tags, screenshots, header image, trailer URL
- Rate limiting: 1 request per 1.5 seconds
- Return structured data

#### `scripts/steamspy_client.py`
- Fetch enrichment data from SteamSpy API
  - Endpoint: `https://steamspy.com/api.php?request=appdetails&appid={appid}`
  - Also: `https://steamspy.com/api.php?request=tag&tag=Indie`
- Get: owner estimates, CCU, median playtime, average playtime
- Rate limiting: 1 request per second (general), 1 per 60 seconds (tag queries)

#### `scripts/database.py`
- SQLite database management
- Tables:
```sql
CREATE TABLE IF NOT EXISTS games (
    steam_app_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE,
    developer TEXT,
    publisher TEXT,
    release_date TEXT,
    price_usd REAL,
    genres TEXT,
    tags TEXT,
    platforms TEXT,
    short_description TEXT,
    header_image_url TEXT,
    screenshots TEXT,
    is_indie BOOLEAN DEFAULT 1,
    first_seen TEXT DEFAULT (datetime('now')),
    last_updated TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS game_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_app_id INTEGER NOT NULL,
    snapshot_date TEXT NOT NULL,
    review_count INTEGER DEFAULT 0,
    review_positive INTEGER DEFAULT 0,
    review_percentage REAL DEFAULT 0,
    owner_estimate INTEGER DEFAULT 0,
    ccu_estimate INTEGER DEFAULT 0,
    follower_count INTEGER DEFAULT 0,
    median_playtime_minutes INTEGER DEFAULT 0,
    price_usd REAL,
    discount_percent INTEGER DEFAULT 0,
    UNIQUE(steam_app_id, snapshot_date),
    FOREIGN KEY (steam_app_id) REFERENCES games(steam_app_id)
);

CREATE TABLE IF NOT EXISTS game_scores (
    steam_app_id INTEGER PRIMARY KEY,
    rising_score REAL DEFAULT 0,
    gem_score REAL DEFAULT 0,
    hype_score REAL DEFAULT 0,
    review_velocity_7d REAL DEFAULT 0,
    follower_velocity_7d REAL DEFAULT 0,
    ccu_growth_7d REAL DEFAULT 0,
    classification TEXT DEFAULT 'new_release',
    last_calculated TEXT,
    FOREIGN KEY (steam_app_id) REFERENCES games(steam_app_id)
);

CREATE TABLE IF NOT EXISTS published_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_type TEXT NOT NULL,
    steam_app_id INTEGER,
    slug TEXT,
    published_date TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (steam_app_id) REFERENCES games(steam_app_id)
);
```

#### `scripts/scorer.py`
- Calculate scores for all games based on snapshots:

```python
# Rising score (games gaining momentum)
rising_score = (
    normalize(review_velocity_7d) * 0.30 +
    normalize(follower_velocity_7d) * 0.25 +
    normalize(ccu_growth_7d) * 0.20 +
    normalize(reddit_mentions_7d) * 0.15 +
    normalize(streamer_pickup) * 0.10
)
# Bonuses:
# × 1.5 if review_count < 1000 (catching early)
# × 1.3 if review_percentage > 90 (quality)
# × 0.7 if release older than 180 days

# Hidden gem score
gem_score = (review_percentage * log(review_count + 1)) / log(owner_estimate + 1)
# Only if: review_percentage >= 90, 20 <= review_count <= 1000, owner_estimate < 50000

# Hype score (unreleased games)
hype_score = normalize(follower_count) * 0.5 + normalize(follower_velocity_7d) * 0.5
```

For MVP (before we have 7 days of snapshots), use simulated deltas or single-point scoring.

#### `scripts/generate_data.py`
- Main pipeline orchestrator
- Subcommands: `gather`, `snapshot`, `score`, `export`
- `gather`: Fetch new indie games from Steam, enrich with SteamSpy
- `snapshot`: Take daily snapshot of all tracked games
- `score`: Recalculate all scores
- `export`: Generate JSON files for Hugo:
  - `static/data/rising.json` — top 20 by rising_score
  - `static/data/gems.json` — hidden gems
  - `static/data/new_releases.json` — releases from last 7 days
  - `static/data/watchlist.json` — unreleased with highest hype
  - `static/data/market_stats.json` — aggregate stats
  - `static/data/games/{slug}.json` — individual game data for profile pages
- Each JSON includes all data needed for the frontend (no additional API calls)

#### `scripts/generate_article.py`
- Generate weekly roundup articles as Hugo markdown
- Uses data from the database
- Creates proper Hugo page bundles with frontmatter
- Includes game screenshots from Steam CDN
- Archetype: weekly roundup

### 3. Frontend JavaScript (`static/js/`)

#### `static/js/charts.js`
- Chart.js wrapper for game profile pages
- Renders: review count line chart, player count chart, follower growth chart
- Reads data from inline JSON or fetched from `/data/games/{slug}.json`

#### `static/js/filters.js`
- Client-side filtering for Rising, Gems, New Releases pages
- Genre dropdown filter
- Price range filter
- Sort selector
- Reads data from page-specific JSON, renders filtered cards

#### `static/js/sparkline.js`
- Tiny inline sparkline charts for game cards (7-day trend)
- Canvas-based, lightweight
- Shows review/follower trend direction

### 4. Tests (`tests/`)

**100% test coverage required.** Use pytest.

#### `tests/test_steam_client.py`
- Test API response parsing
- Test rate limiting
- Test error handling (API down, invalid appid, rate limited)
- Test indie tag filtering
- Mock all HTTP requests (use `responses` or `unittest.mock`)

#### `tests/test_steamspy_client.py`
- Test enrichment data parsing
- Test rate limiting
- Test fallback when SteamSpy is unavailable
- Mock all HTTP requests

#### `tests/test_database.py`
- Test table creation
- Test CRUD operations for all tables
- Test snapshot insertion and dedup (UNIQUE constraint)
- Test score updates
- Use in-memory SQLite for tests

#### `tests/test_scorer.py`
- Test rising_score calculation with known inputs
- Test gem_score calculation
- Test hype_score calculation
- Test bonus multipliers
- Test edge cases (zero values, missing data, new games with no history)
- Test normalization function

#### `tests/test_generate_data.py`
- Test JSON export format
- Test data pipeline orchestration
- Test each subcommand
- Mock database and API calls

#### `tests/test_generate_article.py`
- Test article frontmatter generation
- Test markdown output format
- Test Hugo page bundle creation

### 5. Configuration

#### `config.toml` (Hugo)
```toml
baseURL = "https://opengandalf.github.io/indiegamedrop/"
languageCode = "en-gb"
title = "IndieGameDrop"
theme = "PaperMod"

[params]
  defaultTheme = "dark"
  disableThemeToggle = true
  ShowShareButtons = false
  ShowReadingTime = true
  ShowBreadCrumbs = true
  description = "Data-driven indie game discovery. Finding the next big indie before everyone else."
  
[params.homeInfoParams]
  Title = "IndieGameDrop"
  Content = "Finding the next big indie before everyone else"

[menu]
  [[menu.main]]
    name = "Rising 📈"
    url = "/rising/"
    weight = 1
  [[menu.main]]
    name = "New Releases 🆕"
    url = "/new-releases/"
    weight = 2
  [[menu.main]]
    name = "Hidden Gems 💎"
    url = "/hidden-gems/"
    weight = 3
  [[menu.main]]
    name = "Watchlist 👁️"
    url = "/watchlist/"
    weight = 4
  [[menu.main]]
    name = "Data 📊"
    url = "/data-explorer/"
    weight = 5
  [[menu.main]]
    name = "About"
    url = "/about/"
    weight = 6
```

#### `.github/workflows/deploy.yml`
- Hugo build + deploy to GitHub Pages
- Trigger on push to main
- Use `peaceiris/actions-hugo` and `peaceiris/actions-gh-pages`

#### `requirements.txt`
```
requests>=2.31.0
pytest>=7.4.0
pytest-cov>=4.1.0
responses>=0.23.0
```

### 6. Quality Checklist (`CHECKLIST.md`)

Create a quality checklist based on learnings from The Dice Drop project. Include:
- Image rules (Steam CDN primary, validate URLs)
- Data pipeline rules (multiple sources, dedup, rate limiting)
- Content rules (tone, accuracy, attribution)
- Pre-deploy checklist
- Test requirements

### 7. Project Structure

```
indiegamedrop/
├── .github/workflows/deploy.yml
├── archetypes/
│   └── weekly.md
├── content/
│   ├── about/index.md
│   ├── rising/index.md
│   ├── new-releases/index.md
│   ├── hidden-gems/index.md
│   ├── watchlist/index.md
│   ├── data-explorer/index.md
│   └── game/index.md
├── data/                          # SQLite DB (gitignored)
├── layouts/
│   ├── _default/
│   ├── partials/
│   │   ├── game-card.html
│   │   ├── sparkline.html
│   │   └── stats-bar.html
│   ├── rising/single.html
│   ├── new-releases/single.html
│   ├── hidden-gems/single.html
│   ├── watchlist/single.html
│   ├── data-explorer/single.html
│   └── game/single.html
├── scripts/
│   ├── steam_client.py
│   ├── steamspy_client.py
│   ├── database.py
│   ├── scorer.py
│   ├── generate_data.py
│   └── generate_article.py
├── static/
│   ├── css/
│   │   └── custom.css
│   ├── data/                      # Generated JSON files
│   │   ├── rising.json
│   │   ├── gems.json
│   │   ├── new_releases.json
│   │   ├── watchlist.json
│   │   ├── market_stats.json
│   │   └── games/                 # Per-game JSON
│   └── js/
│       ├── charts.js
│       ├── filters.js
│       └── sparkline.js
├── tests/
│   ├── conftest.py
│   ├── test_steam_client.py
│   ├── test_steamspy_client.py
│   ├── test_database.py
│   ├── test_scorer.py
│   ├── test_generate_data.py
│   └── test_generate_article.py
├── themes/PaperMod/               # Git submodule
├── .gitignore
├── CHECKLIST.md
├── README.md
├── config.toml
└── requirements.txt
```

### 8. Initial Data Seeding

After building everything, run the data pipeline to seed initial data:
```bash
pip install -r requirements.txt
python scripts/generate_data.py gather    # Fetch games from Steam
python scripts/generate_data.py snapshot  # Take initial snapshot
python scripts/generate_data.py score     # Calculate scores
python scripts/generate_data.py export    # Generate JSON for Hugo
```

Then build and verify:
```bash
hugo --minify
# Check that all pages render correctly
```

### 9. Deploy

1. Commit everything
2. Push to GitHub
3. GitHub Actions builds Hugo and deploys to Pages
4. Verify the site is live at https://opengandalf.github.io/indiegamedrop/

## CRITICAL RULES (from The Dice Drop learnings)

1. **Steam CDN for all images** — `https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg` — NEVER use Bing
2. **Rate limit all API calls** — Steam: 1 req/1.5s, SteamSpy: 1 req/s
3. **Mock all HTTP in tests** — never hit real APIs in tests
4. **Every page must work with empty data** — graceful empty states, not crashes
5. **All JSON must be valid** — validate before writing
6. **Git commit after each major milestone** — don't batch everything into one commit
7. **Tests must pass before final commit** — run `pytest --cov` and verify coverage
8. **Hugo must build without errors** — run `hugo --minify` and check

## Git Workflow
- Create a feature branch `feat/initial-build`
- Make commits as you go (not one giant commit)
- When complete, merge to main
- Push to trigger GitHub Pages deploy

When completely finished, run this command to notify me:
openclaw system event --text "Done: IndieGameDrop website built and deployed to GitHub Pages. All tests passing." --mode now
