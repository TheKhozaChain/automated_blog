"""Configuration management for daily_ai_timeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    # LLM Provider settings
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"

    # Processing settings
    top_n_items: int = 10
    timezone: str = "Australia/Sydney"

    # Paths
    output_dir: Path = Path("out")

    # Mode settings
    lookback_hours_daily: int = 24
    lookback_hours_realtime: int = 1
    lookback_hours_weekly: int = 168  # 7 days

    @classmethod
    def from_env(cls, env_file: Optional[Path] = None) -> "Config":
        """Load configuration from environment variables."""
        if env_file and env_file.exists():
            load_dotenv(env_file)
        else:
            load_dotenv()

        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
            top_n_items=int(os.getenv("TOP_N_ITEMS", "10")),
            timezone=os.getenv("TIMEZONE", "Australia/Sydney"),
            output_dir=Path(os.getenv("OUTPUT_DIR", "out")),
            lookback_hours_daily=int(os.getenv("LOOKBACK_HOURS_DAILY", "24")),
            lookback_hours_realtime=int(os.getenv("LOOKBACK_HOURS_REALTIME", "1")),
            lookback_hours_weekly=int(os.getenv("LOOKBACK_HOURS_WEEKLY", "168")),
        )

    def get_preferred_provider(self) -> Optional[str]:
        """Determine which LLM provider to use based on available API keys."""
        if self.anthropic_api_key:
            return "anthropic"
        elif self.openai_api_key:
            return "openai"
        return None

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        if not self.openai_api_key and not self.anthropic_api_key:
            errors.append(
                "No LLM API key configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY."
            )
        return errors


# RSS Feed sources
RSS_FEEDS = {
    "OpenAI Blog": "https://openai.com/blog/rss.xml",
    "Anthropic Blog": "https://www.anthropic.com/rss.xml",
    "DeepMind Blog": "https://deepmind.google/blog/rss.xml",
    "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "MIT Tech Review AI": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    "Ars Technica AI": "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "Wired AI": "https://www.wired.com/feed/tag/ai/latest/rss",
}

# arXiv categories to fetch
ARXIV_CATEGORIES = ["cs.AI", "cs.LG"]

# Hacker News search keywords
HN_KEYWORDS = [
    "AI",
    "OpenAI",
    "Anthropic",
    "Claude",
    "Gemini",
    "NVIDIA",
    "LLM",
    "GPT",
    "machine learning",
    "neural network",
]

# Reddit subreddits for AI news
REDDIT_SUBREDDITS = [
    "MachineLearning",
    "artificial",
]

# Source credibility scores (0-20)
SOURCE_CREDIBILITY = {
    "OpenAI Blog": 20,
    "Anthropic Blog": 20,
    "DeepMind Blog": 20,
    "arXiv": 18,
    "MIT Tech Review AI": 15,
    "TechCrunch AI": 12,
    "The Verge AI": 10,
    "Ars Technica AI": 10,
    "Wired AI": 10,
    "Reddit r/MachineLearning": 10,
    "Reddit r/artificial": 8,
    "Hacker News": 8,
}

# High-value keywords for scoring
SCORING_KEYWORDS = [
    "release",
    "launch",
    "benchmark",
    "acquisition",
    "policy",
    "compute",
    "robot",
    "AGI",
    "breakthrough",
    "billion",
    "million",
    "partnership",
    "regulation",
    "safety",
    "alignment",
]
