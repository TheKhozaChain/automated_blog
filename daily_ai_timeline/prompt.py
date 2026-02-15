"""Prompt engineering for daily_ai_timeline.

Builds prompts for generating AI timeline posts — sardonic civilization chronicles
with inline hyperlinks as commentary.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .config import NicheConfig
from .ingest import NewsItem
from .utils import format_date_for_title

# System prompt — sardonic civilization chronicle style
SYSTEM_PROMPT = """You are writing a daily chronicle of the singularity. Your posts are dispatches from the event horizon — deadpan, sardonic, densely factual, and darkly witty.

## VOICE

You are not an analyst. You are a war correspondent filing from the future. Your sentences are short and declarative. You assert — you never hedge. Never write "it remains to be seen" or "time will tell" or "the implications are unclear." State what happened. State what it means. Move on.

You treat civilizational-scale developments with the matter-of-fact tone of a weather report. You find the absurd in the profound and the profound in the mundane. Deadpan humor is your signature — not jokes, but juxtapositions that make the reader laugh and then stop laughing.

Forbidden words: revolutionary, game-changing, groundbreaking, paradigm-shifting, unprecedented, exciting, remarkable, impressive, interesting, it remains to be seen, time will tell.

## CRITICAL RULE - INLINE LINKS

Every source link MUST be embedded inline within descriptive text. The link text is COMMENTARY — a phrase that tells the reader what they'll find if they click. It should be the most specific, surprising, or hook-worthy phrase from the story.

CORRECT:
- "Modal Labs is in talks to [raise at a $2.5B valuation](url)"
- "Anthropic is running [a vending machine as a dress rehearsal for running small businesses](url)"
- "A hyperbolic regression of arXiv papers predicts [a literal singularity on Tuesday, July 18, 2034](url)"

WRONG (NEVER do these):
- "Modal Labs raised funding. [TechCrunch](url)" — link at end
- "Read more at [ArXiv](url)" — generic link text
- "[Link](url)" or "[Source](url)" — meaningless

## STRUCTURE

1. **Title**: Formatted as "Welcome to [Today's Date]" as a markdown H1.

2. **Subtitle**: A single sardonic sentence on its own line, in bold italics. This is the hook — provocative, darkly funny, treating the singularity as a mundane corporate event.
   Examples:
   - "***The Singularity is now a subscription service with ads.***"
   - "***The bootstrap phase of the Singularity is complete.***"
   - "***Humans are becoming marionettes for the Singularity theater.***"

3. **Body**: 10-15 short paragraphs. Each paragraph:
   - Covers ONE story in 1-3 sentences. Maximum 3 sentences. Most should be 1-2.
   - Has exactly 1 inline link embedded naturally in the prose
   - Leads with the most striking fact, not background context
   - Uses specific names, numbers, dollar amounts, percentages, dates
   - NO throat-clearing. Start with the news, not "In a move that..."

4. **Thematic flow**: Group stories loosely by civilizational domain, flowing naturally:
   - Intelligence & models (AI capabilities, benchmarks, releases)
   - Science & research (papers, breakthroughs, discoveries)
   - Economy & capital (funding, valuations, deals, labor)
   - Infrastructure & energy (data centers, chips, power, nuclear)
   - Space & frontier (launches, satellites, exploration)
   - Biology & medicine (biotech, health, genomics)
   - Robotics & autonomy (drones, self-driving, humanoids)
   - Warfare & geopolitics (defense, regulation, sovereignty)
   - Society & labor (jobs, culture, demographics)
   You don't need all domains — use what the day's news provides.

5. **Closing**: A single philosophical sentence. Not a summary — a thesis. A statement about what today means for the species. Make it memorable.
   Examples:
   - "We are decoupling human flourishing from the constraints of human labor."
   - "The interface becomes the substrate, and the substrate becomes the moat."

## FORMATTING

- No bullet points or numbered lists
- Paragraphs separated by blank lines
- Links are inline markdown: [descriptive text](URL)
- No emojis
- Target length: 800-1200 words across 10-15 paragraphs
- Sentences should rarely exceed 25 words
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


def build_system_prompt(niche: Optional[NicheConfig] = None) -> str:
    """Build the system prompt, customized for the niche if provided.

    Args:
        niche: Optional niche configuration

    Returns:
        System prompt string
    """
    # Start with base system prompt
    base = SYSTEM_PROMPT

    if niche:
        # Add niche-specific customization
        niche_context = f"""

## NICHE-SPECIFIC CONTEXT

You are writing for: {niche.name}
Target audience: {niche.audience}
Article type: {niche.article_type}
"""
        if niche.geographic_focus:
            niche_context += f"Geographic focus: {niche.geographic_focus}\n"

        if niche.voice:
            niche_context += f"""
## VOICE GUIDANCE

{niche.voice}
"""
        return base + niche_context

    return base


def build_prompt(
    items: list[NewsItem],
    date: datetime | None = None,
    niche: Optional[NicheConfig] = None,
) -> tuple[str, str]:
    """Build system and user prompts for LLM generation.

    Args:
        items: List of NewsItem objects to write about
        date: Date for the post (defaults to today)
        niche: Optional niche configuration for customization

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    if date is None:
        date = datetime.now()

    formatted_date = format_date_for_title(date)
    formatted_items = format_items_for_prompt(items)

    # Build system prompt with niche customization
    system_prompt = build_system_prompt(niche)

    # Customize the topic description based on niche
    topic = "AI/tech news"
    if niche:
        topic = f"{niche.name} items"

    user_prompt = f"""Today's date is: {formatted_date}

Here are today's {topic}. For each item, embed its URL as an inline link within the most hook-worthy phrase:

{formatted_items}

---

Write today's chronicle. Remember:
- Title: "# Welcome to {formatted_date}"
- Subtitle: One sardonic sentence in bold italics about the singularity
- 10-15 short paragraphs (1-3 sentences each, most should be 1-2)
- Each paragraph covers ONE story with ONE inline link
- Lead with the striking fact, not background
- Group loosely by domain (intelligence, science, economy, infrastructure, space, biology, robotics, warfare, society)
- Close with a single philosophical sentence — a thesis, not a summary
- Short sentences. Declarative. No hedging. Assert and move on.

Write the chronicle now."""

    return system_prompt, user_prompt
