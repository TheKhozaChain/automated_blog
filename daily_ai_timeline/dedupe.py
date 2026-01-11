"""Deduplication and scoring for daily_ai_timeline.

Handles:
- URL normalization and deduplication
- Fuzzy title matching to detect duplicate stories
- Scoring items by recency, source credibility, and content signals
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Optional

from .config import SCORING_KEYWORDS, SOURCE_CREDIBILITY
from .ingest import NewsItem
from .utils import extract_numbers, hours_since, normalize_url

logger = logging.getLogger(__name__)

# Similarity threshold for fuzzy title matching (0.0 to 1.0)
TITLE_SIMILARITY_THRESHOLD = 0.85


def title_similarity(title1: str, title2: str) -> float:
    """Calculate similarity ratio between two titles.

    Args:
        title1: First title string
        title2: Second title string

    Returns:
        Similarity ratio between 0.0 and 1.0
    """
    # Normalize titles for comparison
    t1 = title1.lower().strip()
    t2 = title2.lower().strip()

    # Use SequenceMatcher for fuzzy matching
    return SequenceMatcher(None, t1, t2).ratio()


def deduplicate_items(
    items: list[NewsItem],
    similarity_threshold: float = TITLE_SIMILARITY_THRESHOLD,
) -> list[NewsItem]:
    """Remove duplicate items based on URL and title similarity.

    Args:
        items: List of NewsItem objects
        similarity_threshold: Minimum similarity ratio to consider duplicates

    Returns:
        Deduplicated list of NewsItem objects
    """
    if not items:
        return []

    # First pass: URL deduplication
    seen_urls = set()
    url_unique = []

    for item in items:
        normalized = normalize_url(item.url)
        if normalized not in seen_urls:
            seen_urls.add(normalized)
            url_unique.append(item)

    logger.debug(f"After URL dedup: {len(url_unique)} items (removed {len(items) - len(url_unique)})")

    # Second pass: Title similarity deduplication
    # Keep items with higher credibility when duplicates are found
    deduplicated = []

    for item in url_unique:
        is_duplicate = False

        for existing in deduplicated:
            similarity = title_similarity(item.title, existing.title)

            if similarity >= similarity_threshold:
                is_duplicate = True
                # Keep the one with higher source credibility
                item_cred = SOURCE_CREDIBILITY.get(item.source, 5)
                existing_cred = SOURCE_CREDIBILITY.get(existing.source, 5)

                if item_cred > existing_cred:
                    # Replace existing with this item
                    deduplicated.remove(existing)
                    deduplicated.append(item)
                    logger.debug(
                        f"Replaced '{existing.title[:50]}' ({existing.source}) "
                        f"with '{item.title[:50]}' ({item.source})"
                    )
                break

        if not is_duplicate:
            deduplicated.append(item)

    logger.info(
        f"Deduplication complete: {len(items)} -> {len(deduplicated)} items "
        f"({len(items) - len(deduplicated)} duplicates removed)"
    )

    return deduplicated


def score_item(
    item: NewsItem,
    reference_time: datetime | None = None,
    lookback_hours: int = 24,
) -> float:
    """Calculate a relevance score for a news item.

    Scoring factors:
    - Recency (0-30 points): More recent items score higher
    - Source credibility (0-20 points): Based on source reputation
    - Numbers present (0-10 points): Items with metrics/data score higher
    - Keywords (0-15 points): High-value keywords increase score

    Args:
        item: The NewsItem to score
        reference_time: Reference time for recency calculation (default: now)
        lookback_hours: The lookback window in hours (24 for daily, 168 for weekly)
            Used to scale recency scoring appropriately

    Returns:
        Numerical score (higher is better)
    """
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)

    score = 0.0

    # Recency score (0-30 points)
    # Scale based on lookback window so items are scored fairly across the period
    # For daily (24h): items lose ~1.25 points per hour
    # For weekly (168h): items lose ~0.18 points per hour
    hours_old = hours_since(item.published, reference_time)
    recency_score = max(0, 30 * (1 - hours_old / lookback_hours))
    score += recency_score

    # Source credibility score (0-20 points)
    credibility_score = SOURCE_CREDIBILITY.get(item.source, 5)
    score += credibility_score

    # Numbers present score (0-10 points)
    # Items with specific metrics/dates are often more newsworthy
    text_to_check = f"{item.title} {item.summary}"
    numbers = extract_numbers(text_to_check)
    if numbers:
        score += min(10, len(numbers) * 3)

    # Keyword score (0-15 points)
    # High-value keywords indicate significant news
    title_lower = item.title.lower()
    summary_lower = item.summary.lower()
    combined = f"{title_lower} {summary_lower}"

    keyword_matches = sum(
        1 for kw in SCORING_KEYWORDS if kw.lower() in combined
    )
    score += min(15, keyword_matches * 3)

    return score


def score_and_rank_items(
    items: list[NewsItem],
    top_n: int = 10,
    lookback_hours: int = 24,
) -> list[NewsItem]:
    """Score all items and return the top N ranked by score.

    Args:
        items: List of NewsItem objects to score
        top_n: Number of top items to return
        lookback_hours: The lookback window in hours for recency scoring

    Returns:
        List of top N NewsItem objects, sorted by score (descending)
    """
    reference_time = datetime.now(timezone.utc)

    # Score each item
    for item in items:
        item.score = score_item(item, reference_time, lookback_hours)

    # Sort by score (descending) and take top N
    sorted_items = sorted(items, key=lambda x: x.score, reverse=True)
    top_items = sorted_items[:top_n]

    logger.info(
        f"Ranked {len(items)} items, selected top {len(top_items)} "
        f"(score range: {top_items[-1].score:.1f} - {top_items[0].score:.1f})"
    )

    return top_items


def process_items(
    items: list[NewsItem],
    top_n: int = 10,
    similarity_threshold: float = TITLE_SIMILARITY_THRESHOLD,
    lookback_hours: int = 24,
) -> list[NewsItem]:
    """Full processing pipeline: deduplicate, score, and rank items.

    Args:
        items: Raw list of NewsItem objects
        top_n: Number of top items to return
        similarity_threshold: Title similarity threshold for deduplication
        lookback_hours: The lookback window in hours for recency scoring
            (24 for daily, 168 for weekly)

    Returns:
        List of top N deduplicated and scored NewsItem objects
    """
    logger.info(f"Processing {len(items)} items...")

    # Step 1: Deduplicate
    unique_items = deduplicate_items(items, similarity_threshold)

    # Step 2: Score and rank
    top_items = score_and_rank_items(unique_items, top_n, lookback_hours)

    return top_items
