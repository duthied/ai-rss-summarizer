#!/usr/bin/env python3
"""Phase 2: Multi-phase pipeline with parallel processing"""

import os
import json
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import feedparser
from anthropic import Anthropic
from dotenv import load_dotenv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()


class FeedFetcher:
    """Phase 1: Fetch items from RSS feeds"""

    def __init__(self, max_items_per_feed=10):
        self.max_items_per_feed = max_items_per_feed

    def fetch_all(self, urls):
        """Fetch items from all feeds."""
        print(f"\n📥 PHASE 1: Fetching from {len(urls)} feeds...")
        items = []

        for url in urls:
            print(f"  Fetching: {url[:60]}...")
            try:
                feed = feedparser.parse(url, request_headers={'User-Agent': 'RSS-Summarizer/1.0'})

                if feed.bozo and hasattr(feed, 'bozo_exception'):
                    print(f"  ⚠️  Warning: {feed.bozo_exception}")

                for entry in feed.entries[:self.max_items_per_feed]:
                    items.append({
                        'source': feed.feed.get('title', 'Unknown'),
                        'title': entry.get('title', 'Untitled'),
                        'link': entry.get('link', ''),
                        'summary': entry.get('summary', entry.get('description', ''))[:1000],
                        'published': entry.get('published', '')
                    })
                print(f"  ✓ Got {min(len(feed.entries), self.max_items_per_feed)} items")
            except Exception as e:
                print(f"  ✗ Failed: {e}")

        print(f"\n✓ Fetched {len(items)} total items")
        return items


class ItemSummarizer:
    """Phase 2: Summarize individual items in parallel using Haiku"""

    def __init__(self, model="claude-haiku-4-5-20251001", max_workers=5):
        self.client = Anthropic()
        self.model = model
        self.max_workers = max_workers

    def summarize_item(self, item):
        """Summarize a single item."""
        prompt = f"""Summarize this article concisely:

Title: {item['title']}
Source: {item['source']}
URL: {item['link']}
Content: {item['summary']}

Provide:
1. One-sentence summary (what happened/what's new)
2. Why it matters (impact/significance)
3. 2-3 key topics/tags

Format as JSON:
{{
  "summary": "...",
  "significance": "...",
  "topics": ["topic1", "topic2", "topic3"]
}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse JSON response
            summary_text = response.content[0].text
            # Extract JSON from potential markdown code blocks
            if "```json" in summary_text:
                summary_text = summary_text.split("```json")[1].split("```")[0].strip()
            elif "```" in summary_text:
                summary_text = summary_text.split("```")[1].split("```")[0].strip()

            summary_data = json.loads(summary_text)

            return {
                **item,
                'ai_summary': summary_data.get('summary', ''),
                'significance': summary_data.get('significance', ''),
                'topics': summary_data.get('topics', []),
                'tokens': {
                    'input': response.usage.input_tokens,
                    'output': response.usage.output_tokens
                }
            }
        except Exception as e:
            print(f"  ✗ Failed to summarize: {item['title'][:50]}... - {e}")
            return {
                **item,
                'ai_summary': item['summary'][:200],
                'significance': '',
                'topics': [],
                'tokens': {'input': 0, 'output': 0}
            }

    def summarize_all(self, items):
        """Summarize all items in parallel."""
        print(f"\n🤖 PHASE 2: Summarizing {len(items)} items with {self.model}...")
        summaries = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.summarize_item, item): item for item in items}

            for i, future in enumerate(as_completed(futures), 1):
                result = future.result()
                summaries.append(result)
                if i % 10 == 0:
                    print(f"  Progress: {i}/{len(items)} items summarized")

        # Calculate total tokens
        total_input = sum(s['tokens']['input'] for s in summaries)
        total_output = sum(s['tokens']['output'] for s in summaries)

        print(f"✓ Summarized {len(summaries)} items")
        print(f"  Tokens: {total_input:,} input, {total_output:,} output")

        return summaries


class ThemeLinker:
    """Phase 3: Find themes and connections across summaries"""

    def __init__(self, model="claude-haiku-4-5-20251001"):
        self.client = Anthropic()
        self.model = model

    def find_connections(self, summaries):
        """Analyze summaries to find themes and connections."""
        print(f"\n🔗 PHASE 3: Finding themes and connections...")

        # Build compact representation
        items_text = "\n".join([
            f"- [{s['source']}] {s['title']}: {s.get('ai_summary', s['summary'][:100])}"
            for s in summaries
        ])

        prompt = f"""Analyze these {len(summaries)} news items and identify major themes and connections.

{items_text}

Find 3-5 overarching themes that connect multiple stories, and interesting connections between items.

Return ONLY valid JSON in this exact format (no additional fields):
{{
  "themes": [
    {{"name": "Theme name", "description": "Why it matters", "story_indices": [0, 3, 7]}},
    {{"name": "Another theme", "description": "Its significance", "story_indices": [2, 5, 9]}}
  ],
  "connections": [
    {{"items": [1, 5], "connection": "How they relate"}},
    {{"items": [3, 8], "connection": "Their relationship"}}
  ]
}}

IMPORTANT: Return ONLY the JSON object, nothing else. Include only "themes" and "connections" fields."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,  # Increased for complete response
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse JSON response with better error handling
            themes_text = response.content[0].text

            # Try to extract JSON from code blocks
            if "```json" in themes_text:
                themes_text = themes_text.split("```json")[1].split("```")[0].strip()
            elif "```" in themes_text:
                themes_text = themes_text.split("```")[1].split("```")[0].strip()

            # Try to find JSON object if it's embedded in other text
            if not themes_text.startswith('{'):
                # Look for first { and last }
                start = themes_text.find('{')
                end = themes_text.rfind('}') + 1
                if start != -1 and end > start:
                    themes_text = themes_text[start:end]

            try:
                themes_data = json.loads(themes_text)
            except json.JSONDecodeError as je:
                # Save problematic response for debugging
                print(f"  ⚠️  JSON parse error, saving raw response to debug")
                with open(f"{os.path.dirname(os.path.abspath(__file__))}/theme_debug.txt", 'w') as f:
                    f.write(themes_text)
                raise je

            print(f"✓ Found {len(themes_data.get('themes', []))} themes")
            print(f"  Tokens: {response.usage.input_tokens:,} input, {response.usage.output_tokens:,} output")

            return {
                **themes_data,
                'tokens': {
                    'input': response.usage.input_tokens,
                    'output': response.usage.output_tokens
                }
            }
        except Exception as e:
            print(f"  ✗ Failed to find themes: {e}")
            print(f"  Continuing without theme analysis...")
            return {'themes': [], 'connections': [], 'tokens': {'input': 0, 'output': 0}}


class DigestSynthesizer:
    """Phase 4: Synthesize final digest using Sonnet"""

    def __init__(self, model="claude-sonnet-4-5-20250929"):
        self.client = Anthropic()
        self.model = model

    def synthesize(self, summaries, themes):
        """Create final digest from summaries and themes."""
        print(f"\n✨ PHASE 4: Synthesizing final digest with {self.model}...")

        # Build summaries text
        summaries_text = "\n\n".join([
            f"**[{s['source']}]** {s['title']}\n"
            f"URL: {s['link']}\n"
            f"Summary: {s.get('ai_summary', s['summary'][:200])}\n"
            f"Significance: {s.get('significance', 'N/A')}\n"
            f"Topics: {', '.join(s.get('topics', []))}"
            for s in summaries
        ])

        # Build themes text
        themes_text = "\n\n".join([
            f"**{t['name']}**: {t['description']}"
            for t in themes.get('themes', [])
        ])

        prompt = f"""Create a comprehensive daily digest from these pre-summarized articles.

THEMES IDENTIFIED:
{themes_text}

ARTICLE SUMMARIES:
{summaries_text}

Write a digest with:

1. **Executive Summary** (2-3 sentences highlighting the most significant developments)

2. **Key Themes** (3-5 themes, each with 2-3 bullet points linking to specific stories)
   - Each bullet should include a [title](URL) link to the story
   - Explain why the theme matters

3. **Top Stories** (7-10 most important/interesting stories)
   - Format: **[Title](URL)** - Why it matters and key takeaways
   - Prioritize impact, novelty, and reader value

IMPORTANT: Include clickable markdown links throughout. Be concise but insightful."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        digest = response.content[0].text

        print(f"✓ Generated digest")
        print(f"  Tokens: {response.usage.input_tokens:,} input, {response.usage.output_tokens:,} output")

        return {
            'digest': digest,
            'tokens': {
                'input': response.usage.input_tokens,
                'output': response.usage.output_tokens
            }
        }


def send_email(digest_text, stats_text):
    """Send digest via email using SMTP."""

    # Check if email is enabled
    if os.getenv('SEND_EMAIL', 'false').lower() != 'true':
        print("📧 Email delivery disabled (SEND_EMAIL=false)")
        return False

    # Get SMTP configuration
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    email_from = os.getenv('EMAIL_FROM', smtp_username)
    email_to = os.getenv('EMAIL_TO')

    if not all([smtp_host, smtp_username, smtp_password, email_to]):
        print("⚠️  Email not configured properly - check .env file")
        return False

    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Daily Digest - {datetime.now().strftime('%B %d, %Y')}"
        msg['From'] = email_from
        msg['To'] = email_to

        # Convert markdown to simple HTML-friendly format
        # This is basic - we could use a proper markdown->HTML converter later
        html_body = f"""
        <html>
          <head>
            <style>
              body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                     line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
              h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
              h2 {{ color: #34495e; margin-top: 30px; }}
              h3 {{ color: #7f8c8d; }}
              a {{ color: #3498db; text-decoration: none; }}
              a:hover {{ text-decoration: underline; }}
              .stats {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 30px; font-size: 0.9em; }}
              hr {{ border: none; border-top: 1px solid #eee; margin: 30px 0; }}
            </style>
          </head>
          <body>
            <div style="white-space: pre-wrap;">{digest_text}</div>
            <div class="stats" style="white-space: pre-wrap;">{stats_text}</div>
          </body>
        </html>
        """

        # Attach both plain text and HTML versions
        text_part = MIMEText(digest_text + "\n\n" + stats_text, 'plain')
        html_part = MIMEText(html_body, 'html')

        msg.attach(text_part)
        msg.attach(html_part)

        # Send email
        print(f"\n📧 Sending email to {email_to}...")
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)

        print(f"✓ Email sent successfully!")
        return True

    except Exception as e:
        print(f"✗ Failed to send email: {e}")
        return False


def main():
    start_time = time.time()

    # Read feeds
    with open('feeds.md') as f:
        urls = []
        for line in f:
            line = line.strip()
            if line.startswith('- http'):
                urls.append(line[2:])
            elif line.startswith('http'):
                urls.append(line)

    # Create output directory
    now = datetime.now()
    month_folder = now.strftime("%B-%Y")
    day_folder = now.strftime("%Y-%m-%d")
    output_dir = f"reports/{month_folder}/{day_folder}"
    os.makedirs(output_dir, exist_ok=True)

    # Phase 1: Fetch
    fetcher = FeedFetcher(max_items_per_feed=10)
    items = fetcher.fetch_all(urls)

    # Save raw items
    with open(f"{output_dir}/01_items.json", 'w') as f:
        json.dump(items, f, indent=2, default=str)

    # Phase 2: Summarize
    summarizer = ItemSummarizer(max_workers=5)
    summaries = summarizer.summarize_all(items)

    # Save summaries
    with open(f"{output_dir}/02_summaries.json", 'w') as f:
        json.dump(summaries, f, indent=2, default=str)

    # Phase 3: Link themes
    linker = ThemeLinker()
    themes = linker.find_connections(summaries)

    # Save themes
    with open(f"{output_dir}/03_themes.json", 'w') as f:
        json.dump(themes, f, indent=2, default=str)

    # Phase 4: Synthesize
    synthesizer = DigestSynthesizer()
    result = synthesizer.synthesize(summaries, themes)

    # Calculate total cost
    haiku_input_cost = 0.80  # per million
    haiku_output_cost = 4.00
    sonnet_input_cost = 3.00
    sonnet_output_cost = 15.00

    total_tokens = {
        'haiku_input': sum(s['tokens']['input'] for s in summaries) + themes['tokens']['input'],
        'haiku_output': sum(s['tokens']['output'] for s in summaries) + themes['tokens']['output'],
        'sonnet_input': result['tokens']['input'],
        'sonnet_output': result['tokens']['output']
    }

    total_cost = (
        (total_tokens['haiku_input'] / 1_000_000 * haiku_input_cost) +
        (total_tokens['haiku_output'] / 1_000_000 * haiku_output_cost) +
        (total_tokens['sonnet_input'] / 1_000_000 * sonnet_input_cost) +
        (total_tokens['sonnet_output'] / 1_000_000 * sonnet_output_cost)
    )

    execution_time = time.time() - start_time

    # Add stats footer
    stats_footer = f"""

---

## 📊 Generation Stats

**Execution Time:** {execution_time:.1f}s

**Token Usage:**
- Haiku: {total_tokens['haiku_input']:,} input, {total_tokens['haiku_output']:,} output
- Sonnet: {total_tokens['sonnet_input']:,} input, {total_tokens['sonnet_output']:,} output
- Total: {sum(total_tokens.values()):,} tokens

**Cost Breakdown:**
- Haiku: ${(total_tokens['haiku_input']/1_000_000 * haiku_input_cost + total_tokens['haiku_output']/1_000_000 * haiku_output_cost):.4f}
- Sonnet: ${(total_tokens['sonnet_input']/1_000_000 * sonnet_input_cost + total_tokens['sonnet_output']/1_000_000 * sonnet_output_cost):.4f}
- **Total: ${total_cost:.4f}**

**Items processed:** {len(items)} from {len(urls)} feeds
"""

    # Save final digest
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_dir}/digest_pipeline_{timestamp}.md"

    with open(output_file, 'w') as f:
        f.write(f"# Daily Digest - {now.strftime('%B %d, %Y')}\n\n")
        f.write(result['digest'])
        f.write(stats_footer)

    print(f"\n{'='*60}")
    print(f"✓ Digest complete!")
    print(f"📄 Saved to: {output_file}")
    print(f"⏱️  Execution time: {execution_time:.1f}s")
    print(f"💰 Total cost: ${total_cost:.4f}")
    print(f"{'='*60}")

    # Send email if enabled
    send_email(result['digest'], stats_footer)


if __name__ == "__main__":
    main()
