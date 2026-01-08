"""Simple web server to preview the generated blog article."""

from __future__ import annotations

import http.server
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


def render_blog(markdown_path: Path, output_path: Path) -> str:
    """Convert markdown to HTML blog page.

    Args:
        markdown_path: Path to the markdown file
        output_path: Path to write the HTML file

    Returns:
        The HTML content
    """
    import json
    import re

    # Read markdown
    md_content = markdown_path.read_text(encoding='utf-8')

    # Convert to HTML
    html_content = markdown.markdown(md_content)

    # Make all links open in a new tab
    html_content = html_content.replace('<a href=', '<a target="_blank" rel="noopener noreferrer" href=')

    # Get metadata from sources.json
    sources_path = markdown_path.parent / "sources.json"
    headline = "Daily AI Timeline"
    date_str = ""
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

        # Check for hero image
        if "hero_image" in sources and sources["hero_image"]:
            hero_image_path = sources["hero_image"]
    else:
        from datetime import datetime
        date_str = datetime.now().strftime("%A, %B %d, %Y")

    # Build hero section HTML
    hero_section = ""
    hero_file = markdown_path.parent / "hero.png"
    if hero_file.exists():
        hero_section = '<img src="hero.png" alt="Article hero image" class="hero-image">'

    # Render template using string.Template (uses $ instead of {})
    template = Template(get_html_template())
    full_html = template.substitute(
        date=date_str,
        headline=headline,
        hero_section=hero_section,
        content=html_content
    )

    # Write HTML
    output_path.write_text(full_html, encoding='utf-8')

    return full_html


def serve_blog(port: int = 8000, open_browser: bool = True):
    """Serve the blog on localhost.

    Args:
        port: Port to serve on
        open_browser: Whether to open browser automatically
    """
    # Find the output directory
    out_dir = Path("out")
    md_path = out_dir / "today.md"
    html_path = out_dir / "index.html"

    if not md_path.exists():
        print(f"Error: {md_path} not found. Run the generator first.")
        return

    # Render the blog
    print(f"Converting {md_path} to HTML...")
    render_blog(md_path, html_path)
    print(f"Created {html_path}")

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
