"""Tests for prompt construction."""

import pytest
from datetime import datetime, timezone

from daily_ai_timeline.ingest import NewsItem
from daily_ai_timeline.prompt import (
    build_prompt,
    format_items_for_prompt,
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
        system, user = build_prompt(items)
        assert isinstance(system, str)
        assert isinstance(user, str)
        assert len(system) > 0
        assert len(user) > 0

    def test_prompt_includes_items(self):
        items = self._create_items()
        _, user = build_prompt(items)
        for item in items:
            assert item.title in user

    def test_includes_date(self):
        items = self._create_items()
        date = datetime(2025, 1, 2)
        _, user = build_prompt(items, date)
        assert "January" in user

    def test_system_prompt_has_voice(self):
        items = self._create_items()
        system, _ = build_prompt(items)
        assert "sardonic" in system.lower() or "chronicle" in system.lower()

    def test_user_prompt_has_welcome(self):
        items = self._create_items()
        _, user = build_prompt(items, datetime(2025, 3, 15))
        assert "Welcome to" in user
