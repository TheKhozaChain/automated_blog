# Foundation Documentation

This document provides detailed technical information about the Daily AI Timeline project.

## Architecture Overview

The system follows a pipeline architecture:

```
Sources → Ingestion → Deduplication → Scoring → Generation → Output
```

### 1. Source Ingestion (`ingest.py`)

Fetches AI news from three source types:

#### RSS Feeds
- OpenAI Blog: `https://openai.com/blog/rss.xml`
- Anthropic Blog: `https://www.anthropic.com/rss.xml`
- DeepMind Blog: `https://deepmind.google/blog/rss.xml`
- The Verge AI: `https://www.theverge.com/rss/ai-artificial-intelligence/index.xml`
- TechCrunch AI: `https://techcrunch.com/category/artificial-intelligence/feed/`
- MIT Tech Review AI: `https://www.technologyreview.com/topic/artificial-intelligence/feed`
- Ars Technica: `https://feeds.arstechnica.com/arstechnica/technology-lab`
- Wired AI: `https://www.wired.com/feed/tag/ai/latest/rss`

#### arXiv
- Categories: `cs.AI`, `cs.LG`
- API: Export API with Atom feed parsing
- Extracts: Title, abstract, authors, URL, date

#### Hacker News
- API: Algolia Search API
- Keywords: AI, OpenAI, Anthropic, Claude, Gemini, NVIDIA, LLM, GPT, machine learning, neural network
- Filters: Minimum points, recency

### 2. Deduplication (`dedupe.py`)

Two-phase deduplication:

1. **URL Normalization**
   - Removes `www.` prefix
   - Strips tracking parameters (utm_*, ref, fbclid, etc.)
   - Lowercases domain
   - Removes trailing slashes

2. **Fuzzy Title Matching**
   - Uses `difflib.SequenceMatcher`
   - Threshold: 0.85 similarity
   - Keeps higher-credibility source on match

### 3. Scoring Algorithm

Items are scored on a 0-75 point scale:

| Factor | Points | Description |
|--------|--------|-------------|
| Recency | 0-30 | `max(0, 30 - hours_old)` |
| Source Credibility | 0-20 | Based on source reputation |
| Numbers | 0-10 | Monetary amounts, metrics, dates |
| Keywords | 0-15 | High-value terms (release, launch, AGI, etc.) |

#### Source Credibility Scores
- OpenAI/Anthropic/DeepMind Blog: 20
- arXiv: 18
- MIT Tech Review: 15
- TechCrunch: 12
- The Verge/Ars Technica/Wired: 10
- Hacker News: 8
- Unknown: 5

### 4. LLM Integration (`generator.py`)

Supports two providers with automatic fallback:

```python
# Provider selection logic
if ANTHROPIC_API_KEY is set:
    use Anthropic (Claude)
elif OPENAI_API_KEY is set:
    use OpenAI (GPT)
else:
    raise error
```

#### Generation Flow
1. Build prompts for each output type
2. Call LLM with style-enforcing system prompt
3. Validate outputs (character limits)
4. Build X thread if needed
5. Save all outputs

### 5. Output Formats

#### Full Post (`today.md`)
- 1500-2000 words
- Complete style with all paragraphs
- All source links included

#### LinkedIn (`today_linkedin.txt`)
- 900-1400 characters
- Top 3-4 developments
- Ends with engagement hook

#### X Single Tweet (`today_x.txt`)
- Max 280 characters
- Most significant development
- Punchy, memorable

#### X Thread
- 3-6 tweets
- First: Hook + "Thread:"
- Middle: One development each
- Last: Closing thought + CTA

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | One of these | - | Anthropic API key |
| `OPENAI_API_KEY` | required | - | OpenAI API key |
| `ANTHROPIC_MODEL` | No | `claude-3-sonnet-20240229` | Anthropic model |
| `OPENAI_MODEL` | No | `gpt-4o` | OpenAI model |
| `TOP_N_ITEMS` | No | `10` | Items to include |
| `TIMEZONE` | No | `Australia/Sydney` | Timezone for dates |
| `OUTPUT_DIR` | No | `out` | Output directory |
| `LOOKBACK_HOURS_DAILY` | No | `24` | Hours for daily mode |
| `LOOKBACK_HOURS_REALTIME` | No | `1` | Hours for realtime mode |

## Scheduling Examples

### Cron (Linux/macOS)

```bash
# Daily at 7:05 AM
5 7 * * * /usr/bin/env bash -lc 'cd /path/to/daily_ai_timeline && source venv/bin/activate && python -m daily_ai_timeline run --mode daily'

# Hourly realtime updates
0 * * * * /usr/bin/env bash -lc 'cd /path/to/daily_ai_timeline && source venv/bin/activate && python -m daily_ai_timeline run --mode realtime'
```

### launchd (macOS)

Create `~/Library/LaunchAgents/com.dailyaitimeline.daily.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dailyaitimeline.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>cd /path/to/daily_ai_timeline && source venv/bin/activate && python -m daily_ai_timeline run --mode daily</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>7</integer>
        <key>Minute</key>
        <integer>5</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/path/to/daily_ai_timeline/logs/daily.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/daily_ai_timeline/logs/daily.err</string>
</dict>
</plist>
```

Load with:
```bash
launchctl load ~/Library/LaunchAgents/com.dailyaitimeline.daily.plist
```

### systemd (Linux)

Create `/etc/systemd/system/daily-ai-timeline.service`:

```ini
[Unit]
Description=Daily AI Timeline Generator
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/path/to/daily_ai_timeline
ExecStart=/path/to/daily_ai_timeline/venv/bin/python -m daily_ai_timeline run --mode daily
User=youruser
Environment=PATH=/path/to/daily_ai_timeline/venv/bin

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/daily-ai-timeline.timer`:

```ini
[Unit]
Description=Run Daily AI Timeline at 7:05 AM

[Timer]
OnCalendar=*-*-* 07:05:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable with:
```bash
sudo systemctl enable --now daily-ai-timeline.timer
```

## Troubleshooting

### No items fetched
- Check internet connectivity
- Verify RSS feed URLs are accessible
- Increase `LOOKBACK_HOURS_*` if sources have fewer updates

### LLM errors
- Verify API keys are set correctly
- Check API quota/billing status
- Try switching to the other provider

### Output too short/long
- LinkedIn validation is informational; content still saved
- Adjust prompts in `prompt.py` if consistently wrong length

### Rate limiting
- Add delays between source fetches if needed
- Consider caching results for realtime mode

## Extending the System

### Adding new RSS feeds
Edit `config.py`:
```python
RSS_FEEDS = {
    # ... existing feeds
    "New Source": "https://example.com/feed.xml",
}
SOURCE_CREDIBILITY = {
    # ... existing sources
    "New Source": 12,
}
```

### Adding new scoring keywords
Edit `config.py`:
```python
SCORING_KEYWORDS = [
    # ... existing keywords
    "new_keyword",
]
```

### Custom output formats
Add new output type in `prompt.py`:
```python
OUTPUT_INSTRUCTIONS = {
    # ... existing types
    "custom": """Your custom instructions here...""",
}
```
