#!/usr/bin/env python3
"""Feed item deduplication module.

Tracks previously processed feed items to avoid duplicate summaries.
Uses a hybrid approach with fallback chain: GUID → Normalized Link → Title+Date composite.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


def normalize_link(url):
    """Remove tracking parameters from URLs.

    Strips common tracking parameters like utm_*, at_*, fbclid, etc.
    to normalize URLs for deduplication.

    Args:
        url: URL string to normalize

    Returns:
        Normalized URL string without tracking parameters
    """
    if not url:
        return ''

    try:
        parsed = urlparse(url)

        # Common tracking parameters to remove
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
            'at_medium', 'at_campaign', 'at_custom1', 'at_custom2', 'at_custom3',
            'fbclid', 'gclid', 'msclkid', 'mc_cid', 'mc_eid',
            'ref', 'source', 'campaign'
        }

        # Parse and filter query parameters
        clean_params = {
            k: v for k, v in parse_qs(parsed.query).items()
            if k not in tracking_params
        }

        # Reconstruct URL without tracking params
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(clean_params, doseq=True),
            ''  # Remove fragment
        ))
    except Exception as e:
        logging.warning(f"Failed to normalize URL: {url} - {e}")
        return url


def get_item_identifier(entry):
    """Generate stable unique identifier for feed entry.

    Uses fallback chain for maximum reliability:
    1. GUID (entry.id) - most stable, designed for this purpose
    2. Normalized link - strips tracking params
    3. Title + published date composite - last resort

    Args:
        entry: feedparser entry object

    Returns:
        Tuple of (id_type, identifier) where id_type is 'guid', 'link', or 'composite'
    """
    # Priority 1: Use feed GUID (most stable)
    if hasattr(entry, 'id') and entry.id:
        return ('guid', entry.id)

    # Priority 2: Normalized link (remove tracking params)
    if entry.get('link'):
        normalized = normalize_link(entry.link)
        if normalized:
            return ('link', normalized)

    # Priority 3: Title + published date composite
    title_slug = entry.get('title', 'untitled')[:100].lower().strip()
    pub_date = entry.get('published', '')[:10]  # Just YYYY-MM-DD
    return ('composite', f"{title_slug}|{pub_date}")


class DedupState:
    """Track seen feed items across runs with rolling time window.

    Maintains a JSON state file with seen items and their metadata.
    Automatically cleans up entries older than lookback_days.
    """

    def __init__(self, state_file='reports/.dedup_state.json', lookback_days=7):
        """Initialize deduplication state.

        Args:
            state_file: Path to JSON state file
            lookback_days: Number of days to track history (older entries auto-deleted)
        """
        self.state_file = Path(state_file)
        self.lookback_days = lookback_days
        self.state = self._load_or_create()

    def _load_or_create(self):
        """Load existing state or create new one.

        Returns:
            State dictionary with 'version', 'last_cleanup', and 'items' keys
        """
        if not self.state_file.exists():
            logging.info(f"  Creating new dedup state file: {self.state_file}")
            return {
                'version': '1.0',
                'last_cleanup': datetime.now().isoformat(),
                'items': {}
            }

        try:
            with open(self.state_file) as f:
                state = json.load(f)
                logging.info(f"  Loaded dedup state: {len(state.get('items', {}))} items tracked")
                return state
        except json.JSONDecodeError as e:
            # Corrupted - backup and start fresh
            backup_file = self.state_file.with_suffix('.corrupt')
            logging.warning(f"  Corrupted state file, backing up to {backup_file}")
            self.state_file.rename(backup_file)
            return self._load_or_create()
        except Exception as e:
            logging.error(f"  Failed to load state file: {e}")
            return self._load_or_create()

    def is_seen(self, item_id):
        """Check if item was processed before.

        Args:
            item_id: Unique identifier string (from get_item_identifier)

        Returns:
            True if item was seen in previous runs
        """
        return item_id in self.state['items']

    def mark_seen(self, item_id, source, title):
        """Mark item as seen with metadata.

        If item already exists, updates last_seen and increments fetch_count.
        Otherwise creates new entry.

        Args:
            item_id: Unique identifier string
            source: Feed source name
            title: Item title (truncated to 100 chars)
        """
        now = datetime.now().isoformat()

        if item_id in self.state['items']:
            # Update existing entry
            self.state['items'][item_id]['last_seen'] = now
            self.state['items'][item_id]['fetch_count'] += 1
        else:
            # Create new entry
            self.state['items'][item_id] = {
                'first_seen': now,
                'last_seen': now,
                'fetch_count': 1,
                'source': source,
                'title': title[:100]
            }

    def cleanup_old_entries(self):
        """Remove entries older than lookback_days.

        Entries are kept based on their last_seen timestamp.
        """
        cutoff = datetime.now() - timedelta(days=self.lookback_days)

        items_before = len(self.state['items'])
        self.state['items'] = {
            k: v for k, v in self.state['items'].items()
            if datetime.fromisoformat(v['last_seen'].replace('Z', '')) > cutoff
        }

        removed = items_before - len(self.state['items'])
        if removed > 0:
            logging.info(f"  🗑️  Cleaned up {removed} old entries (kept {len(self.state['items'])} items)")

    def save(self):
        """Save state atomically to disk.

        Uses temp file + rename for atomic write to prevent corruption.
        """
        try:
            self.state['last_cleanup'] = datetime.now().isoformat()

            # Ensure parent directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            # Write to temp file then rename (atomic)
            tmp_file = self.state_file.with_suffix('.tmp')
            with open(tmp_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            tmp_file.rename(self.state_file)

            logging.debug(f"  Saved dedup state: {len(self.state['items'])} items")
        except Exception as e:
            logging.error(f"  Failed to save dedup state: {e}")

    def get_stats(self):
        """Get statistics about dedup state.

        Returns:
            Dictionary with stats: total_items, oldest_entry, newest_entry
        """
        if not self.state['items']:
            return {
                'total_items': 0,
                'oldest_entry': None,
                'newest_entry': None
            }

        timestamps = [
            datetime.fromisoformat(v['last_seen'].replace('Z', ''))
            for v in self.state['items'].values()
        ]

        return {
            'total_items': len(self.state['items']),
            'oldest_entry': min(timestamps),
            'newest_entry': max(timestamps)
        }
