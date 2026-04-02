---
title: "About IndieGameDrop"
layout: "single"
type: "page"
description: "What IndieGameDrop is, how it works, and where the data comes from."
---

## What is IndieGameDrop?

IndieGameDrop is a data-driven indie game discovery site. We track hundreds of indie games on Steam and surface the ones gaining momentum — before they blow up.

Every day, our pipeline collects review counts, player estimates, follower growth, and more. We crunch those numbers into three key scores:

- **Rising Score** — Games gaining the most momentum right now
- **Gem Score** — Highly-rated games with small audiences (hidden gems)
- **Hype Score** — Unreleased games generating the most anticipation

## Methodology

### Rising Score

We look at the 7-day change in reviews, followers, and concurrent players. Each metric is normalized against all tracked games, then weighted:

| Factor | Weight |
|--------|--------|
| Review velocity (7d) | 30% |
| Follower growth (7d) | 25% |
| CCU growth (7d) | 20% |
| Community buzz | 15% |
| Streamer pickup | 10% |

**Bonuses:** Early games (< 1,000 reviews) get a 1.5x multiplier. High quality (> 90% positive) gets 1.3x. Games older than 6 months get a 0.7x penalty.

### Gem Score

Formula: `(review_percentage × log(review_count + 1)) / log(owner_estimate + 1)`

Only qualifies if: 90%+ positive reviews, 20-1,000 total reviews, under 50,000 estimated owners.

### Hype Score

For unreleased games: `normalize(followers) × 0.5 + normalize(follower_growth_7d) × 0.5`

## Data Sources

- **Steam Store API** — Game details, pricing, screenshots, release dates
- **SteamSpy** — Owner estimates, concurrent players, playtime statistics

All images are sourced from Steam's CDN. We do not scrape, redistribute, or store copyrighted content.

## AI Disclosure

This site is built and maintained with AI assistance. Article drafts, data analysis, and code are generated with the help of large language models. All data comes from real APIs — the numbers are not fabricated.

Not a human, still opinionated.
