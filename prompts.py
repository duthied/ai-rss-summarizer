"""Custom prompts for different feed types"""

PROMPTS = {
    'news': """Article: {title}
Source: {source}
Content: {content}

Extract:
1. What happened (2-3 sentences) - the key facts
2. Key people/organizations involved
3. Geographic context (where this is happening)
4. Implications/impact - why this matters
5. Topics (3-5 tags for categorization)

Format as JSON:
{{
  "summary": "what happened in 2-3 sentences",
  "significance": "why it matters and impact",
  "entities": ["person/org 1", "person/org 2"],
  "location": "geographic context",
  "topics": ["topic1", "topic2", "topic3"]
}}""",

    'tech': """Article: {title}
Source: {source}
Content: {content}

Extract:
1. What was announced/discovered (2-3 sentences)
2. Technical significance - what's new or different
3. Business/industry impact
4. Companies/projects/technologies mentioned
5. Topics (3-5 tags)

Format as JSON:
{{
  "summary": "what was announced/discovered",
  "significance": "technical and business significance",
  "entities": ["company/project 1", "company/project 2"],
  "topics": ["topic1", "topic2", "topic3"]
}}""",

    'science': """Article: {title}
Source: {source}
Content: {content}

Extract:
1. Research finding/discovery (2-3 sentences)
2. Methodology (if mentioned - how they did it)
3. Implications for the field
4. Real-world applications or impact
5. Topics (3-5 tags)

Format as JSON:
{{
  "summary": "the research finding",
  "significance": "implications and applications",
  "methodology": "how they did it (if mentioned)",
  "topics": ["topic1", "topic2", "topic3"]
}}""",

    'culture': """Article: {title}
Source: {source}
Content: {content}

Extract:
1. Main point or story (2-3 sentences)
2. Cultural/social context - what makes this interesting
3. Key themes or ideas explored
4. Topics (3-5 tags)

Format as JSON:
{{
  "summary": "main point",
  "significance": "why this is culturally/socially interesting",
  "themes": ["theme 1", "theme 2"],
  "topics": ["topic1", "topic2", "topic3"]
}}""",

    'finance': """Article: {title}
Source: {source}
Content: {content}

Extract:
1. Financial development (2-3 sentences) - what changed
2. Market impact - who/what is affected
3. Numbers/data mentioned (if any)
4. Implications for investors or economy
5. Topics (3-5 tags)

Format as JSON:
{{
  "summary": "financial development",
  "significance": "market impact and implications",
  "data": "key numbers or metrics mentioned",
  "topics": ["topic1", "topic2", "topic3"]
}}""",

    'default': """Article: {title}
Source: {source}
Content: {content}

Extract:
1. Main point (2-3 sentences)
2. Why it matters
3. Topics (3-5 tags)

Format as JSON:
{{
  "summary": "main point",
  "significance": "why it matters",
  "topics": ["topic1", "topic2", "topic3"]
}}"""
}

# Feed source to category mapping
FEED_CATEGORIES = {
    # News sources
    'bbc': 'news',
    'aljazeera': 'news',
    'cbc': 'news',
    'cnn': 'news',
    'npr': 'news',
    'reuters': 'news',
    'guardian': 'news',
    'atlantic': 'news',
    'economist': 'news',
    'huffpost': 'news',
    'semafor': 'news',
    'vox': 'news',

    # Tech sources
    'tech': 'tech',
    'venturebeat': 'tech',
    'digital': 'tech',
    'dev.to': 'tech',
    'hacker': 'tech',
    'ycombinator': 'tech',
    'techcrunch': 'tech',
    'arstechnica': 'tech',
    'wired': 'tech',
    'gizmodo': 'tech',
    'geekwire': 'tech',
    'producthunt': 'tech',
    'techradar': 'tech',
    'verge': 'tech',
    'mashable': 'tech',
    'engadget': 'tech',
    'bleepingcomputer': 'tech',
    'krebsonsecurity': 'tech',

    # Science sources
    'science': 'science',
    'nature': 'science',
    'sciencedaily': 'science',
    'nasa': 'science',
    'deepmind': 'tech',  # AI research
    'openai': 'tech',
    'bair': 'tech',  # Berkeley AI Research

    # Culture sources
    'kottke': 'culture',
    'openculture': 'culture',
    'culture': 'culture',
    'apartment': 'culture',
    'oatmeal': 'culture',
    'xkcd': 'culture',
    'waitbutwhy': 'culture',
    'penny-arcade': 'culture',
    'giantitp': 'culture',
    'rockpapershotgun': 'culture',
    'steampowered': 'culture',

    # Finance sources
    'market': 'finance',
    'cnbc': 'finance',
    'economist': 'finance',
    'moneymorning': 'finance',
    'canadianvaluestocks': 'finance',
    'telegraph': 'finance',
    'businessinsider': 'finance',
    'entrepreneur': 'finance',
    'fastcompany': 'finance',
    'harvardbusiness': 'finance',
}


def get_prompt_for_source(source_name, item):
    """Select prompt based on feed source."""
    source_lower = source_name.lower()

    # Try to match feed category
    category = 'default'
    for keyword, cat in FEED_CATEGORIES.items():
        if keyword in source_lower:
            category = cat
            break

    # Get template
    template = PROMPTS.get(category, PROMPTS['default'])

    # Format with item data
    return template.format(
        title=item['title'],
        source=source_name,
        content=item.get('summary', '')[:2000]  # Limit content length
    )


def get_category_for_source(source_name):
    """Get category for a source (for debugging/logging)."""
    source_lower = source_name.lower()
    for keyword, cat in FEED_CATEGORIES.items():
        if keyword in source_lower:
            return cat
    return 'default'
