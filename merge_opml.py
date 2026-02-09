#!/usr/bin/env python3
"""Merge feeds from OPML into feeds.md, avoiding duplicates."""

import xml.etree.ElementTree as ET
import re

def normalize_url(url):
    """Normalize URL for comparison (remove http/https, trailing slashes, etc.)"""
    url = url.lower().strip()
    url = re.sub(r'^https?://', '', url)
    url = url.rstrip('/')
    return url

def parse_opml(file_path):
    """Parse OPML file and extract feeds organized by category."""
    tree = ET.parse(file_path)
    root = tree.getroot()

    feeds_by_category = {}

    # Find all outline elements
    body = root.find('body')
    for category_outline in body.findall('outline'):
        category_title = category_outline.get('title', 'Uncategorized')

        # Check if this outline has nested outlines (it's a category)
        nested_outlines = category_outline.findall('outline')
        if nested_outlines:
            # This is a category with feeds
            feeds = []
            for feed_outline in nested_outlines:
                xml_url = feed_outline.get('xmlUrl')
                if xml_url:
                    title = feed_outline.get('title', feed_outline.get('text', ''))
                    feeds.append({
                        'url': xml_url,
                        'title': title
                    })
            if feeds:
                feeds_by_category[category_title] = feeds
        else:
            # This is a standalone feed (not in a category)
            xml_url = category_outline.get('xmlUrl')
            if xml_url:
                title = category_outline.get('title', category_outline.get('text', ''))
                if 'Uncategorized' not in feeds_by_category:
                    feeds_by_category['Uncategorized'] = []
                feeds_by_category['Uncategorized'].append({
                    'url': xml_url,
                    'title': title
                })

    return feeds_by_category

def parse_existing_feeds(file_path):
    """Parse existing feeds.md and extract all URLs."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Extract all URLs from markdown links
    url_pattern = r'- (https?://[^\s\)]+)'
    urls = re.findall(url_pattern, content)

    # Normalize all URLs
    normalized_urls = {normalize_url(url) for url in urls}

    return normalized_urls, content

def add_feeds_to_md(opml_file, md_file):
    """Add new feeds from OPML to feeds.md."""
    # Parse OPML
    feeds_by_category = parse_opml(opml_file)

    # Parse existing feeds
    existing_normalized_urls, existing_content = parse_existing_feeds(md_file)

    # Find new feeds by category
    new_feeds_by_category = {}
    total_new = 0
    total_duplicates = 0

    for category, feeds in feeds_by_category.items():
        new_feeds = []
        for feed in feeds:
            normalized = normalize_url(feed['url'])
            if normalized not in existing_normalized_urls:
                new_feeds.append(feed)
                total_new += 1
            else:
                total_duplicates += 1

        if new_feeds:
            new_feeds_by_category[category] = new_feeds

    print(f"Found {total_new} new feeds to add")
    print(f"Skipped {total_duplicates} duplicate feeds")

    if not new_feeds_by_category:
        print("No new feeds to add!")
        return

    # Build the new content to append
    new_content_parts = []

    for category, feeds in sorted(new_feeds_by_category.items()):
        new_content_parts.append(f"\n## {category}")
        for feed in sorted(feeds, key=lambda x: x['title'].lower()):
            new_content_parts.append(f"- {feed['url']}")

    # Append to existing content
    updated_content = existing_content.rstrip() + '\n' + '\n'.join(new_content_parts) + '\n'

    # Write back
    with open(md_file, 'w') as f:
        f.write(updated_content)

    print(f"\nAdded {total_new} new feeds to {md_file}")
    print("\nNew feeds by category:")
    for category, feeds in sorted(new_feeds_by_category.items()):
        print(f"  {category}: {len(feeds)} feeds")

if __name__ == '__main__':
    add_feeds_to_md('Feeder-2026-02-08.opml', 'feeds.md')
