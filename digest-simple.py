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
    """Create digest using single Claude call. Returns (digest_text, usage_stats, cost)."""
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
        max_tokens=3000,  # Increased to handle larger digests
        messages=[{"role": "user", "content": prompt}]
    )

    # Extract usage stats
    usage = response.usage
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens

    # Calculate cost (Claude Sonnet 4.5 pricing)
    # Input: $3.00 per million tokens, Output: $15.00 per million tokens
    input_cost = (input_tokens / 1_000_000) * 3.00
    output_cost = (output_tokens / 1_000_000) * 15.00
    total_cost = input_cost + output_cost

    usage_stats = {
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'total_tokens': input_tokens + output_tokens,
        'cost': total_cost
    }

    return response.content[0].text, usage_stats

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
    digest, usage_stats = create_digest(items)

    # Add usage stats to digest
    usage_footer = f"""

---

## 📊 Generation Stats

**Token Usage:**
- Input tokens: {usage_stats['input_tokens']:,}
- Output tokens: {usage_stats['output_tokens']:,}
- Total tokens: {usage_stats['total_tokens']:,}

**Cost:** ${usage_stats['cost']:.4f}

**Items processed:** {len(items)} from {len(urls)} feeds
"""

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"reports/digest_simple_{timestamp}.md"

    with open(output_file, 'w') as f:
        f.write(f"# Daily Digest - {datetime.now().strftime('%B %d, %Y')}\n\n")
        f.write(digest)
        f.write(usage_footer)

    print(f"\n✓ Saved to {output_file}")
    print(f"💰 Cost: ${usage_stats['cost']:.4f} ({usage_stats['total_tokens']:,} tokens)")
    print(f"\n{digest[:500]}...")

if __name__ == "__main__":
    main()
