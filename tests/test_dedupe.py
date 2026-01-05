"""Tests for deduplication logic."""

import pytest
from datetime import datetime, timezone

from daily_ai_timeline.dedupe import (
    deduplicate_items,
    title_similarity,
)
from daily_ai_timeline.ingest import NewsItem
from daily_ai_timeline.utils import normalize_url


class TestUrlNormalization:
    """Tests for URL normalization."""

    def test_removes_www_prefix(self):
        url = "https://www.example.com/article"
        normalized = normalize_url(url)
        assert "www." not in normalized
        assert "example.com" in normalized

    def test_removes_utm_params(self):
        url = "https://example.com/article?utm_source=twitter&utm_medium=social"
        normalized = normalize_url(url)
        assert "utm_source" not in normalized
        assert "utm_medium" not in normalized

    def test_removes_trailing_slash(self):
        url = "https://example.com/article/"
        normalized = normalize_url(url)
        assert normalized.endswith("/article")

    def test_lowercases_domain(self):
        url = "https://EXAMPLE.COM/Article"
        normalized = normalize_url(url)
        assert "example.com" in normalized

    def test_preserves_path(self):
        url = "https://example.com/blog/2024/ai-news"
        normalized = normalize_url(url)
        assert "/blog/2024/ai-news" in normalized


class TestTitleSimilarity:
    """Tests for fuzzy title matching."""

    def test_identical_titles(self):
        title1 = "OpenAI announces GPT-5"
        title2 = "OpenAI announces GPT-5"
        assert title_similarity(title1, title2) == 1.0

    def test_similar_titles(self):
        title1 = "OpenAI announces GPT-5 with new features"
        title2 = "OpenAI announces GPT-5 with improved features"
        similarity = title_similarity(title1, title2)
        assert similarity > 0.85

    def test_different_titles(self):
        title1 = "OpenAI announces GPT-5"
        title2 = "Google releases Gemini 2.0"
        similarity = title_similarity(title1, title2)
        assert similarity < 0.5

    def test_case_insensitive(self):
        title1 = "OPENAI ANNOUNCES GPT-5"
        title2 = "openai announces gpt-5"
        similarity = title_similarity(title1, title2)
        assert similarity == 1.0


class TestDeduplication:
    """Tests for item deduplication."""

    def _create_item(
        self,
        title: str,
        url: str,
        source: str = "Test Source",
    ) -> NewsItem:
        return NewsItem(
            title=title,
            url=url,
            source=source,
            published=datetime.now(timezone.utc),
        )

    def test_deduplicates_by_url(self):
        items = [
            self._create_item("Article 1", "https://example.com/article"),
            self._create_item("Article 2", "https://example.com/article"),
        ]
        result = deduplicate_items(items)
        assert len(result) == 1

    def test_deduplicates_by_similar_title(self):
        items = [
            self._create_item(
                "OpenAI announces GPT-5 today",
                "https://example1.com/article",
            ),
            self._create_item(
                "OpenAI announces GPT-5 today!",
                "https://example2.com/article",
            ),
        ]
        result = deduplicate_items(items)
        assert len(result) == 1

    def test_keeps_different_articles(self):
        items = [
            self._create_item(
                "OpenAI announces GPT-5",
                "https://example.com/openai",
            ),
            self._create_item(
                "Google releases Gemini 2.0",
                "https://example.com/google",
            ),
        ]
        result = deduplicate_items(items)
        assert len(result) == 2

    def test_prefers_higher_credibility_source(self):
        items = [
            self._create_item(
                "OpenAI announces GPT-5",
                "https://example1.com/article",
                "Hacker News",  # Lower credibility
            ),
            self._create_item(
                "OpenAI announces GPT-5",
                "https://example2.com/article",
                "OpenAI Blog",  # Higher credibility
            ),
        ]
        result = deduplicate_items(items)
        assert len(result) == 1
        assert result[0].source == "OpenAI Blog"

    def test_empty_list(self):
        result = deduplicate_items([])
        assert result == []
