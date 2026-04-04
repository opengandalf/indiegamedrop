"""Generate weekly roundup articles as Hugo markdown."""

import os
import logging
from datetime import datetime, date

from scripts.database import Database

logger = logging.getLogger(__name__)

CONTENT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "content", "posts"
)

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "indiegamedrop.db"
)


def generate_weekly_roundup(db_path=None, output_dir=None):
    """Generate a weekly roundup article.

    Creates a Hugo page bundle with proper frontmatter.
    """
    db = Database(db_path or DEFAULT_DB_PATH)
    out_dir = output_dir or CONTENT_DIR

    try:
        today = date.today()
        slug = f"weekly-roundup-{today.isoformat()}"
        article_dir = os.path.join(out_dir, slug)
        os.makedirs(article_dir, exist_ok=True)

        rising = db.get_top_rising(limit=5)
        gems = db.get_hidden_gems(limit=3)
        new_releases = db.get_new_releases(limit=5)
        stats = db.get_market_stats()

        frontmatter = _build_frontmatter(today, rising)
        body = _build_body(rising, gems, new_releases, stats)

        content = f"{frontmatter}\n{body}"
        filepath = os.path.join(article_dir, "index.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        # Record published content
        db.insert_published_content("weekly_roundup", slug=slug)

        logger.info("Generated weekly roundup: %s", slug)
        return filepath
    finally:
        db.close()


def _build_frontmatter(today, rising):
    """Build Hugo frontmatter for the article."""
    title = f"Weekly Roundup — {today.strftime('%d %B %Y')}"
    description = "This week's top indie game movers, new releases, and hidden gems."
    cover_image = ""
    if rising:
        cover_image = rising[0].get("header_image_url", "")

    frontmatter = f"""---
title: "{title}"
date: {today.isoformat()}
draft: false
type: "posts"
tags: ["weekly-roundup"]
description: "{description}"
"""
    if cover_image:
        frontmatter += f"""cover:
  image: "{cover_image}"
  alt: "This week's top rising indie game"
"""
    frontmatter += "---\n"
    return frontmatter


def _build_body(rising, gems, new_releases, stats):
    """Build the article markdown body."""
    sections = []

    # Intro
    sections.append(
        "Another week, another batch of indie games making moves. "
        "Here's what the data is telling us.\n"
    )

    # Rising section
    sections.append("## This Week's Fastest Rising\n")
    if rising:
        for game in rising:
            name = game.get("name", "Unknown")
            app_id = game.get("steam_app_id", "")
            header = game.get("header_image_url", "")
            score = game.get("rising_score", 0)
            sections.append(
                f"### {name}\n\n"
                f"![{name}]({header})\n\n"
                f"**Rising Score:** {score:.2f}\n"
            )
    else:
        sections.append("*No rising games this week.*\n")

    # Hidden gems
    sections.append("## Hidden Gems\n")
    if gems:
        for game in gems:
            name = game.get("name", "Unknown")
            header = game.get("header_image_url", "")
            gem_score = game.get("gem_score", 0)
            sections.append(
                f"### {name}\n\n"
                f"![{name}]({header})\n\n"
                f"**Gem Score:** {gem_score:.2f}\n"
            )
    else:
        sections.append("*No hidden gems found this week.*\n")

    # New releases
    sections.append("## New Releases Worth Watching\n")
    if new_releases:
        for game in new_releases:
            name = game.get("name", "Unknown")
            price = game.get("price_usd", 0)
            price_str = f"${price:.2f}" if price else "Free"
            sections.append(f"- **{name}** — {price_str}\n")
    else:
        sections.append("*No notable new releases this week.*\n")

    # Stats
    sections.append("## By the Numbers\n")
    total = stats.get("total_games", 0)
    new_week = stats.get("new_this_week", 0)
    avg_score = stats.get("avg_review_score", 0)
    sections.append(
        f"- **{total}** indie games tracked\n"
        f"- **{new_week}** new releases this week\n"
        f"- **{avg_score}%** average review score\n"
    )

    return "\n".join(sections)


def main():
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    generate_weekly_roundup()


if __name__ == "__main__":
    main()
