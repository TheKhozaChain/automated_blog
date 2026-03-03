# Daily AI Timeline

Automated AI news blog that aggregates content from multiple sources, scores and deduplicates items, then uses an LLM to generate a polished daily article with an AI-generated hero image. Serve it locally and view it in your browser.

## Features

- **Multi-source ingestion**: RSS feeds, arXiv papers, Hacker News, Reddit, X/Twitter
- **Smart deduplication**: URL normalization + fuzzy title matching
- **Relevance scoring**: Recency, source credibility, keywords, metrics
- **LLM generation**: Supports both OpenAI and Anthropic APIs
- **AI-generated hero images**: DALL-E generates editorial images for each article
- **Editorial headlines**: Catchy headlines generated for each post
- **Multiple output formats**: Full markdown, rendered HTML blog
- **Daily & Weekly modes**: 24-hour summaries or 7-day roundups
- **Niche system**: Create topic-specific blogs using YAML configs

---

## Getting Started

### 1. Clone & install

```bash
git clone <repository-url>
cd automated_blog

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -e ".[dev]"
```

### 2. Configure API keys

```bash
cp .env.example .env
```

Edit `.env` and add at least one LLM provider key:

```bash
# Required — at least one of these:
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here    # also needed for hero image generation (DALL-E)
```

### 3. Generate today's blog

```bash
python -m daily_ai_timeline run --mode daily
```

### 4. View it locally

```bash
python -m daily_ai_timeline serve
```

Open **http://localhost:8000** in your browser.

---

## CLI Reference

### `run` — Generate blog content

```bash
python -m daily_ai_timeline run [OPTIONS]

Options:
  --mode {daily,realtime,weekly}   daily (24h), realtime (1h), weekly (7 days)
  --top N                          Number of top items (default: 10)
  --output, -o DIR                 Output directory
  --niche, -n NAME                 Niche config to use (default: ai_news)
  --fetch-content                  Fetch full article content (slower)
  --quiet, -q                      Suppress progress output
```

### `serve` — Preview in browser

```bash
python -m daily_ai_timeline serve [OPTIONS]

Options:
  --port, -p PORT     Port (default: 8000)
  --dir, -d DIR       Output directory to serve (default: out)
  --no-browser        Don't auto-open browser
```

### `sources` — Show configured news sources

```bash
python -m daily_ai_timeline sources
```

### `niches` — List available niche configs

```bash
python -m daily_ai_timeline niches
```

---

## Output Files

After running, you'll find these in the output directory:

| File | Description |
|------|-------------|
| `today.md` | Full markdown article |
| `hero.png` | AI-generated hero image (DALL-E 3) |
| `index.html` | Rendered HTML blog page |
| `sources.json` | Metadata: headline, image path, selected items |
| `archive/` | Past articles saved by date |
| `archive.html` | Browse past articles |

---

## Creating a Custom Niche

You can create topic-specific blogs by adding a YAML file in `niches/`:

```yaml
# niches/my_topic.yaml
name: "My Topic Blog"
description: "Daily digest of my topic"
output_dir: "out-my-topic"

branding:
  site_name: "My Topic Blog"
  tagline: "Your daily digest"

rss_feeds:
  Source Name: "https://example.com/feed.xml"

arxiv_categories: []

hn_keywords:
  - "keyword1"

reddit_subreddits:
  - "subreddit1"

scoring_keywords:
  - "important"

prompts:
  voice: |
    Write as a topic expert.
  article_type: "news analysis"
  audience: "professionals"
```

Then run it:

```bash
python -m daily_ai_timeline run --niche my_topic --mode daily
python -m daily_ai_timeline serve --dir out-my-topic
```

---

## Development

```bash
pytest                          # Run tests
pytest --cov=daily_ai_timeline  # With coverage
```

## Project Structure

```
automated_blog/
├── daily_ai_timeline/     # Core package
│   ├── cli.py             # CLI interface
│   ├── config.py          # Configuration + NicheConfig
│   ├── ingest.py          # Source fetching
│   ├── dedupe.py          # Deduplication & scoring
│   ├── prompt.py          # LLM prompts
│   ├── generator.py       # LLM integration
│   ├── server.py          # Local blog server
│   └── utils.py           # Utilities
├── niches/                # Niche YAML configs
│   └── ai_news.yaml       # Default AI news config
├── tests/
├── pyproject.toml
└── README.md
```

## License

MIT License
