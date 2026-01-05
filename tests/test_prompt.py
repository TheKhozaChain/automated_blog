"""Tests for prompt construction."""

import pytest
from datetime import datetime, timezone

from daily_ai_timeline.ingest import NewsItem
from daily_ai_timeline.prompt import (
    build_prompt,
    build_thread_from_full,
    format_items_for_prompt,
    validate_linkedin_output,
    validate_x_output,
)


class TestFormatItems:
    """Tests for formatting items for prompts."""

    def _create_item(
        self,
        title: str = "Test Article",
        source: str = "Test Source",
        url: str = "https://example.com/article",
    ) -> NewsItem:
        return NewsItem(
            title=title,
            url=url,
            source=source,
            published=datetime.now(timezone.utc),
            summary="This is a test summary.",
        )

    def test_includes_title(self):
        items = [self._create_item(title="OpenAI announces GPT-5")]
        formatted = format_items_for_prompt(items)
        assert "OpenAI announces GPT-5" in formatted

    def test_includes_source(self):
        items = [self._create_item(source="OpenAI Blog")]
        formatted = format_items_for_prompt(items)
        assert "OpenAI Blog" in formatted

    def test_includes_url(self):
        items = [self._create_item(url="https://openai.com/blog/gpt5")]
        formatted = format_items_for_prompt(items)
        assert "https://openai.com/blog/gpt5" in formatted

    def test_numbers_multiple_items(self):
        items = [
            self._create_item(title="Article 1"),
            self._create_item(title="Article 2"),
            self._create_item(title="Article 3"),
        ]
        formatted = format_items_for_prompt(items)
        assert "1. **Article 1**" in formatted
        assert "2. **Article 2**" in formatted
        assert "3. **Article 3**" in formatted


class TestBuildPrompt:
    """Tests for building LLM prompts."""

    def _create_items(self, count: int = 3) -> list[NewsItem]:
        return [
            NewsItem(
                title=f"Article {i}",
                url=f"https://example.com/article-{i}",
                source="Test Source",
                published=datetime.now(timezone.utc),
            )
            for i in range(count)
        ]

    def test_returns_system_and_user_prompts(self):
        items = self._create_items()
        system, user = build_prompt(items, "full")
        assert isinstance(system, str)
        assert isinstance(user, str)
        assert len(system) > 0
        assert len(user) > 0

    def test_full_prompt_includes_items(self):
        items = self._create_items()
        _, user = build_prompt(items, "full")
        for item in items:
            assert item.title in user

    def test_linkedin_prompt_different_from_full(self):
        items = self._create_items()
        _, full_user = build_prompt(items, "full")
        _, linkedin_user = build_prompt(items, "linkedin")

        # Different output instructions
        assert "FULL blog post" in full_user
        assert "LINKEDIN post" in linkedin_user

    def test_includes_date(self):
        items = self._create_items()
        date = datetime(2025, 1, 2)
        _, user = build_prompt(items, "full", date)
        assert "January" in user


class TestValidation:
    """Tests for output validation."""

    def test_valid_tweet(self):
        text = "This is a short tweet."
        is_valid, error = validate_x_output(text)
        assert is_valid
        assert error == ""

    def test_invalid_tweet_too_long(self):
        text = "x" * 300
        is_valid, error = validate_x_output(text)
        assert not is_valid
        assert "exceeds 280" in error

    def test_tweet_exactly_280(self):
        text = "x" * 280
        is_valid, error = validate_x_output(text)
        assert is_valid

    def test_valid_linkedin(self):
        text = "x" * 1000
        is_valid, error = validate_linkedin_output(text)
        assert is_valid

    def test_linkedin_too_short(self):
        text = "x" * 500
        is_valid, error = validate_linkedin_output(text)
        assert not is_valid
        assert "too short" in error

    def test_linkedin_too_long(self):
        text = "x" * 2000
        is_valid, error = validate_linkedin_output(text)
        assert not is_valid
        assert "too long" in error


class TestThreadGeneration:
    """Tests for X thread generation."""

    def test_generates_multiple_tweets(self):
        full_post = """Welcome to Thursday, January 2, 2025.

This is the first paragraph about an important development.

This is the second paragraph about another development.

This is the third paragraph about yet another development.

This is the closing thought about AI progress."""

        thread = build_thread_from_full(full_post)
        assert len(thread) >= 2

    def test_tweets_are_numbered(self):
        full_post = """Welcome to Thursday.

Paragraph one is here.

Paragraph two is here.

Closing thought."""

        thread = build_thread_from_full(full_post)
        for i, tweet in enumerate(thread):
            assert tweet.startswith(f"{i + 1}/")

    def test_tweets_within_length(self):
        full_post = """Welcome to Thursday, January 2, 2025. This is a test post.

""" + "\n\n".join([f"Paragraph {i} with some content." for i in range(10)])

        thread = build_thread_from_full(full_post)
        for tweet in thread:
            assert len(tweet) <= 280, f"Tweet too long: {len(tweet)} chars"
