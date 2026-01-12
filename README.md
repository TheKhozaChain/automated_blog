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
- **Niche System**: Create multiple blogs for different topics/industries using YAML configs

---

## Quick Start (TL;DR)

```bash
# 1. Activate your virtual environment
source venv/bin/activate

# 2. Generate today's AI News blog (Dr. Alex Wissner-Gross style)
python -m daily_ai_timeline run --mode daily

# 3. View it in your browser
python -m daily_ai_timeline serve
```

Then open **http://localhost:8000** in your browser.

---

## Running Multiple Blogs (Main + Niches)

You can run the **main AI News blog** alongside **custom niche blogs** on different ports:

```bash
# 1. Generate the main AI News blog (Dr. Alex style) → out-daily/
python -m daily_ai_timeline run --mode daily --output out-daily

# 2. Generate a niche blog (e.g., AI Jobs Australia) → out-jobs-au/
python -m daily_ai_timeline run --niche ai_jobs_au --mode daily

# 3. Serve both on different ports
python -m daily_ai_timeline serve --dir out-daily --port 8000      # Main AI News
python -m daily_ai_timeline serve --dir out-jobs-au --port 8001    # AI Jobs AU
```

| Blog | Command | URL |
|------|---------|-----|
| **Main AI News** (Dr. Alex style) | `run --mode daily` | http://localhost:8000 |
| **AI Jobs Australia** (niche) | `run --niche ai_jobs_au` | http://localhost:8001 |

> **Note:** The main blog uses Dr. Alex Wissner-Gross's analytical style. Niches inherit this style but add their own voice/audience customization.

---

## Creating Custom Niches

Niches let you create topic-specific blogs (jobs, crypto, healthcare AI, etc.) without copying the codebase.

### List Available Niches

```bash
python -m daily_ai_timeline niches
```

### Run a Niche

```bash
# Run the AI Jobs Australia niche
python -m daily_ai_timeline run --niche ai_jobs_au --mode daily

# View sources configured for a niche
python -m daily_ai_timeline sources --niche ai_jobs_au
```

### Creating a New Niche

1. Create a YAML file in the `niches/` directory:

```yaml
# niches/my_niche.yaml
name: "My Custom Niche"
description: "Daily digest of my topic"
output_dir: "out-my-niche"

branding:
  site_name: "My Custom Blog"
  tagline: "Your daily digest of my topic"

# RSS feeds to fetch from
rss_feeds:
  Source Name: "https://example.com/feed.xml"

# arXiv categories (empty list to disable)
arxiv_categories: []

# Hacker News search keywords
hn_keywords:
  - "keyword1"
  - "keyword2"

# Reddit subreddits to monitor
reddit_subreddits:
  - "subreddit1"
  - "subreddit2"

# Source credibility scores (0-20)
source_credibility:
  Source Name: 15
  Reddit r/subreddit1: 10

# Keywords that boost item scores
scoring_keywords:
  - "important"
  - "breaking"

# Customize the LLM prompt
prompts:
  voice: |
    Write as a [topic] expert.
    Focus on practical insights.
  article_type: "news analysis"
  audience: "professionals in [industry]"
  geographic_focus: "Australia"  # optional
```

2. Run your new niche:

```bash
python -m daily_ai_timeline run --niche my_niche --mode daily
python -m daily_ai_timeline serve --dir out-my-niche --port 8003
```

### Included Configurations

| Name | Description | Output Dir | Style |
|------|-------------|------------|-------|
| *(default)* | Main AI News blog | `out/` | Dr. Alex Wissner-Gross |
| `ai_jobs_au` | AI job opportunities in Australia | `out-jobs-au/` | Job market analyst |

> **All blogs use the Dr. Alex Wissner-Gross analytical style as a base.** Niches add topic-specific voice and audience customization on top.

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
  --niche, -n NAME              Niche configuration to use (default: ai_news)
  --mode {daily,realtime,weekly}  Run mode:
                                    daily    = 24h lookback (default)
                                    realtime = 1h lookback
                                    weekly   = 7-day lookback
  --top N                         Number of top items (default: 10)
  --output, -o DIR                Output directory (overrides niche default)
  --fetch-content                 Fetch full article content (slower)
  --quiet, -q                     Suppress progress bars
```

**Examples:**

```bash
# Standard daily run (uses ai_news niche)
python -m daily_ai_timeline run --mode daily

# Weekly roundup with 15 items
python -m daily_ai_timeline run --mode weekly --top 15

# Run a different niche
python -m daily_ai_timeline run --niche ai_jobs_au --mode daily
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

### Niches Command

List available niche configurations.

```bash
python -m daily_ai_timeline niches
```

### Sources Command

List configured news sources for a niche.

```bash
python -m daily_ai_timeline sources --niche ai_news
python -m daily_ai_timeline sources --niche ai_jobs_au
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
│   ├── config.py        # Configuration + NicheConfig
│   ├── ingest.py        # Source fetching
│   ├── dedupe.py        # Deduplication & scoring
│   ├── prompt.py        # LLM prompts
│   ├── generator.py     # LLM integration
│   ├── server.py        # Local blog server
│   └── utils.py         # Utilities
├── niches/              # Niche configuration files
│   ├── ai_news.yaml     # Default AI news niche
│   └── ai_jobs_au.yaml  # AI jobs in Australia
├── tests/
├── out/                 # Default output
├── pyproject.toml
└── README.md
```

## License

MIT License
