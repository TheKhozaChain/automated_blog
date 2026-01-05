"""Tests for item scoring logic."""

import pytest
from datetime import datetime, timedelta, timezone

from daily_ai_timeline.dedupe import score_item, score_and_rank_items
from daily_ai_timeline.ingest import NewsItem


class TestScoring:
    """Tests for the scoring algorithm."""

    def _create_item(
        self,
        title: str = "Test Article",
        source: str = "Test Source",
        hours_ago: float = 0,
        summary: str = "",
    ) -> NewsItem:
        published = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        return NewsItem(
            title=title,
            url="https://example.com/article",
            source=source,
            published=published,
            summary=summary,
        )

    def test_recent_items_score_higher(self):
        recent = self._create_item(hours_ago=1)
        old = self._create_item(hours_ago=20)

        recent_score = score_item(recent)
        old_score = score_item(old)

        assert recent_score > old_score

    def test_credible_sources_score_higher(self):
        openai = self._create_item(source="OpenAI Blog")
        hn = self._create_item(source="Hacker News")

        openai_score = score_item(openai)
        hn_score = score_item(hn)

        assert openai_score > hn_score

    def test_keywords_increase_score(self):
        with_keywords = self._create_item(
            title="OpenAI launches breakthrough AGI benchmark"
        )
        without_keywords = self._create_item(
            title="Tech company releases software update"
        )

        kw_score = score_item(with_keywords)
        no_kw_score = score_item(without_keywords)

        assert kw_score > no_kw_score

    def test_numbers_increase_score(self):
        with_numbers = self._create_item(
            title="OpenAI raises $10B in funding round"
        )
        without_numbers = self._create_item(
            title="OpenAI raises funding round"
        )

        num_score = score_item(with_numbers)
        no_num_score = score_item(without_numbers)

        assert num_score > no_num_score

    def test_combined_factors(self):
        # Item with all positive factors
        best = self._create_item(
            title="OpenAI launches $10B AGI benchmark breakthrough",
            source="OpenAI Blog",
            hours_ago=0.5,
        )

        # Item with no positive factors
        worst = self._create_item(
            title="Some company did something",
            source="Unknown Blog",
            hours_ago=23,
        )

        best_score = score_item(best)
        worst_score = score_item(worst)

        assert best_score > worst_score * 2  # Should be significantly higher


class TestRanking:
    """Tests for item ranking."""

    def _create_items(self, count: int) -> list[NewsItem]:
        items = []
        for i in range(count):
            items.append(
                NewsItem(
                    title=f"Article {i}",
                    url=f"https://example.com/article-{i}",
                    source="Test Source",
                    published=datetime.now(timezone.utc) - timedelta(hours=i),
                )
            )
        return items

    def test_returns_top_n(self):
        items = self._create_items(20)
        result = score_and_rank_items(items, top_n=10)
        assert len(result) == 10

    def test_sorted_by_score_descending(self):
        items = self._create_items(10)
        result = score_and_rank_items(items, top_n=10)

        for i in range(len(result) - 1):
            assert result[i].score >= result[i + 1].score

    def test_handles_fewer_items_than_top_n(self):
        items = self._create_items(5)
        result = score_and_rank_items(items, top_n=10)
        assert len(result) == 5

    def test_empty_list(self):
        result = score_and_rank_items([], top_n=10)
        assert result == []
