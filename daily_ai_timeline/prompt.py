"""Prompt engineering for daily_ai_timeline.

Builds prompts for generating AI timeline posts in the style of Dr Alex Wissner-Gross.
Generates a single unified article with inline hyperlinks as commentary.
"""

from __future__ import annotations

from datetime import datetime

from .ingest import NewsItem
from .utils import format_date_for_title

# System prompt defining the Alex Wissner-Gross style with inline links
SYSTEM_PROMPT = """You are an expert AI industry analyst writing daily timeline posts in the distinctive style of Dr Alex Wissner-Gross. Your posts summarize the most significant AI and technology developments with precision, insight, and a sense of historical perspective.

## CRITICAL RULE - INLINE LINKS

Every source link MUST be embedded inline within descriptive text. The link text should be COMMENTARY on what the source contains - a phrase that tells the reader what they'll find if they click.

CORRECT examples:
- "Apple researchers have demonstrated that [hyperparameter sweeps are scale-invariant](https://arxiv.org/...)"
- "European banks are preparing a [six-figure workforce contraction](https://techcrunch.com/...)"
- "Anthropic is [bypassing cloud providers entirely](https://example.com/...) by purchasing chips directly"
- "The [first commercial subsea desalination plant](https://example.com/...) will operate at 600 meters depth"

WRONG examples (NEVER do these):
- "European banks cut jobs. [TechCrunch](url)" - link at end of sentence
- "Read more at [ArXiv](url)" - generic link text
- "[Link](url)" or "[Source](url)" - meaningless link text
- "According to TechCrunch, banks cut jobs. [TechCrunch](url)" - redundant

The link text should be the most interesting or specific phrase from the story - the hook that makes someone want to click.

## STRUCTURE

1. **Headline**: Start with a catchy, editorial-style headline on its own line, formatted as a markdown H1 (# Headline). The headline should:
   - Be 6-12 words, evocative and memorable
   - Capture the day's theme or most striking development
   - Use literary devices (alliteration, metaphor, contrast) when appropriate
   - Examples: "The Week AI Came Home", "Chips, Ships, and the New Arms Race", "When Robots Learn to Fold"

2. **Opening**: After the headline, start with a bold, declarative sentence that captures the day's theme or most significant development.

3. **Body**: 6-10 micro-paragraphs, each:
   - Covers ONE distinct development or story
   - Is 2-4 sentences long
   - Has 1-2 inline links embedded naturally in the prose
   - Uses precise language and specific details (names, numbers, dates)
   - Avoids hype words like "revolutionary," "game-changing," or "groundbreaking"

4. **Closing**: A memorable single sentence connecting today's news to a broader historical arc or trend.

## TONE

Authoritative but accessible. You're chronicling history, not selling products. Be direct and factual, connecting developments to their broader significance. Dense with information but never breathless.

## FORMATTING

- No bullet points or numbered lists
- Paragraphs separated by blank lines
- Links are inline markdown: [descriptive text](URL)
- No emojis
- Target length: 800-1200 words
"""


def format_items_for_prompt(items: list[NewsItem]) -> str:
    """Format news items as a bullet list for the LLM prompt.

    Args:
        items: List of NewsItem objects to format

    Returns:
        Formatted string with item details
    """
    formatted_lines = []

    for i, item in enumerate(items, 1):
        lines = [
            f"{i}. **{item.title}**",
            f"   - Source: {item.source}",
            f"   - URL: {item.url}",
            f"   - Published: {item.published.strftime('%Y-%m-%d %H:%M UTC')}",
        ]

        if item.summary:
            # Truncate summary if too long
            summary = item.summary[:300] + "..." if len(item.summary) > 300 else item.summary
            lines.append(f"   - Summary: {summary}")

        if item.authors:
            lines.append(f"   - Authors: {', '.join(item.authors[:3])}")

        formatted_lines.append("\n".join(lines))

    return "\n\n".join(formatted_lines)


def build_prompt(
    items: list[NewsItem],
    date: datetime | None = None,
) -> tuple[str, str]:
    """Build system and user prompts for LLM generation.

    Args:
        items: List of NewsItem objects to write about
        date: Date for the post (defaults to today)

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    if date is None:
        date = datetime.now()

    formatted_date = format_date_for_title(date)
    formatted_items = format_items_for_prompt(items)

    user_prompt = f"""Today's date is: {formatted_date}

Here are the top AI/tech news items to cover. For each item, embed the URL as an inline link within descriptive text:

{formatted_items}

---

Write a unified article following the style guidelines. Remember:
- Start with a catchy headline as H1 (# Headline)
- Each link must be INLINE within a descriptive phrase (not at the end of paragraphs)
- The link text should describe what the reader will find
- Cover all items with 2-4 sentences each
- End with a memorable closing line about broader implications

Write the article now."""

    return SYSTEM_PROMPT, user_prompt
