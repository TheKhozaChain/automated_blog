"""Tests for utility functions."""

from daily_ai_timeline.utils import calculate_reading_time


def test_calculate_reading_time_basic():
    """Test basic reading time calculation."""
    # 238 words at 238 wpm should be 1 minute
    text = " ".join(["word"] * 238)
    assert calculate_reading_time(text) == 1


def test_calculate_reading_time_longer():
    """Test reading time for longer text."""
    # 500 words at 238 wpm should be ~2 minutes (rounded up)
    text = " ".join(["word"] * 500)
    assert calculate_reading_time(text) == 3  # ceil(500 / 238) = 3


def test_calculate_reading_time_with_markdown():
    """Test that markdown formatting is properly stripped."""
    text = """# Heading

This is **bold** and *italic* text with [a link](https://example.com).

```python
code block should be removed
```

More text with `inline code`."""

    # Should count: Heading, This, is, bold, and, italic, text, with, a, link, More, text, with, inline, code
    # That's 15 words, minimum 1 minute
    result = calculate_reading_time(text)
    assert result >= 1


def test_calculate_reading_time_minimum():
    """Test that reading time has a minimum of 1 minute."""
    text = "Just a few words"
    assert calculate_reading_time(text) == 1


def test_calculate_reading_time_removes_links():
    """Test that links are processed correctly."""
    text = "Check out [this amazing article](https://example.com) for more info."
    # Should count: Check, out, this, amazing, article, for, more, info = 8 words
    result = calculate_reading_time(text)
    assert result == 1  # Minimum


def test_calculate_reading_time_removes_images():
    """Test that images are removed from word count."""
    text = "Here's an image: ![alt text](image.png) and more text."
    # Should count: Here's, an, image, and, more, text = 6 words
    result = calculate_reading_time(text)
    assert result == 1  # Minimum


def test_calculate_reading_time_realistic_article():
    """Test with a realistic article-length text."""
    # Create a ~1000 word article (should be ~5 minutes at 238 wpm)
    words = " ".join(["lorem"] * 1000)
    article = f"""# The Future of AI

{words}

This is the conclusion."""

    result = calculate_reading_time(article)
    # ceil((1000 + 5) / 238) = ceil(4.22) = 5
    assert result == 5
