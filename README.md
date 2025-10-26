# URL Comparison Tool

A comprehensive tool for discovering and comparing URLs across two websites. Perfect for content parity checks, broken link detection, SEO audits, and migration validation.

## Overview

This tool discovers all public URLs on two sites (via sitemaps and/or crawling), probes each URL for HTTP status and metadata, and outputs a detailed CSV comparison showing status codes, redirects, response times, and more.

**Primary use cases:**
- **Content parity audits**: Find pages that exist on one site but not the other
- **Migration validation**: Verify redirects and ensure no content is lost
- **SEO checks**: Identify 404s, broken links, and redirect chains
- **QA testing**: Validate site health and response times

## Features

✅ **Comprehensive Discovery**
- Parse sitemaps (including nested and gzipped)
- Intelligent web crawling with depth control
- Respects robots.txt and nofollow

✅ **Detailed Probing**
- HTTP status codes (initial and final after redirects)
- Redirect chain tracking
- Response time measurement
- Content-type detection
- HTML metadata extraction (title, canonical URL)

✅ **Smart Comparison**
- URL normalization for accurate matching
- Classification by comparison type (same, mismatch, redirect, error, etc.)
- Path-based comparison logic

✅ **Production Ready**
- Configurable concurrency and rate limiting
- Retry logic with exponential backoff
- Progress bars and detailed summaries
- Polite crawling practices

## Installation

```bash
# Clone the repository
cd url-compare

# Install dependencies
pip install -r requirements.txt
```

### Requirements

- Python 3.8+
- See `requirements.txt` for dependencies

## Quick Start

### Basic Usage

```bash
python url-compare.py \
  --site-a=https://ansiblepilot.com \
  --site-b=https://ansiblebyexample.com
```

This will:
1. Discover URLs from both sitemaps and crawling
2. Probe all URLs
3. Generate `urls-compare.csv` with comparison results

### Using a Configuration File

Create a `config.yaml` (see provided template):

```yaml
site_a: "https://ansiblepilot.com"
site_b: "https://ansiblebyexample.com"
discovery: "both"
concurrency: 8
rate_limit_rps: 2
output: "urls-compare.csv"
```

Then run:

```bash
python url-compare.py --config=config.yaml
```

## Configuration Options

### Core Settings

| Option | Default | Description |
|--------|---------|-------------|
| `--site-a` | *required* | URL of first site |
| `--site-b` | *required* | URL of second site |
| `--config` | `config.yaml` | Path to YAML config file |
| `--output` | `urls-compare.csv` | Output CSV file path |

### Discovery Options

| Option | Default | Description |
|--------|---------|-------------|
| `--discovery` | `both` | Discovery method: `sitemap`, `crawl`, or `both` |
| `--crawl-max-depth` | `2` | Maximum crawl depth from homepage |
| `--sitemaps` | auto | Override sitemap URLs (space-separated list) |

### HTTP Options

| Option | Default | Description |
|--------|---------|-------------|
| `--concurrency` | `8` | Number of concurrent requests |
| `--rate-limit-rps` | `2.0` | Rate limit (requests/sec per host) |
| `--timeout-ms` | `10000` | Request timeout in milliseconds |
| `--max-redirects` | `5` | Maximum redirects to follow |
| `--retry` | `2` | Number of retries on network errors |

### URL Normalization

| Option | Default | Description |
|--------|---------|-------------|
| `--include-query` | `false` | Include query strings in path keys |
| `--include-fragment` | `false` | Include fragments (#) in path keys |

### Behavior

| Option | Default | Description |
|--------|---------|-------------|
| `--follow-robots` | `true` | Respect robots.txt rules |
| `--user-agent` | `URLCompareBot/1.0` | User agent string |

## Usage Examples

### Sitemap-Only Comparison (Fast)

```bash
python url-compare.py \
  --site-a=https://ansiblepilot.com \
  --site-b=https://ansiblebyexample.com \
  --discovery=sitemap \
  --output=sitemap-compare.csv
```

### Deep Crawl with High Concurrency

```bash
python url-compare.py \
  --site-a=https://example.com \
  --site-b=https://example.org \
  --discovery=crawl \
  --crawl-max-depth=3 \
  --concurrency=16 \
  --rate-limit-rps=5
```

### Include Query Parameters

```bash
python url-compare.py \
  --site-a=https://ansiblepilot.com \
  --site-b=https://ansiblebyexample.com \
  --include-query
```

## Output CSV Format

The output CSV contains one row per unique path, with detailed comparison data:

### Key Columns

- `path_key` - Normalized path for comparison
- `present_on_a` / `present_on_b` - Whether URL exists on each site
- `source_a` / `source_b` - Discovery source (sitemap, crawl, both)
- `initial_status_a` / `initial_status_b` - Initial HTTP status
- `final_status_a` / `final_status_b` - Final status after redirects
- `redirect_hops_a` / `redirect_hops_b` - Number of redirects
- `final_url_a` / `final_url_b` - Final URL after redirects
- `response_time_ms_a` / `response_time_ms_b` - Response time
- `canonical_url_a` / `canonical_url_b` - Canonical URL from HTML
- `title_a` / `title_b` - Page title (if HTML)
- `comparison_class` - Classification of comparison result
- `notes` - Error messages and warnings

### Comparison Classes

- `same_status` - Both sites return the same status
- `a_only` - URL exists only on site A
- `b_only` - URL exists only on site B
- `status_mismatch` - Different status codes
- `redirect_both` - Both sites redirect
- `redirect_mismatch` - One redirects, one doesn't
- `error_a` - Site A returns 5xx error
- `error_b` - Site B returns 5xx error

## Analyzing Results

### Find Missing Pages

```bash
# Pages on A but not B
grep ",true,false," urls-compare.csv

# Pages on B but not A
grep ",false,true," urls-compare.csv
```

### Find Status Mismatches

```bash
# All mismatches
grep "status_mismatch" urls-compare.csv

# Pages that are 200 on A but 404 on B
awk -F',' '$7==200 && $14==404' urls-compare.csv
```

### Find Redirect Issues

```bash
# All redirect mismatches
grep "redirect_mismatch" urls-compare.csv
```

### Use with Excel/Google Sheets

1. Open the CSV in Excel or Google Sheets
2. Apply filters to the header row
3. Use pivot tables for aggregate analysis

## URL Normalization Rules

The tool normalizes URLs to match paths across domains:

1. ✅ Lowercase scheme and host
2. ✅ Remove default ports (`:80`, `:443`)
3. ✅ Strip trailing slashes (except root `/`)
4. ✅ Remove fragments (`#...`) by default
5. ✅ Remove or sort query parameters
6. ✅ Remove tracking parameters (`utm_*`, `fbclid`, etc.)
7. ✅ Collapse duplicate slashes

This ensures `/page/` and `/page` are treated as the same path.

## Exit Codes

- `0` - Success, no issues found
- `1` - Partial success, some errors or mismatches detected
- `2` - Fatal error (configuration, I/O, etc.)

## Limitations

### Version 1 Scope

⚠️ **Not supported in v1:**
- Authenticated/logged-in pages
- JavaScript-rendered content (no headless browser)
- Content diffing beyond title comparison
- Binary content comparison

### Recommended Practices

- Start with `--discovery=sitemap` for large sites
- Use `--rate-limit-rps=1` for small/slow servers
- Increase `--timeout-ms` for slow-responding sites
- Test with small crawl depths first

## Troubleshooting

### "robots_disallow" in notes

The robots.txt file blocks access. Use `--follow-robots=false` to override (use responsibly).

### "timeout" in notes

Increase `--timeout-ms` or check site availability.

### "redirect_loop" in notes

The site has a redirect loop (browser would also fail).

### Low URL counts

- Check if sitemap exists at `/sitemap.xml`
- Increase `--crawl-max-depth` for deeper crawling
- Verify the sites are accessible

## Project Structure

```
url-compare/
├── url-compare.py      # Main CLI entry point
├── url_normalizer.py   # URL normalization logic
├── discovery.py        # Sitemap & crawling
├── prober.py          # HTTP probing
├── comparator.py      # Comparison logic
├── csv_writer.py      # CSV output
├── config.yaml        # Configuration template
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## Advanced Usage

### Programmatic Usage

```python
from url_normalizer import URLNormalizer
from discovery import URLDiscoverer
from prober import URLProber
from comparator import URLComparator
from csv_writer import CSVWriter

config = {
    'site_a': 'https://example.com',
    'site_b': 'https://example.org',
    'discovery': 'both',
    'concurrency': 8,
    'rate_limit_rps': 2
}

# Discovery
discoverer = URLDiscoverer(config)
urls_a = await discoverer.discover(config['site_a'], 'both')
urls_b = await discoverer.discover(config['site_b'], 'both')

# Probing
prober = URLProber(config)
results_a = await prober.probe_urls(urls_a.keys())
results_b = await prober.probe_urls(urls_b.keys())

# Comparison
comparator = URLComparator(config)
comparisons = comparator.compare(urls_a, results_a, urls_b, results_b)

# Output
CSVWriter.write_csv(comparisons, 'output.csv')
CSVWriter.print_summary(comparisons)
```

## Contributing

Contributions welcome! Areas for improvement:

- [ ] Headless browser support for JS-rendered links
- [ ] Content diffing (HTML structure, text)
- [ ] Authentication support
- [ ] Database output option
- [ ] REST API interface
- [ ] Docker container

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or feature requests, please open an issue on the repository.

## Credits

Built according to PRD specifications for comparing ansiblepilot.com and ansiblebyexample.com.

---

**Happy comparing! 🔍**
