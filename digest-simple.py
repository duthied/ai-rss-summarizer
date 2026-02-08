#!/usr/bin/env python3
"""Phase 1: Minimal viable digest - single-pass approach"""

import os
import feedparser
from anthropic import Anthropic
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def fetch_feeds(urls, max_items=3):
    """Fetch items from RSS feeds."""
    items = []

    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_items]:
                items.append({
                    'source': feed.feed.get('title', 'Unknown'),
                    'title': entry.get('title', 'Untitled'),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', '')[:500]  # Truncate
                })
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")

    return items

def create_digest(items):
    """Create digest using single Claude call."""
    client = Anthropic()

    # Build compact prompt with links
    items_text = "\n\n".join([
        f"**{item['source']}**: {item['title']}\nURL: {item['link']}\n{item['summary']}"
        for item in items
    ])

    prompt = f"""Create a daily digest from these feed items:

{items_text}

Write a brief report with:
1. Executive Summary (2-3 sentences)
2. Key Themes (3-5 themes, with each point including a [title](link) to the relevant story)
3. Top Stories (5-7 most interesting stories with [Title](link) format and brief explanation)

IMPORTANT: Every interesting point should include a clickable markdown link so readers can learn more. Use the actual URLs from the feed items provided above.

Be concise and focus on actionable insights."""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text

def main():
    # Read feeds from feeds.md
    with open('feeds.md') as f:
        urls = []
        for line in f:
            line = line.strip()
            # Handle both plain URLs and markdown list format
            if line.startswith('- http'):
                urls.append(line[2:])  # Remove '- ' prefix
            elif line.startswith('http'):
                urls.append(line)

    print(f"Fetching {len(urls)} feeds...")
    items = fetch_feeds(urls, max_items=10)
    print(f"Collected {len(items)} items\n")

    print("Generating digest...")
    digest = create_digest(items)

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"reports/digest_simple_{timestamp}.md"

    with open(output_file, 'w') as f:
        f.write(f"# Daily Digest - {datetime.now().strftime('%B %d, %Y')}\n\n")
        f.write(digest)

    print(f"\n✓ Saved to {output_file}\n")
    print(digest[:500] + "...")

if __name__ == "__main__":
    main()
