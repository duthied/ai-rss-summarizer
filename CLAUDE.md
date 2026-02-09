# CLAUDE.md

This file provides guidance to Claude Code and other AI assistants when working with this repository.

## Project Overview

This is an **RSS feed summarizer** that generates daily digests using Claude AI. It fetches items from multiple RSS feeds, summarizes them using AI, identifies themes, and sends a formatted digest via email.

**Key insight:** This project evolved from a simple single-pass approach (Phase 1) to a cost-optimized multi-phase pipeline (Phase 2) with parallel processing.

## Repository Structure

```
ai-rss-summarizer/
├── digest-pipeline.py      # Phase 2: Recommended production script
├── digest-simple.py        # Phase 1: Simple single-pass (legacy/testing)
├── feeds.md                # RSS feed URLs (user-maintained)
├── .env                    # Config/secrets (not in git)
├── .env.example            # Config template
├── requirements.txt        # Python dependencies
├── reports/                # Generated digests (not in git)
│   └── {Month-Year}/
│       └── {YYYY-MM-DD}/
│           ├── digest_pipeline_{timestamp}.md
│           ├── 01_items.json
│           ├── 02_summaries.json
│           └── 03_themes.json
├── README.md
└── CLAUDE.md               # This file
```

## Scripts

### digest-pipeline.py (Phase 2) ⭐ RECOMMENDED

The production-ready multi-phase pipeline with email delivery.

**Architecture:**
1. **Phase 1: Fetch** - Parse feeds.md, fetch RSS items, save to JSON
2. **Phase 2: Summarize** - Parallel Haiku calls (5 workers) to summarize each item
3. **Phase 3: Link Themes** - Haiku analyzes summaries to find themes/connections
4. **Phase 4: Synthesize** - Sonnet creates final digest, converts to HTML, sends email

**Key classes:**
- `FeedFetcher` - RSS feed parsing with feedparser + deduplication
- `ItemSummarizer` - Parallel summarization with ThreadPoolExecutor
- `ThemeLinker` - Theme detection and connection finding
- `DigestSynthesizer` - Final digest creation
- `send_email()` - SMTP email delivery with HTML formatting

**Key modules:**
- `dedup.py` - Feed item deduplication with 7-day rolling state
- `prompts.py` - Category-specific prompts for better summaries
- `format_digest.py` - Digest formatting utilities

**Features:**
- Parallel processing (5 workers)
- Cost-optimized (Haiku for bulk, Sonnet for synthesis)
- Smart deduplication (30-40% cost savings on subsequent runs)
- Email delivery with markdown→HTML conversion
- Intermediate JSON outputs for debugging
- Dynamic token calculation based on item count
- Test mode via MAX_FEEDS environment variable

### digest-simple.py (Phase 1)

Legacy single-pass approach. Kept for simplicity and testing.

**Use when:**
- Testing with small feed counts (<50 items)
- Need simple, easy-to-understand code
- Don't need email delivery

**Limitations:**
- More expensive (all Sonnet tokens)
- Slower (no parallel processing)
- No intermediate outputs
- No email delivery

## Configuration (.env)

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Email delivery (optional)
SEND_EMAIL=true|false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=email@example.com
SMTP_PASSWORD=app-password
EMAIL_FROM=email@example.com
EMAIL_TO=email@example.com

# Deduplication (optional - enabled by default)
DEDUP_ENABLED=true
DEDUP_LOOKBACK_DAYS=7
DEDUP_STATE_FILE=reports/.dedup_state.json

# Testing (optional)
MAX_FEEDS=3  # Limit feeds for faster testing
```

## Common Operations

### Add/Modify Feeds
Edit `feeds.md` - markdown list format with category headers:
```markdown
## Tech News
- https://feed1.com/rss
- https://feed2.com/rss
```

### Run in Test Mode
```bash
# In .env:
MAX_FEEDS=3

python digest-pipeline.py  # Processes only first 3 feeds
```

### Run in Production
```bash
# In .env:
# MAX_FEEDS=3  (comment out or remove)

python digest-pipeline.py  # Processes all feeds
```

### Debug Issues
Check intermediate JSON files in `reports/{Month-Year}/{YYYY-MM-DD}/`:
- `01_items.json` - Are feeds being fetched correctly?
- `02_summaries.json` - Are individual summaries good?
- `03_themes.json` - Are themes relevant?

## Cost Optimization

**Phase 2 Strategy:**
- Use **Haiku** ($0.80/M in, $4/M out) for:
  - Individual item summarization (Phase 2)
  - Theme detection (Phase 3)
- Use **Sonnet** ($3/M in, $15/M out) for:
  - Final digest synthesis only (Phase 4)

**Result:** 44% cheaper and 43% faster than Phase 1

**Typical costs:**
- 3 feeds (30 items): ~$0.09
- 10 feeds (100 items): ~$0.20
- 27 feeds (270 items): ~$0.28

## Email Delivery

**HTML Formatting:**
- Uses `markdown` library to convert markdown → HTML
- Professional GitHub-inspired styling
- Responsive design
- Both plain text and HTML MIME parts

**SMTP Providers:**
- Gmail: `smtp.gmail.com:587` (requires app password)
- Outlook: `smtp.office365.com:587`
- iCloud: `smtp.mail.me.com:587`
- Any custom SMTP server

## Implementation History

This project was built incrementally:

**Phase 0 (2026-02-07):** Setup, environment, feeds.md
**Phase 1 (2026-02-07):** Simple single-pass digest (digest-simple.py)
**Phase 2 (2026-02-08):** Multi-phase pipeline (digest-pipeline.py)
- Built from scratch (not copied from reference implementation)
- Added parallel processing with ThreadPoolExecutor
- Added email delivery with HTML formatting
- Added test mode (MAX_FEEDS)

**Implemented (2026-02-09):**
- ✅ Phase 3: Custom prompts per feed type (prompts.py)
- ✅ Phase 5.1: Feed item deduplication (dedup.py)

**Not yet implemented:**
- Phase 4: Automation (cron/launchd)
- Phase 5.2+: Caching, filtering, weekly summaries
- Phase 6: Performance optimization

See `~/second-brain/1-projects/agentic/feed-summarization/implementation-plan.md` for detailed implementation plan.

## Dependencies

```
anthropic       # Claude API client
feedparser      # RSS/Atom parsing
python-dotenv   # Environment variables
markdown        # Markdown → HTML conversion
```

All use standard Python (no complex ML libraries). The `dedup.py` module uses only stdlib.

## Key Design Decisions

### Why Two Scripts?
- **digest-simple.py** - Educational, easy to understand, good for small-scale testing
- **digest-pipeline.py** - Production-ready, cost-optimized, scalable

### Why Parallel Processing?
- Summarizing 200+ items serially is slow
- Haiku is fast enough for parallel calls
- 5 workers balances speed vs API rate limits

### Why Markdown for Files, HTML for Email?
- Markdown is human-readable in files (easy to view in Obsidian, editors)
- HTML renders better in email clients (links, headers, styling)

### Why Save Intermediate JSON?
- Debugging: Can inspect each phase independently
- Recovery: Could resume from checkpoints (not yet implemented)
- Analysis: Can analyze theme quality, summarization effectiveness

## Testing Strategy

1. **Unit testing** - Not implemented (would test individual classes)
2. **Integration testing** - Manual testing with `MAX_FEEDS=3`
3. **Cost validation** - Check stats footer in digest

**Best practice for development:**
- Set `MAX_FEEDS=3` in .env
- Run digest-pipeline.py
- Check email and JSON outputs
- When satisfied, comment out MAX_FEEDS for production

## Troubleshooting Guide

### Email Not Sending
- Check SMTP credentials in .env
- Gmail requires app password (not regular password)
- Verify SEND_EMAIL=true
- Check port 587 is allowed through firewall

### High Costs
- Phase 2 should be ~$0.28 for 177 items
- If higher: check token usage in stats footer
- Reduce max_items_per_feed in FeedFetcher.__init__()
- Use MAX_FEEDS to limit feed count

### Poor Quality Digests
- Check 02_summaries.json - are individual summaries good?
- Check 03_themes.json - are themes relevant?
- May need custom prompts (Phase 3 - not yet implemented)

### Slow Execution
- Check which feeds are slow (progress shows each feed)
- Remove slow/broken feeds from feeds.md
- Increase max_workers in ItemSummarizer (if CPU allows)
- Use MAX_FEEDS for testing

### JSON Parse Errors (Phase 3)
- Claude sometimes returns malformed JSON
- Check theme_debug.txt for problematic response
- Usually due to truncation - max_tokens too low
- Current: 2000 tokens (should be sufficient)

## Future Enhancements

**Phase 3 candidates:**
- Custom prompts per feed category (news vs tech vs science)
- Better HTML email templates (tables, images)
- Feed-specific max_items configuration

**Phase 4 candidates:**
- Automated scheduling (cron/launchd)
- Cost tracking over time
- Quality monitoring

**Phase 5 candidates:**
- ✅ **Deduplication** - IMPLEMENTED (2026-02-09)
  - Cross-day deduplication (tracks items across runs)
  - Cross-feed deduplication (same story from multiple sources)
  - 7-day rolling window with auto-cleanup
  - Configurable via DEDUP_* env vars
- Caching (avoid re-fetching unchanged feeds)
- Date filtering (only recent items)
- Weekly summary (trends across week)

## Environment

**Typical usage:**
- macOS (Darwin)
- Python 3.13
- Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)
- Claude Haiku 4.5 (claude-haiku-4-5-20251001)

**File locations:**
- Code: `~/src/ai-rss-summarizer/`
- Documentation: `~/second-brain/1-projects/agentic/feed-summarization/`
- Reports symlink: `~/second-brain/1-projects/agentic/feed-summarization/digests/` → `~/src/ai-rss-summarizer/reports/`

## Related Documentation

- Implementation plan: `~/second-brain/1-projects/agentic/feed-summarization/implementation-plan.md`
- Obsidian vault: Uses PARA method (Projects/Areas/Resources/Archive)
- Claude Code docs: https://docs.anthropic.com/claude-code

## Working with This Codebase

### When Adding Features
1. Test with MAX_FEEDS=3 first
2. Check intermediate JSON outputs
3. Verify email rendering (if applicable)
4. Update README.md and this file
5. Commit with descriptive message

### When Debugging
1. Check script output (shows progress per phase)
2. Examine intermediate JSON files
3. Check theme_debug.txt if phase 3 failed
4. Review stats footer for token/cost analysis

### When Modifying Prompts
- ItemSummarizer: Individual item summaries (keep concise)
- ThemeLinker: Theme detection (balance breadth vs depth)
- DigestSynthesizer: Final digest (focus on insight, not summary)

### Code Style
- Classes for each major phase
- Clear docstrings
- Print progress to stdout (user-friendly)
- Save intermediate outputs (debugging)
- Environment variables for configuration (not hardcoded)

## Important Notes

- `.env` contains secrets - never commit
- `reports/` contains personal data - in .gitignore
- `feeds.md` is user-maintained - don't overwrite without asking
- Email credentials are sensitive - handle carefully
- Test mode (MAX_FEEDS) exists for a reason - use it!

## Contact & Context

This is a personal project by devlon (duthied@gmail.com). The codebase emphasizes:
- Cost optimization
- Practical usefulness over perfection
- Incremental development
- Clear documentation

When suggesting changes, prioritize:
1. Cost reduction
2. Quality improvement
3. User experience
4. Code clarity

Avoid:
- Over-engineering
- Unnecessary complexity
- Breaking existing functionality
- Expensive operations without justification
