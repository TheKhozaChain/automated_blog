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

from .config import Config, NicheConfig
from .ingest import NewsItem
from .prompt import build_prompt
from .utils import calculate_reading_time, ensure_output_dir, save_json, save_text

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
    headline: str
    sources: list[dict]
    generated_at: datetime
    reading_time_minutes: int = 0
    hero_image_path: Optional[Path] = None


def extract_headline(article: str) -> str:
    """Extract the headline from the article markdown.

    Args:
        article: The full article markdown

    Returns:
        The headline text (without the # prefix)
    """
    import re
    # Look for H1 headline at the start
    match = re.match(r'^#\s+(.+?)(?:\n|$)', article.strip())
    if match:
        return match.group(1).strip()
    # Fallback: use first line
    first_line = article.strip().split('\n')[0]
    return first_line.lstrip('#').strip()


def generate_hero_image(
    headline: str,
    article_preview: str,
    config: Config,
    output_dir: Path,
) -> Optional[Path]:
    """Generate a hero image using DALL-E based on the article content.

    Args:
        headline: The article headline
        article_preview: First few paragraphs of the article
        config: Application configuration
        output_dir: Directory to save the image

    Returns:
        Path to the saved image, or None if generation fails
    """
    if not config.openai_api_key:
        logger.warning("OpenAI API key required for image generation. Skipping.")
        return None

    try:
        from openai import OpenAI
        import requests

        client = OpenAI(api_key=config.openai_api_key)

        # Create a prompt for DALL-E based on the headline and content
        image_prompt = f"""Create a sophisticated, editorial-style hero image for a technology article.

Headline: "{headline}"

Style requirements:
- Modern, clean, minimalist aesthetic
- Abstract or conceptual representation of AI/technology themes
- Dark, moody color palette with accent colors (deep blues, teals, purples)
- Suitable for a professional tech publication like Wired or MIT Technology Review
- No text or words in the image
- Cinematic lighting, high contrast
- Could include abstract neural networks, geometric patterns, futuristic cityscapes, or symbolic imagery

The image should evoke innovation, progress, and the intersection of technology with society."""

        logger.info("Generating hero image with DALL-E...")
        response = client.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            size="1792x1024",  # Wide format for hero image
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        if not image_url:
            logger.warning("No image URL returned from DALL-E")
            return None

        # Download and save the image
        image_response = requests.get(image_url, timeout=30)
        image_response.raise_for_status()

        ensure_output_dir(output_dir)
        image_path = output_dir / "hero.png"
        with open(image_path, 'wb') as f:
            f.write(image_response.content)

        logger.info(f"Saved hero image to {image_path}")
        return image_path

    except Exception as e:
        logger.warning(f"Failed to generate hero image: {e}")
        return None


def generate_article(
    items: list[NewsItem],
    config: Config,
    date: Optional[datetime] = None,
    niche: Optional[NicheConfig] = None,
) -> GeneratedArticle:
    """Generate a unified article from the given news items.

    Args:
        items: List of NewsItem objects to write about
        config: Application configuration
        date: Date for the post (defaults to today)
        niche: Optional niche configuration for customization

    Returns:
        GeneratedArticle container
    """
    if date is None:
        date = datetime.now()

    provider = get_provider(config)

    # Generate the unified article
    logger.info("Generating article with inline links...")
    system_prompt, user_prompt = build_prompt(items, date, niche)
    article = provider.generate(system_prompt, user_prompt, max_tokens=3000)

    # Extract headline from the article
    headline = extract_headline(article)
    logger.info(f"Article headline: {headline}")

    # Calculate reading time
    reading_time = calculate_reading_time(article)
    logger.info(f"Estimated reading time: {reading_time} min")

    # Prepare sources metadata
    sources = [item.to_dict() for item in items]

    return GeneratedArticle(
        article=article,
        headline=headline,
        sources=sources,
        generated_at=date,
        reading_time_minutes=reading_time,
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

    # Create archive directory
    archive_dir = output_dir / "archive"
    ensure_output_dir(archive_dir)

    saved_files = {}

    # Generate date string for archive
    date_str = result.generated_at.strftime("%Y-%m-%d")

    # Save article as markdown (today.md for current, dated for archive)
    article_path = output_dir / "today.md"
    save_text(result.article, article_path)
    saved_files["article"] = article_path
    logger.info(f"Saved article to {article_path}")

    # Save dated copy to archive
    archive_article_path = archive_dir / f"{date_str}.md"
    save_text(result.article, archive_article_path)
    saved_files["archive_article"] = archive_article_path
    logger.info(f"Saved archive article to {archive_article_path}")

    # Save sources metadata
    sources_path = output_dir / "sources.json"
    sources_data = {
        "generated_at": result.generated_at.isoformat(),
        "headline": result.headline,
        "reading_time_minutes": result.reading_time_minutes,
        "hero_image": str(result.hero_image_path) if result.hero_image_path else None,
        "item_count": len(result.sources),
        "items": result.sources,
    }
    save_json(sources_data, sources_path)
    saved_files["sources"] = sources_path
    logger.info(f"Saved sources to {sources_path}")

    # Save dated sources to archive
    archive_sources_path = archive_dir / f"{date_str}.json"
    save_json(sources_data, archive_sources_path)
    saved_files["archive_sources"] = archive_sources_path

    # Copy hero image to archive if it exists
    if result.hero_image_path and result.hero_image_path.exists():
        import shutil
        archive_hero_path = archive_dir / f"{date_str}.png"
        shutil.copy2(result.hero_image_path, archive_hero_path)
        saved_files["archive_hero"] = archive_hero_path
        logger.info(f"Saved archive hero image to {archive_hero_path}")

    # Record hero image path if it exists
    if result.hero_image_path:
        saved_files["hero_image"] = result.hero_image_path

    return saved_files


def run_generation_pipeline(
    items: list[NewsItem],
    config: Config,
    date: Optional[datetime] = None,
    generate_image: bool = True,
    niche: Optional[NicheConfig] = None,
) -> tuple[GeneratedArticle, dict[str, Path]]:
    """Run the complete generation pipeline.

    Args:
        items: List of NewsItem objects
        config: Application configuration
        date: Date for the post (defaults to today)
        generate_image: Whether to generate a hero image with DALL-E
        niche: Optional niche configuration for customization

    Returns:
        Tuple of (GeneratedArticle, saved file paths)
    """
    # Generate the article
    result = generate_article(items, config, date, niche)

    # Generate hero image if enabled
    if generate_image:
        article_preview = result.article[:500]
        image_path = generate_hero_image(
            headline=result.headline,
            article_preview=article_preview,
            config=config,
            output_dir=config.output_dir,
        )
        result.hero_image_path = image_path

    # Save to files
    saved_files = save_outputs(result, config.output_dir)

    return result, saved_files
