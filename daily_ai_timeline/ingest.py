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

from .config import ARXIV_CATEGORIES, HN_KEYWORDS, REDDIT_SUBREDDITS, RSS_FEEDS, X_ACCOUNTS, Config, NicheConfig
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

                # Re-tag HN items that link to X/Twitter as "X/Twitter" source
                # so the LLM attributes them correctly
                source = "Hacker News"
                if url and any(domain in url for domain in ["x.com/", "twitter.com/"]):
                    source = "X/Twitter"

                item = NewsItem(
                    title=hit.get("title", "Untitled"),
                    url=url,
                    source=source,
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


def fetch_x_syndication(
    accounts: list[str],
    max_hours: int = 24,
    min_likes: int = 20,
    show_progress: bool = True,
) -> list[NewsItem]:
    """Fetch recent tweets from curated X/Twitter accounts via the public
    syndication API. Requires NO API key, NO login, NO credentials.

    Uses the same public endpoint that powers embedded tweet widgets.
    If X changes or blocks this endpoint, the function fails gracefully
    and returns an empty list with a clear log message.

    Args:
        accounts: List of X/Twitter screen names (without @)
        max_hours: Maximum age of tweets to include
        min_likes: Minimum likes threshold for tweets
        show_progress: Whether to show progress bar

    Returns:
        List of NewsItem objects
    """
    import json

    items = []
    seen_ids = set()
    syndication_url = "https://syndication.twitter.com/srv/timeline-profile/screen-name/{username}"

    acct_iter = tqdm(accounts, desc="Fetching X/Twitter") if show_progress else accounts

    for username in acct_iter:
        try:
            url = syndication_url.format(username=username)
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

            if response.status_code == 403:
                logger.warning(
                    f"X syndication blocked for @{username} (403 Forbidden). "
                    "X may have restricted access to this endpoint."
                )
                continue

            if response.status_code == 404:
                logger.warning(f"X account @{username} not found (404).")
                continue

            if response.status_code != 200:
                logger.warning(
                    f"X syndication returned {response.status_code} for @{username}. "
                    "The syndication API may have changed or be rate-limiting."
                )
                continue

            # Parse the __NEXT_DATA__ JSON from the HTML response
            soup = BeautifulSoup(response.text, "html.parser")
            next_data_tag = soup.find("script", id="__NEXT_DATA__")

            if not next_data_tag or not next_data_tag.string:
                logger.warning(
                    f"X syndication for @{username}: no __NEXT_DATA__ found. "
                    "X may have changed their syndication page structure. "
                    "The X/Twitter source will be unavailable until this is fixed."
                )
                continue

            try:
                data = json.loads(next_data_tag.string)
            except json.JSONDecodeError:
                logger.warning(
                    f"X syndication for @{username}: failed to parse JSON. "
                    "The syndication page structure may have changed."
                )
                continue

            entries = (
                data.get("props", {})
                .get("pageProps", {})
                .get("timeline", {})
                .get("entries", [])
            )

            for entry in entries:
                if entry.get("type") != "tweet":
                    continue

                tweet = entry.get("content", {}).get("tweet", {})
                if not tweet:
                    continue

                tweet_id = entry.get("entry_id", "").replace("tweet-", "")
                if tweet_id in seen_ids:
                    continue
                seen_ids.add(tweet_id)

                # Parse creation time
                created_at = tweet.get("created_at", "")
                published = parse_date(created_at) if created_at else None
                if not published:
                    continue

                # Skip tweets outside lookback window
                if hours_since(published) > max_hours:
                    continue

                # Check engagement threshold
                likes = tweet.get("favorite_count", 0)
                if likes < min_likes:
                    continue

                # Get tweet text
                text = tweet.get("text", "")

                # Skip tweets that are just links with no commentary
                clean_text = text.strip()
                if clean_text.startswith("https://t.co/") and len(clean_text) < 30:
                    # Tweet is just a link — try to get expanded URL for title
                    entities = tweet.get("entities", {})
                    urls = entities.get("urls", [])
                    if urls:
                        expanded = urls[0].get("expanded_url", "")
                        display = urls[0].get("display_url", "")
                        text = f"Shared: {display or expanded}"

                # Get user info
                user = tweet.get("user", {})
                screen_name = user.get("screen_name", username)
                display_name = user.get("name", username)

                # Build tweet URL
                tweet_url = f"https://x.com/{screen_name}/status/{tweet_id}"

                # Build title with author
                title_text = text[:150].replace("\n", " ")
                if len(text) > 150:
                    title_text += "..."
                title = f"@{screen_name}: {title_text}"

                retweets = tweet.get("retweet_count", 0)
                replies = tweet.get("reply_count", 0)

                item = NewsItem(
                    title=title,
                    url=tweet_url,
                    source="X/Twitter",
                    published=published,
                    summary=text[:400],
                    authors=[f"@{screen_name}"],
                )
                items.append(item)

        except requests.exceptions.ConnectionError:
            logger.warning(
                f"Cannot connect to X syndication API for @{username}. "
                "X.com may be down or blocking requests. Skipping X/Twitter source."
            )
            break  # If we can't connect at all, skip remaining accounts
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching X syndication for @{username}.")
            continue
        except Exception as e:
            logger.warning(
                f"Unexpected error fetching X/Twitter for @{username}: {e}. "
                "This may indicate a change in X's syndication API. "
                "The X/Twitter source will be skipped for this account."
            )
            continue

    logger.info(f"Fetched {len(items)} posts from X/Twitter")
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
    niche: NicheConfig | None = None,
) -> list[NewsItem]:
    """Fetch items from all configured sources.

    Args:
        config: Application configuration
        mode: 'daily' (24h), 'realtime' (1h), or 'weekly' (7 days)
        show_progress: Whether to show progress bars
        fetch_content: Whether to fetch full article content
        niche: Niche configuration (uses defaults if None)

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

    # Use niche sources if provided, otherwise use defaults
    rss_feeds = niche.rss_feeds if niche else RSS_FEEDS
    arxiv_categories = niche.arxiv_categories if niche else ARXIV_CATEGORIES
    hn_keywords = niche.hn_keywords if niche else HN_KEYWORDS
    reddit_subreddits = niche.reddit_subreddits if niche else REDDIT_SUBREDDITS
    x_accounts = niche.x_accounts if niche else X_ACCOUNTS

    # Fetch from all sources
    all_items = []

    # RSS feeds
    if rss_feeds:
        rss_items = fetch_rss_feeds(
            feeds=rss_feeds,
            max_hours=max_hours,
            show_progress=show_progress,
        )
        all_items.extend(rss_items)

    # arXiv (skip if no categories configured)
    if arxiv_categories:
        arxiv_items = fetch_arxiv(
            categories=arxiv_categories,
            max_hours=max_hours,
            show_progress=show_progress,
        )
        all_items.extend(arxiv_items)

    # Hacker News
    if hn_keywords:
        hn_items = fetch_hackernews(
            keywords=hn_keywords,
            max_hours=max_hours,
            show_progress=show_progress,
        )
        all_items.extend(hn_items)

    # X/Twitter (via public syndication API — no credentials needed)
    x_accounts = niche.x_accounts if niche else X_ACCOUNTS
    if x_accounts:
        x_items = fetch_x_syndication(
            accounts=x_accounts,
            max_hours=max_hours,
            show_progress=show_progress,
        )
        all_items.extend(x_items)

    # Reddit (legacy — only fetched if subreddits are configured)
    if reddit_subreddits:
        reddit_items = fetch_reddit(
            subreddits=reddit_subreddits,
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
