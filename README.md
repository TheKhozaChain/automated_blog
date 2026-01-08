# Daily AI Timeline

Automate daily AI timeline posts in the style of Dr Alex Wissner-Gross. This tool aggregates AI news from multiple sources, deduplicates and scores items, then uses an LLM (OpenAI or Anthropic) to generate formatted posts for X, LinkedIn, and markdown archives.

## Features

- **Multi-source ingestion**: RSS feeds, arXiv papers, Hacker News
- **Smart deduplication**: URL normalization + fuzzy title matching
- **Relevance scoring**: Recency, source credibility, keywords, metrics
- **LLM generation**: Supports both OpenAI and Anthropic APIs
- **AI-generated hero images**: DALL-E generates stunning editorial images for each article
- **Editorial headlines**: Catchy, memorable headlines generated for each post
- **Multiple output formats**: X (with thread support), LinkedIn, full markdown

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd daily_ai_timeline

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### 2. Configuration

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

### 3. Generate Content

```bash
# Generate daily post (last 24 hours)
python -m daily_ai_timeline run --mode daily

# Generate realtime update (last hour)
python -m daily_ai_timeline run --mode realtime

# Override number of items
python -m daily_ai_timeline run --top 15

# List configured sources
python -m daily_ai_timeline sources
```

### 4. View the Blog

After generating content, start the local server to view your blog:

```bash
# Start the server and open in browser
python -m daily_ai_timeline serve

# Or specify a custom port
python -m daily_ai_timeline serve --port 3000

# Start without auto-opening browser
python -m daily_ai_timeline serve --no-browser
```

Then open http://localhost:8000 in your browser.

> **Note:** You must run `serve` after each `run` to see updated content. The `run` command generates the markdown files, while `serve` converts them to HTML and starts the web server.

## Output Files

After running, you'll find these files in `out/`:

- `today.md` - Full markdown post with headline (800-1200 words)
- `hero.png` - AI-generated hero image (1792x1024, DALL-E 3)
- `index.html` - Rendered HTML blog page
- `sources.json` - Metadata including headline, image path, and selected items

> **Note:** Hero image generation requires an OpenAI API key (uses DALL-E 3).

## CLI Options

### Run Command
```
python -m daily_ai_timeline run [OPTIONS]

Options:
  --mode {daily,realtime}  Run mode (default: daily)
  --top N                  Number of top items (default: 10)
  --output, -o DIR         Output directory (default: out/)
  --fetch-content          Fetch full article content
  --quiet, -q              Suppress progress bars
```

### Serve Command
```
python -m daily_ai_timeline serve [OPTIONS]

Options:
  --port, -p PORT          Port to serve on (default: 8000)
  --no-browser             Don't auto-open browser
```

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
daily_ai_timeline/
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
├── out/                  # Generated outputs
├── pyproject.toml
└── README.md
```

## License

MIT License
