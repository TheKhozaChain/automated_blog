"""LLM integration and post generation for daily_ai_timeline.

Provides abstraction for OpenAI and Anthropic APIs, and orchestrates
the generation of a unified article with inline links.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import Config
from .ingest import NewsItem
from .prompt import build_prompt
from .utils import ensure_output_dir, save_json, save_text

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
    ) -> str:
        """Generate text from the LLM.

        Args:
            system_prompt: System/context prompt
            user_prompt: User/task prompt
            max_tokens: Maximum tokens in response

        Returns:
            Generated text
        """
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model name to use
        """
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
    ) -> str:
        """Generate text using OpenAI API."""
        # GPT-5+ models use max_completion_tokens instead of max_tokens
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_completion_tokens=max_tokens,
            temperature=0.7,
        )
        return response.choices[0].message.content or ""


class AnthropicProvider(LLMProvider):
    """Anthropic API provider."""

    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model name to use
        """
        from anthropic import Anthropic

        self.client = Anthropic(api_key=api_key)
        self.model = model

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
    ) -> str:
        """Generate text using Anthropic API."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        # Extract text from response
        return response.content[0].text if response.content else ""


def get_provider(config: Config) -> LLMProvider:
    """Get the appropriate LLM provider based on configuration.

    Args:
        config: Application configuration

    Returns:
        Configured LLMProvider instance

    Raises:
        ValueError: If no API key is configured
    """
    preferred = config.get_preferred_provider()

    if preferred == "anthropic":
        logger.info(f"Using Anthropic provider with model: {config.anthropic_model}")
        return AnthropicProvider(
            api_key=config.anthropic_api_key,
            model=config.anthropic_model,
        )
    elif preferred == "openai":
        logger.info(f"Using OpenAI provider with model: {config.openai_model}")
        return OpenAIProvider(
            api_key=config.openai_api_key,
            model=config.openai_model,
        )
    else:
        raise ValueError(
            "No LLM API key configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY."
        )


@dataclass
class GeneratedArticle:
    """Container for the generated article."""

    article: str
    sources: list[dict]
    generated_at: datetime


def generate_article(
    items: list[NewsItem],
    config: Config,
    date: Optional[datetime] = None,
) -> GeneratedArticle:
    """Generate a unified article from the given news items.

    Args:
        items: List of NewsItem objects to write about
        config: Application configuration
        date: Date for the post (defaults to today)

    Returns:
        GeneratedArticle container
    """
    if date is None:
        date = datetime.now()

    provider = get_provider(config)

    # Generate the unified article
    logger.info("Generating article with inline links...")
    system_prompt, user_prompt = build_prompt(items, date)
    article = provider.generate(system_prompt, user_prompt, max_tokens=3000)

    # Prepare sources metadata
    sources = [item.to_dict() for item in items]

    return GeneratedArticle(
        article=article,
        sources=sources,
        generated_at=date,
    )


def save_outputs(
    result: GeneratedArticle,
    output_dir: Path,
) -> dict[str, Path]:
    """Save generated article to files.

    Args:
        result: GeneratedArticle container
        output_dir: Directory to save files

    Returns:
        Dictionary mapping output type to file path
    """
    ensure_output_dir(output_dir)

    saved_files = {}

    # Save article as markdown
    article_path = output_dir / "today.md"
    save_text(result.article, article_path)
    saved_files["article"] = article_path
    logger.info(f"Saved article to {article_path}")

    # Save sources metadata
    sources_path = output_dir / "sources.json"
    sources_data = {
        "generated_at": result.generated_at.isoformat(),
        "item_count": len(result.sources),
        "items": result.sources,
    }
    save_json(sources_data, sources_path)
    saved_files["sources"] = sources_path
    logger.info(f"Saved sources to {sources_path}")

    return saved_files


def run_generation_pipeline(
    items: list[NewsItem],
    config: Config,
    date: Optional[datetime] = None,
) -> tuple[GeneratedArticle, dict[str, Path]]:
    """Run the complete generation pipeline.

    Args:
        items: List of NewsItem objects
        config: Application configuration
        date: Date for the post (defaults to today)

    Returns:
        Tuple of (GeneratedArticle, saved file paths)
    """
    # Generate the article
    result = generate_article(items, config, date)

    # Save to files
    saved_files = save_outputs(result, config.output_dir)

    return result, saved_files
