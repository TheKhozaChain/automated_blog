"""Simple web server to preview the generated blog article."""

from __future__ import annotations

import http.server
import json
import socketserver
import webbrowser
from pathlib import Path
from string import Template

import markdown


def get_html_template() -> str:
    """Return the HTML template for the blog."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$headline - Daily AI Timeline</title>
    <meta property="og:title" content="$headline">
    <meta property="og:image" content="hero.png">
    <meta property="og:type" content="article">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Georgia', 'Times New Roman', serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #e8e8e8;
            line-height: 1.8;
        }

        .container {
            max-width: 780px;
            margin: 0 auto;
            padding: 60px 30px;
        }

        header {
            text-align: center;
            margin-bottom: 50px;
            padding-bottom: 30px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        header .brand {
            font-size: 0.9rem;
            font-weight: 400;
            letter-spacing: 3px;
            text-transform: uppercase;
            color: #64ffda;
            margin-bottom: 20px;
        }

        header .date {
            font-size: 0.9rem;
            color: #8892b0;
            font-style: italic;
            margin-bottom: 15px;
        }

        header .reading-time {
            font-size: 0.85rem;
            color: #64ffda;
            font-weight: 500;
            letter-spacing: 1px;
            margin-bottom: 25px;
        }

        .hero-image {
            width: 100%;
            max-width: 100%;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.4);
        }

        .headline {
            font-size: 2.2rem;
            font-weight: 700;
            color: #fff;
            line-height: 1.3;
            margin-top: 20px;
        }

        article {
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            padding: 50px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.05);
        }

        article h1 {
            display: none;
        }

        article p {
            margin-bottom: 1.8em;
            font-size: 1.1rem;
            color: #ccd6f6;
        }

        article p:first-of-type {
            font-size: 1.3rem;
            font-weight: 600;
            color: #fff;
            border-left: 3px solid #64ffda;
            padding-left: 20px;
            margin-bottom: 2em;
        }

        article p:last-of-type {
            font-size: 1.2rem;
            font-weight: 600;
            color: #64ffda;
            margin-top: 2em;
            padding-top: 1.5em;
            border-top: 1px solid rgba(255,255,255,0.1);
        }

        article a {
            color: #64ffda;
            text-decoration: none;
            border-bottom: 1px solid rgba(100, 255, 218, 0.3);
            transition: all 0.2s ease;
        }

        article a:hover {
            color: #fff;
            border-bottom-color: #64ffda;
            background: rgba(100, 255, 218, 0.1);
            padding: 2px 4px;
            margin: -2px -4px;
            border-radius: 3px;
        }

        article strong {
            color: #fff;
            font-weight: 600;
        }

        footer {
            text-align: center;
            margin-top: 50px;
            padding-top: 30px;
            border-top: 1px solid rgba(255,255,255,0.1);
            color: #8892b0;
            font-size: 0.85rem;
        }

        footer a {
            color: #64ffda;
            text-decoration: none;
        }

        @media (max-width: 600px) {
            .container {
                padding: 30px 20px;
            }
            article {
                padding: 30px 25px;
            }
            article p {
                font-size: 1rem;
            }
            article p:first-of-type {
                font-size: 1.1rem;
            }
            .headline {
                font-size: 1.6rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <p class="brand">Daily AI Timeline</p>
            <p class="date">$date</p>
            $reading_time_section
            $hero_section
            <h1 class="headline">$headline</h1>
        </header>

        <article>
            $content
        </article>

        <footer>
            <p>Generated with <a href="#">Daily AI Timeline</a></p>
        </footer>
    </div>
</body>
</html>
"""


def render_blog(markdown_path: Path, output_path: Path, is_archive: bool = False) -> str:
    """Convert markdown to HTML blog page.

    Args:
        markdown_path: Path to the markdown file
        output_path: Path to write the HTML file
        is_archive: Whether this is an archived article

    Returns:
        The HTML content
    """
    import re

    # Read markdown
    md_content = markdown_path.read_text(encoding='utf-8')

    # Convert to HTML
    html_content = markdown.markdown(md_content)

    # Make all links open in a new tab
    html_content = html_content.replace('<a href=', '<a target="_blank" rel="noopener noreferrer" href=')

    # Get metadata from sources.json
    if is_archive:
        # For archive, use dated JSON file
        date_stem = markdown_path.stem
        sources_path = markdown_path.parent / f"{date_stem}.json"
    else:
        sources_path = markdown_path.parent / "sources.json"

    headline = "Daily AI Timeline"
    date_str = ""
    reading_time_minutes = None
    hero_image_path = None

    if sources_path.exists():
        with open(sources_path, 'r') as f:
            sources = json.load(f)
        from dateutil import parser as date_parser
        generated_dt = date_parser.parse(sources["generated_at"])
        date_str = generated_dt.strftime("%A, %B %d, %Y")

        # Get headline from sources.json
        if "headline" in sources and sources["headline"]:
            headline = sources["headline"]

        # Get reading time from sources.json
        if "reading_time_minutes" in sources:
            reading_time_minutes = sources["reading_time_minutes"]

        # Check for hero image
        if "hero_image" in sources and sources["hero_image"]:
            hero_image_path = sources["hero_image"]
    else:
        from datetime import datetime
        date_str = datetime.now().strftime("%A, %B %d, %Y")

    # Build reading time section HTML
    reading_time_section = ""
    if reading_time_minutes:
        reading_time_section = f'<p class="reading-time">{reading_time_minutes} min read</p>'

    # Build hero section HTML
    hero_section = ""
    if is_archive:
        # For archive, check for dated hero image
        date_str = markdown_path.stem
        hero_file = markdown_path.parent / f"{date_str}.png"
        if hero_file.exists():
            hero_section = f'<img src="{date_str}.png" alt="Article hero image" class="hero-image">'
    else:
        hero_file = markdown_path.parent / "hero.png"
        if hero_file.exists():
            hero_section = '<img src="hero.png" alt="Article hero image" class="hero-image">'

    # Render template using string.Template (uses $ instead of {})
    template = Template(get_html_template())
    full_html = template.substitute(
        date=date_str,
        headline=headline,
        reading_time_section=reading_time_section,
        hero_section=hero_section,
        content=html_content
    )

    # Write HTML
    output_path.write_text(full_html, encoding='utf-8')

    return full_html


def get_archive_template() -> str:
    """Return the HTML template for the archive page."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Archive - Daily AI Timeline</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Georgia', 'Times New Roman', serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #e8e8e8;
            line-height: 1.8;
        }

        .container {
            max-width: 780px;
            margin: 0 auto;
            padding: 60px 30px;
        }

        header {
            text-align: center;
            margin-bottom: 50px;
            padding-bottom: 30px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        header .brand {
            font-size: 0.9rem;
            font-weight: 400;
            letter-spacing: 3px;
            text-transform: uppercase;
            color: #64ffda;
            margin-bottom: 20px;
        }

        header .brand a {
            color: #64ffda;
            text-decoration: none;
        }

        h1 {
            font-size: 2.2rem;
            font-weight: 700;
            color: #fff;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #8892b0;
            font-style: italic;
        }

        .archive-list {
            list-style: none;
        }

        .archive-item {
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            padding: 25px 30px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.05);
            transition: all 0.2s ease;
        }

        .archive-item:hover {
            background: rgba(255,255,255,0.06);
            border-color: rgba(100, 255, 218, 0.2);
        }

        .archive-item a {
            text-decoration: none;
        }

        .archive-date {
            font-size: 0.85rem;
            color: #64ffda;
            margin-bottom: 8px;
            letter-spacing: 1px;
        }

        .archive-headline {
            font-size: 1.3rem;
            color: #fff;
            font-weight: 600;
            margin-bottom: 8px;
        }

        .archive-meta {
            font-size: 0.9rem;
            color: #8892b0;
        }

        footer {
            text-align: center;
            margin-top: 50px;
            padding-top: 30px;
            border-top: 1px solid rgba(255,255,255,0.1);
            color: #8892b0;
            font-size: 0.85rem;
        }

        footer a {
            color: #64ffda;
            text-decoration: none;
        }

        .empty-state {
            text-align: center;
            padding: 60px 30px;
            color: #8892b0;
        }

        @media (max-width: 600px) {
            .container {
                padding: 30px 20px;
            }
            .archive-item {
                padding: 20px;
            }
            h1 {
                font-size: 1.6rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <p class="brand"><a href="index.html">Daily AI Timeline</a></p>
            <h1>Archive</h1>
            <p class="subtitle">Past editions of the Daily AI Timeline</p>
        </header>

        <ul class="archive-list">
            $archive_items
        </ul>

        <footer>
            <p>Generated with <a href="#">Daily AI Timeline</a></p>
        </footer>
    </div>
</body>
</html>
"""


def render_archive(output_dir: Path) -> str:
    """Generate the archive page listing all past articles.

    Args:
        output_dir: Directory containing the archive folder

    Returns:
        The HTML content
    """
    archive_dir = output_dir / "archive"
    archive_items_html = ""

    if archive_dir.exists():
        # Find all JSON files in archive (they contain metadata)
        json_files = sorted(archive_dir.glob("*.json"), reverse=True)

        for json_path in json_files:
            date_str = json_path.stem  # e.g., "2026-01-09"
            try:
                with open(json_path, 'r') as f:
                    metadata = json.load(f)

                headline = metadata.get("headline", "Untitled")
                reading_time = metadata.get("reading_time_minutes", 0)
                item_count = metadata.get("item_count", 0)

                # Format date nicely
                from dateutil import parser as date_parser
                generated_dt = date_parser.parse(metadata["generated_at"])
                formatted_date = generated_dt.strftime("%A, %B %d, %Y")

                archive_items_html += f"""
            <li class="archive-item">
                <a href="archive/{date_str}.html">
                    <p class="archive-date">{formatted_date}</p>
                    <h2 class="archive-headline">{headline}</h2>
                    <p class="archive-meta">{reading_time} min read · {item_count} stories</p>
                </a>
            </li>
"""
            except Exception as e:
                print(f"Warning: Could not read archive metadata {json_path}: {e}")
                continue

    if not archive_items_html:
        archive_items_html = '<li class="empty-state">No archived articles yet. Run the generator to create your first post!</li>'

    template = Template(get_archive_template())
    html = template.substitute(archive_items=archive_items_html)

    # Save archive page
    archive_path = output_dir / "archive.html"
    archive_path.write_text(html, encoding='utf-8')

    return html


def render_archive_articles(output_dir: Path):
    """Render all archived markdown articles to HTML.

    Args:
        output_dir: Directory containing the archive folder
    """
    archive_dir = output_dir / "archive"
    if not archive_dir.exists():
        return

    # Find all markdown files in archive
    md_files = archive_dir.glob("*.md")

    for md_path in md_files:
        date_str = md_path.stem  # e.g., "2026-01-09"
        html_path = archive_dir / f"{date_str}.html"

        # Use the same render function but with archive paths
        render_blog(md_path, html_path, is_archive=True)


def serve_blog(port: int = 8000, open_browser: bool = True, output_dir: str = "out"):
    """Serve the blog on localhost.

    Args:
        port: Port to serve on
        open_browser: Whether to open browser automatically
        output_dir: Directory containing the blog files
    """
    # Find the output directory
    out_dir = Path(output_dir)
    md_path = out_dir / "today.md"
    html_path = out_dir / "index.html"

    if not md_path.exists():
        print(f"Error: {md_path} not found. Run the generator first.")
        return

    # Render the blog
    print(f"Converting {md_path} to HTML...")
    render_blog(md_path, html_path)
    print(f"Created {html_path}")

    # Render archive page
    print("Generating archive page...")
    render_archive(out_dir)
    print("Created archive.html")

    # Render archived articles
    print("Rendering archived articles...")
    render_archive_articles(out_dir)
    print("Archive articles rendered")

    # Change to output directory
    import os
    os.chdir(out_dir)

    # Create server
    handler = http.server.SimpleHTTPRequestHandler

    with socketserver.TCPServer(("", port), handler) as httpd:
        url = f"http://localhost:{port}"
        print(f"\n{'='*50}")
        print(f"Blog is live at: {url}")
        print(f"{'='*50}")
        print("Press Ctrl+C to stop the server\n")

        if open_browser:
            webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    serve_blog()
