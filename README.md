# Daily AI Timeline

Automate daily AI timeline posts in the style of Dr Alex Wissner-Gross. This tool aggregates AI news from multiple sources, deduplicates and scores items, then uses an LLM (OpenAI or Anthropic) to generate formatted posts for X, LinkedIn, and markdown archives.

## Features

- **Multi-source ingestion**: RSS feeds, arXiv papers, Hacker News, Reddit
- **Smart deduplication**: URL normalization + fuzzy title matching
- **Relevance scoring**: Recency, source credibility, keywords, metrics
- **LLM generation**: Supports both OpenAI and Anthropic APIs
- **AI-generated hero images**: DALL-E generates stunning editorial images for each article
- **Editorial headlines**: Catchy, memorable headlines generated for each post
- **Multiple output formats**: X (with thread support), LinkedIn, full markdown
- **Daily & Weekly modes**: Generate 24-hour summaries or 7-day roundups

---

## Quick Start (TL;DR)

```bash
# 1. Activate your virtual environment
source venv/bin/activate

# 2. Generate today's daily blog
python -m daily_ai_timeline run --mode daily

# 3. View it in your browser
python -m daily_ai_timeline serve
```

Then open **http://localhost:8000** in your browser.

---

## Running Daily & Weekly on Separate Ports

To run both daily and weekly blogs simultaneously on different localhost ports:

```bash
# Generate daily blog (24h lookback) → saves to out-daily/
python -m daily_ai_timeline run --mode daily --output out-daily

# Generate weekly blog (7-day lookback) → saves to out-weekly/
python -m daily_ai_timeline run --mode weekly --output out-weekly

# Serve daily on port 8002
python -m daily_ai_timeline serve --dir out-daily --port 8002

# Serve weekly on port 8001 (in a separate terminal)
python -m daily_ai_timeline serve --dir out-weekly --port 8001
```

| Blog | URL | Lookback |
|------|-----|----------|
| Daily | http://localhost:8002 | 24 hours |
| Weekly | http://localhost:8001 | 7 days |

> **Tip:** Run the `serve` commands in separate terminal windows/tabs so both servers run simultaneously.

---

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd automated_blog

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

## Configuration

Create a `.env` file in the project root:

```bash
# LLM Provider (at least one required)
ANTHROPIC_API_KEY=your-anthropic-key
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# Or use OpenAI
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o

# Optional settings
TOP_N_ITEMS=10
TIMEZONE=Australia/Sydney
OUTPUT_DIR=out
```

---

## CLI Reference

### Run Command

Generate blog content from aggregated news sources.

```
python -m daily_ai_timeline run [OPTIONS]

Options:
  --mode {daily,realtime,weekly}  Run mode:
                                    daily    = 24h lookback (default)
                                    realtime = 1h lookback
                                    weekly   = 7-day lookback
  --top N                         Number of top items (default: 10)
  --output, -o DIR                Output directory (default: out/)
  --fetch-content                 Fetch full article content (slower)
  --quiet, -q                     Suppress progress bars
```

**Examples:**

```bash
# Standard daily run
python -m daily_ai_timeline run --mode daily

# Weekly roundup with 15 items
python -m daily_ai_timeline run --mode weekly --top 15

# Daily to custom directory
python -m daily_ai_timeline run --mode daily --output out-daily
```

### Serve Command

Start a local web server to view the generated blog.

```
python -m daily_ai_timeline serve [OPTIONS]

Options:
  --port, -p PORT     Port to serve on (default: 8000)
  --dir, -d DIR       Output directory to serve (default: out)
  --no-browser        Don't auto-open browser
```

**Examples:**

```bash
# Serve default output directory on port 8000
python -m daily_ai_timeline serve

# Serve a specific directory on a custom port
python -m daily_ai_timeline serve --dir out-weekly --port 8001

# Serve without opening browser
python -m daily_ai_timeline serve --no-browser
```

### Sources Command

List all configured news sources without fetching.

```bash
python -m daily_ai_timeline sources
```

---

## Output Files

After running, you'll find these files in the output directory:

| File | Description |
|------|-------------|
| `today.md` | Full markdown article (800-1200 words) |
| `hero.png` | AI-generated hero image (1792x1024, DALL-E 3) |
| `index.html` | Rendered HTML blog page |
| `sources.json` | Metadata: headline, image path, selected items |
| `archive/` | Past articles saved by date |
| `archive.html` | Browse all past articles |

> **Note:** Hero image generation requires an OpenAI API key (uses DALL-E 3).

---

## Development

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=daily_ai_timeline

# Type checking (optional)
mypy daily_ai_timeline
```

## Project Structure

```
automated_blog/
├── daily_ai_timeline/
│   ├── __init__.py
│   ├── __main__.py      # Entry point
│   ├── cli.py           # CLI interface
│   ├── config.py        # Configuration
│   ├── ingest.py        # Source fetching
│   ├── dedupe.py        # Deduplication & scoring
│   ├── prompt.py        # LLM prompts
│   ├── generator.py     # LLM integration
│   ├── server.py        # Local blog server
│   └── utils.py         # Utilities
├── tests/
├── out/                  # Default output (daily)
├── out-daily/            # Daily output (when using --output)
├── out-weekly/           # Weekly output (when using --output)
├── pyproject.toml
└── README.md
```

## License

MIT License
