"""Source ingestion for daily_ai_timeline.

Fetches AI news from multiple sources:
- RSS feeds (OpenAI, Anthropic, DeepMind, tech news sites)
- arXiv papers (cs.AI and cs.LG categories)
- Hacker News (via Algolia API)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote_plus

import feedparser
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from .config import ARXIV_CATEGORIES, HN_KEYWORDS, REDDIT_SUBREDDITS, RSS_FEEDS, Config
from .utils import clean_html, hours_since, parse_date

logger = logging.getLogger(__name__)

# Request headers to mimic a browser
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Request timeout in seconds
REQUEST_TIMEOUT = 15


@dataclass
class NewsItem:
    """Represents a single news item from any source."""

    title: str
    url: str
    source: str
    published: datetime
    summary: str = ""
    content: str = ""
    authors: list[str] = field(default_factory=list)
    score: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published": self.published.isoformat(),
            "summary": self.summary,
            "content": self.content[:500] if self.content else "",
            "authors": self.authors,
            "score": self.score,
        }


def fetch_rss_feeds(
    feeds: dict[str, str] = RSS_FEEDS,
    max_hours: int = 24,
    show_progress: bool = True,
) -> list[NewsItem]:
    """Fetch items from RSS feeds.

    Args:
        feeds: Dictionary mapping source name to RSS URL
        max_hours: Maximum age of items to include
        show_progress: Whether to show progress bar

    Returns:
        List of NewsItem objects
    """
    items = []
    feed_iter = tqdm(feeds.items(), desc="Fetching RSS feeds") if show_progress else feeds.items()

    for source_name, feed_url in feed_iter:
        try:
            logger.debug(f"Fetching RSS feed: {source_name}")
            feed = feedparser.parse(feed_url)

            for entry in feed.entries:
                # Parse publication date
                published = None
                for date_field in ["published", "updated", "created"]:
                    if hasattr(entry, date_field):
                        published = parse_date(getattr(entry, date_field))
                        if published:
                            break

                if not published:
                    published = datetime.now(timezone.utc)

                # Skip items older than max_hours
                if hours_since(published) > max_hours:
                    continue

                # Extract summary
                summary = ""
                if hasattr(entry, "summary"):
                    summary = clean_html(entry.summary)
                elif hasattr(entry, "description"):
                    summary = clean_html(entry.description)

                item = NewsItem(
                    title=entry.get("title", "Untitled"),
                    url=entry.get("link", ""),
                    source=source_name,
                    published=published,
                    summary=summary[:500] if summary else "",
                )
                items.append(item)

        except Exception as e:
            logger.warning(f"Error fetching RSS feed {source_name}: {e}")
            continue

    logger.info(f"Fetched {len(items)} items from RSS feeds")
    return items


def fetch_arxiv(
    categories: list[str] = ARXIV_CATEGORIES,
    max_results: int = 50,
    max_hours: int = 24,
    show_progress: bool = True,
) -> list[NewsItem]:
    """Fetch recent papers from arXiv.

    Args:
        categories: List of arXiv category codes (e.g., ['cs.AI', 'cs.LG'])
        max_results: Maximum number of results per category
        max_hours: Maximum age of papers to include
        show_progress: Whether to show progress bar

    Returns:
        List of NewsItem objects
    """
    items = []
    base_url = "http://export.arxiv.org/api/query"

    cat_iter = tqdm(categories, desc="Fetching arXiv") if show_progress else categories

    for category in cat_iter:
        try:
            # Build query for recent papers in category
            query = f"cat:{category}"
            params = {
                "search_query": query,
                "start": 0,
                "max_results": max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }

            response = requests.get(base_url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            # Parse Atom feed
            feed = feedparser.parse(response.content)

            for entry in feed.entries:
                # Parse publication date
                published = parse_date(entry.get("published", ""))
                if not published:
                    continue

                # Skip items older than max_hours
                if hours_since(published) > max_hours:
                    continue

                # Extract authors
                authors = []
                if hasattr(entry, "authors"):
                    authors = [a.get("name", "") for a in entry.authors]

                # Get abstract
                summary = entry.get("summary", "")
                summary = clean_html(summary).replace("\n", " ")

                item = NewsItem(
                    title=entry.get("title", "").replace("\n", " "),
                    url=entry.get("link", ""),
                    source="arXiv",
                    published=published,
                    summary=summary[:500] if summary else "",
                    authors=authors[:5],  # Limit to first 5 authors
                )
                items.append(item)

        except Exception as e:
            logger.warning(f"Error fetching arXiv category {category}: {e}")
            continue

    logger.info(f"Fetched {len(items)} papers from arXiv")
    return items


def fetch_hackernews(
    keywords: list[str] = HN_KEYWORDS,
    max_hours: int = 24,
    min_points: int = 10,
    show_progress: bool = True,
) -> list[NewsItem]:
    """Fetch AI-related stories from Hacker News via Algolia API.

    Args:
        keywords: List of keywords to search for
        max_hours: Maximum age of stories to include
        min_points: Minimum point threshold for stories
        show_progress: Whether to show progress bar

    Returns:
        List of NewsItem objects
    """
    items = []
    seen_ids = set()
    base_url = "https://hn.algolia.com/api/v1/search"

    kw_iter = tqdm(keywords, desc="Fetching Hacker News") if show_progress else keywords

    for keyword in kw_iter:
        try:
            params = {
                "query": keyword,
                "tags": "story",
                "numericFilters": f"created_at_i>{int((datetime.now(timezone.utc).timestamp()) - (max_hours * 3600))}",
            }

            response = requests.get(base_url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            for hit in data.get("hits", []):
                # Skip if already seen or below point threshold
                story_id = hit.get("objectID")
                if story_id in seen_ids:
                    continue
                seen_ids.add(story_id)

                points = hit.get("points", 0)
                if points < min_points:
                    continue

                # Parse creation time
                created_at = hit.get("created_at")
                published = parse_date(created_at) if created_at else datetime.now(timezone.utc)

                # Get URL (prefer article URL, fall back to HN discussion)
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={story_id}"

                item = NewsItem(
                    title=hit.get("title", "Untitled"),
                    url=url,
                    source="Hacker News",
                    published=published,
                    summary=f"Points: {points}, Comments: {hit.get('num_comments', 0)}",
                    authors=[hit.get("author", "")],
                )
                items.append(item)

        except Exception as e:
            logger.warning(f"Error fetching Hacker News for keyword '{keyword}': {e}")
            continue

    logger.info(f"Fetched {len(items)} stories from Hacker News")
    return items


def fetch_reddit(
    subreddits: list[str] = REDDIT_SUBREDDITS,
    max_hours: int = 24,
    show_progress: bool = True,
) -> list[NewsItem]:
    """Fetch AI-related posts from Reddit subreddits via RSS.

    Args:
        subreddits: List of subreddit names to fetch from
        max_hours: Maximum age of posts to include
        show_progress: Whether to show progress bar

    Returns:
        List of NewsItem objects
    """
    items = []
    seen_urls = set()

    sub_iter = tqdm(subreddits, desc="Fetching Reddit") if show_progress else subreddits

    for subreddit in sub_iter:
        try:
            # Use Reddit RSS feed (more reliable than JSON API)
            rss_url = f"https://www.reddit.com/r/{subreddit}/hot.rss"
            feed = feedparser.parse(rss_url)

            for entry in feed.entries:
                # Get the actual link (not the Reddit comments page)
                url = entry.get("link", "")

                # Skip if already seen
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # Parse publication date
                published = None
                for date_field in ["published", "updated"]:
                    if hasattr(entry, date_field):
                        published = parse_date(getattr(entry, date_field))
                        if published:
                            break

                if not published:
                    published = datetime.now(timezone.utc)

                # Skip items older than max_hours
                if hours_since(published) > max_hours:
                    continue

                # Extract title (remove subreddit prefix if present)
                title = entry.get("title", "Untitled")

                # Get author
                author = entry.get("author", "")
                if author.startswith("/u/"):
                    author = author[3:]

                # Extract summary/content
                summary = ""
                if hasattr(entry, "summary"):
                    summary = clean_html(entry.summary)[:200]

                item = NewsItem(
                    title=title,
                    url=url,
                    source=f"Reddit r/{subreddit}",
                    published=published,
                    summary=summary if summary else f"From r/{subreddit}",
                    authors=[author] if author else [],
                )
                items.append(item)

        except Exception as e:
            logger.warning(f"Error fetching Reddit r/{subreddit}: {e}")
            continue

    logger.info(f"Fetched {len(items)} posts from Reddit")
    return items


def extract_article_content(url: str, max_words: int = 500) -> str:
    """Extract main content from an article URL.

    Args:
        url: The article URL to fetch
        max_words: Maximum number of words to extract

    Returns:
        Extracted text content (may be empty on failure)
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()

        # Try to find main content
        content = None

        # Look for article tag first
        article = soup.find("article")
        if article:
            content = article

        # Try common content selectors
        if not content:
            for selector in [
                ".article-content",
                ".post-content",
                ".entry-content",
                ".content",
                "main",
                "[role='main']",
            ]:
                found = soup.select_one(selector)
                if found:
                    content = found
                    break

        # Fall back to body
        if not content:
            content = soup.body

        if not content:
            return ""

        # Extract text
        text = content.get_text(separator=" ", strip=True)

        # Limit to max_words
        words = text.split()
        if len(words) > max_words:
            text = " ".join(words[:max_words]) + "..."

        return text

    except Exception as e:
        logger.debug(f"Could not extract content from {url}: {e}")
        return ""


def fetch_all_sources(
    config: Config,
    mode: str = "daily",
    show_progress: bool = True,
    fetch_content: bool = False,
) -> list[NewsItem]:
    """Fetch items from all configured sources.

    Args:
        config: Application configuration
        mode: 'daily' (24h), 'realtime' (1h), or 'weekly' (7 days)
        show_progress: Whether to show progress bars
        fetch_content: Whether to fetch full article content

    Returns:
        Combined list of NewsItem objects from all sources
    """
    if mode == "weekly":
        max_hours = config.lookback_hours_weekly
    elif mode == "realtime":
        max_hours = config.lookback_hours_realtime
    else:
        max_hours = config.lookback_hours_daily

    logger.info(f"Fetching sources with {max_hours}h lookback window")

    # Fetch from all sources
    all_items = []

    # RSS feeds
    rss_items = fetch_rss_feeds(
        feeds=RSS_FEEDS,
        max_hours=max_hours,
        show_progress=show_progress,
    )
    all_items.extend(rss_items)

    # arXiv
    arxiv_items = fetch_arxiv(
        categories=ARXIV_CATEGORIES,
        max_hours=max_hours,
        show_progress=show_progress,
    )
    all_items.extend(arxiv_items)

    # Hacker News
    hn_items = fetch_hackernews(
        keywords=HN_KEYWORDS,
        max_hours=max_hours,
        show_progress=show_progress,
    )
    all_items.extend(hn_items)

    # Reddit
    reddit_items = fetch_reddit(
        subreddits=REDDIT_SUBREDDITS,
        max_hours=max_hours,
        show_progress=show_progress,
    )
    all_items.extend(reddit_items)

    # Optionally fetch full content for top items
    if fetch_content:
        logger.info("Fetching full article content...")
        item_iter = (
            tqdm(all_items, desc="Extracting content")
            if show_progress
            else all_items
        )
        for item in item_iter:
            if not item.content and item.url:
                item.content = extract_article_content(item.url)

    logger.info(f"Total items fetched: {len(all_items)}")
    return all_items
