# AI RSS Summarizer

Cost-optimized RSS feed digest generator using Claude AI with email delivery.

## Features

- **Multi-phase pipeline** - Parallel processing with Haiku for summaries, Sonnet for synthesis
- **Email delivery** - Beautiful HTML-formatted digests sent via any SMTP server
- **Smart deduplication** - Automatically skips previously processed items (30-40% cost savings)
- **Cost-optimized** - ~$0.18-0.28 per run for 177 items (~$5-8/month daily)
- **Test mode** - Limit feeds for faster development iterations
- **Two approaches** - Simple single-pass (Phase 1) or advanced pipeline (Phase 2)

## Quick Start

### 1. Clone and Install

```bash
git clone git@github.com:duthied/ai-rss-summarizer.git
cd ai-rss-summarizer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Email delivery (optional)
SEND_EMAIL=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=your-email@gmail.com

# Testing (optional - limit feeds for faster testing)
# MAX_FEEDS=3

# Deduplication (optional - enabled by default)
DEDUP_ENABLED=true
DEDUP_LOOKBACK_DAYS=7
```

### 3. Add Your Feeds

Edit `feeds.md` with your RSS feed URLs:

```markdown
# RSS Feeds to Monitor

## Tech News
- https://feeds.example.com/tech
- https://another-feed.com/rss

## Science
- https://science-feed.com/rss
```

### 4. Run

**Recommended: Phase 2 Pipeline** (parallel processing, email delivery)
```bash
python digest-pipeline.py
```

**Alternative: Phase 1 Simple** (single-pass, file only)
```bash
python digest-simple.py
```

## Email Setup

### Gmail
1. Enable 2-factor authentication
2. Create app password: https://myaccount.google.com/apppasswords
3. Use app password in `.env`

### Other Providers
- **Outlook**: `smtp.office365.com:587`
- **iCloud**: `smtp.mail.me.com:587`
- **Custom SMTP**: Any SMTP server

## Cost Breakdown

| Feeds | Items | Phase 1 Cost | Phase 2 Cost | Time |
|-------|-------|--------------|--------------|------|
| 3     | 30    | ~$0.15       | ~$0.09       | ~84s |
| 10    | 100   | ~$0.35       | ~$0.20       | ~120s |
| 27    | 270   | ~$0.50+      | ~$0.28       | ~170s |

**Phase 2 is 44% cheaper and 43% faster than Phase 1**

## Deduplication

The digest automatically tracks previously processed items to avoid reprocessing:

- **Cross-day deduplication:** Items seen in previous runs are skipped
- **Cross-feed deduplication:** Same story from multiple feeds only processed once
- **7-day rolling window:** Automatically cleans up old tracking data
- **Configurable:** Can be disabled or adjusted via `.env`

**Configuration:**
```bash
DEDUP_ENABLED=true              # Enable/disable (default: true)
DEDUP_LOOKBACK_DAYS=7           # Days to track (default: 7)
```

**Manual reset:**
```bash
# Force reprocess all items
rm reports/.dedup_state.json
```

**Savings:** Typically reduces daily processing by 30-40%, saving ~$0.08 per run.

## Test Mode

For faster development iterations, limit the number of feeds:

```bash
# In .env:
MAX_FEEDS=3
```

This processes only the first 3 feeds from `feeds.md`.

## Output

### Local Files
Digests are saved to: `reports/{Month-Year}/{YYYY-MM-DD}/digest_pipeline_{timestamp}.md`

Example: `reports/February-2026/2026-02-08/digest_pipeline_20260208_123427.md`

### Email
When `SEND_EMAIL=true`, digests are sent as HTML-formatted emails with:
- Professional styling
- Clickable links
- Proper headers and formatting
- Stats footer

### Intermediate Files (Phase 2 only)
- `01_items.json` - Raw feed items
- `02_summaries.json` - AI-generated summaries
- `03_themes.json` - Detected themes and connections

## Scripts

### digest-pipeline.py (Phase 2)
**Recommended** - Multi-phase pipeline with parallel processing

- ✅ 4 phases: Fetch → Summarize (Haiku) → Link themes → Synthesize (Sonnet)
- ✅ Parallel processing (5 workers)
- ✅ Email delivery with HTML formatting
- ✅ Cost-optimized
- ✅ Intermediate outputs for debugging
- ✅ 44% cheaper, 43% faster than Phase 1

### digest-simple.py (Phase 1)
Simple single-pass approach

- ✅ Easy to understand
- ✅ Single Sonnet API call
- ✅ Good for small feed lists (<50 items)
- ⚠️ More expensive for large feed lists
- ⚠️ No email delivery

## Architecture (Phase 2)

```
Phase 1: Fetch
├─ Parse feeds.md
├─ Fetch RSS feeds (feedparser)
└─ Save: 01_items.json

Phase 2: Summarize (Parallel)
├─ ThreadPoolExecutor (5 workers)
├─ Claude Haiku for individual items
├─ Extract: summary, significance, topics
└─ Save: 02_summaries.json

Phase 3: Link Themes
├─ Claude Haiku analyzes all summaries
├─ Identify 3-5 major themes
├─ Find connections between items
└─ Save: 03_themes.json

Phase 4: Synthesize
├─ Claude Sonnet creates final digest
├─ Uses summaries + themes
├─ Structured output with links
├─ Convert markdown → HTML for email
└─ Save: digest_pipeline_{timestamp}.md
```

## Pricing

### Claude Models
- **Haiku**: $0.80/M input, $4/M output (bulk summaries)
- **Sonnet**: $3/M input, $15/M output (final synthesis)

### Example (177 items)
- Haiku: 54K input + 21K output = $0.13
- Sonnet: 29K input + 3K output = $0.13
- **Total: $0.26-0.28 per run**

## Automation

### Cron (Daily at 4 AM)
```bash
0 4 * * * cd ~/src/ai-rss-summarizer && source venv/bin/activate && python digest-pipeline.py &> /dev/null
```

### Launchd (macOS)
See implementation plan for details.

## Development

### Project Structure
```
ai-rss-summarizer/
├── digest-pipeline.py    # Phase 2: Multi-phase pipeline
├── digest-simple.py      # Phase 1: Simple single-pass
├── feeds.md              # RSS feed URLs
├── .env                  # Configuration (not in git)
├── .env.example          # Configuration template
├── requirements.txt      # Python dependencies
├── reports/              # Generated digests (not in git)
│   └── {Month-Year}/
│       └── {YYYY-MM-DD}/
│           ├── digest_pipeline_{timestamp}.md
│           ├── 01_items.json
│           ├── 02_summaries.json
│           └── 03_themes.json
└── README.md
```

### Dependencies
- `anthropic` - Claude API client
- `feedparser` - RSS/Atom feed parsing
- `python-dotenv` - Environment variable management
- `markdown` - Markdown to HTML conversion (for email)

## Troubleshooting

### Email not sending
- Check SMTP credentials in `.env`
- For Gmail: use app password, not regular password
- Verify `SEND_EMAIL=true`
- Check firewall allows port 587

### High costs
- Use Phase 2 pipeline (cheaper)
- Reduce `max_items_per_feed` in code
- Use `MAX_FEEDS` to limit feed count

### Slow execution
- Check feed URLs (slow/broken feeds)
- Increase `max_workers` in Phase 2 (if CPU allows)
- Use `MAX_FEEDS` for testing

### Empty/truncated digests
- Phase 2 calculates `max_tokens` dynamically
- Check intermediate JSON files for errors

## Contributing

This is a personal project, but feel free to fork and adapt!

## License

MIT

## Links

- [Implementation Plan](https://github.com/duthied/ai-rss-summarizer/wiki) (if available)
- [Claude AI](https://claude.ai)
- [Anthropic API Docs](https://docs.anthropic.com)
