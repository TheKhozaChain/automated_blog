"""Utility functions for daily_ai_timeline."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from dateutil import parser as date_parser
from dateutil import tz


def get_current_time(timezone_str: str = "Australia/Sydney") -> datetime:
    """Get current time in the specified timezone."""
    tz_info = tz.gettz(timezone_str)
    return datetime.now(tz_info)


def parse_date(date_str: str, default_tz: str = "UTC") -> Optional[datetime]:
    """Parse a date string into a datetime object."""
    try:
        dt = date_parser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz.gettz(default_tz))
        return dt
    except (ValueError, TypeError):
        return None


def format_date_for_title(dt: datetime) -> str:
    """Format date for the post title (e.g., 'Thursday, January 2, 2025')."""
    return dt.strftime("%A, %B %-d, %Y")


def hours_since(dt: datetime, reference: Optional[datetime] = None) -> float:
    """Calculate hours elapsed since a given datetime."""
    if reference is None:
        reference = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    delta = reference - dt
    return delta.total_seconds() / 3600


def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication purposes."""
    parsed = urlparse(url)

    # Remove www prefix
    netloc = parsed.netloc
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # Remove common tracking parameters
    tracking_params = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "ref",
        "source",
        "fbclid",
        "gclid",
    }
    query_params = parse_qs(parsed.query)
    filtered_params = {
        k: v for k, v in query_params.items() if k.lower() not in tracking_params
    }
    new_query = urlencode(filtered_params, doseq=True)

    # Reconstruct URL
    normalized = urlunparse(
        (
            parsed.scheme.lower(),
            netloc.lower(),
            parsed.path.rstrip("/"),
            parsed.params,
            new_query,
            "",  # Remove fragment
        )
    )
    return normalized


def extract_numbers(text: str) -> list[str]:
    """Extract number patterns from text (monetary, metrics, dates)."""
    patterns = [
        r"\$[\d,]+(?:\.\d+)?[BMK]?",  # Monetary amounts
        r"[\d.]+[BMK]\b",  # Abbreviated numbers (e.g., 5B, 100M)
        r"\d{4}",  # Years
        r"\d+(?:\.\d+)?%",  # Percentages
    ]
    numbers = []
    for pattern in patterns:
        numbers.extend(re.findall(pattern, text, re.IGNORECASE))
    return numbers


def clean_html(html: str) -> str:
    """Remove HTML tags and clean up text."""
    # Remove HTML tags
    clean = re.sub(r"<[^>]+>", "", html)
    # Normalize whitespace
    clean = re.sub(r"\s+", " ", clean)
    # Remove leading/trailing whitespace
    clean = clean.strip()
    return clean


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to a maximum length, breaking at word boundaries."""
    if len(text) <= max_length:
        return text
    truncated = text[: max_length - len(suffix)]
    # Try to break at a word boundary
    last_space = truncated.rfind(" ")
    if last_space > max_length // 2:
        truncated = truncated[:last_space]
    return truncated + suffix


def ensure_output_dir(output_dir: Path) -> Path:
    """Ensure the output directory exists."""
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_json(data: Any, filepath: Path) -> None:
    """Save data to a JSON file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)


def load_json(filepath: Path) -> Any:
    """Load data from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_text(text: str, filepath: Path) -> None:
    """Save text to a file."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)


def split_into_tweets(text: str, max_length: int = 280) -> list[str]:
    """Split text into tweet-sized chunks."""
    if len(text) <= max_length:
        return [text]

    tweets = []
    paragraphs = text.split("\n\n")
    current_tweet = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If paragraph fits in current tweet
        if len(current_tweet) + len(para) + 2 <= max_length:
            if current_tweet:
                current_tweet += "\n\n" + para
            else:
                current_tweet = para
        else:
            # Save current tweet and start new one
            if current_tweet:
                tweets.append(current_tweet)
            # If paragraph itself is too long, split by sentences
            if len(para) > max_length:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                current_tweet = ""
                for sentence in sentences:
                    if len(current_tweet) + len(sentence) + 1 <= max_length:
                        if current_tweet:
                            current_tweet += " " + sentence
                        else:
                            current_tweet = sentence
                    else:
                        if current_tweet:
                            tweets.append(current_tweet)
                        current_tweet = sentence
            else:
                current_tweet = para

    if current_tweet:
        tweets.append(current_tweet)

    # Add thread numbering if multiple tweets
    if len(tweets) > 1:
        total = len(tweets)
        tweets = [f"{i + 1}/{total} {tweet}" for i, tweet in enumerate(tweets)]

    return tweets


def validate_tweet_length(text: str, max_length: int = 280) -> bool:
    """Check if text fits within tweet character limit."""
    return len(text) <= max_length
