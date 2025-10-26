#!/usr/bin/env python3
"""
URL Comparison Tool - Main CLI Interface

Compare URLs across two sites for content parity checks, broken links, and migration audits.
"""

import argparse
import asyncio
import sys
import yaml
from pathlib import Path

from tqdm import tqdm

from url_normalizer import URLNormalizer
from discovery import URLDiscoverer
from prober import URLProber
from comparator import URLComparator
from csv_writer import CSVWriter


def load_config(config_path=None):
    """Load configuration from YAML file."""
    config = {}
    
    if config_path and Path(config_path).exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
    
    return config


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Compare URLs across two sites',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --site-a=https://ansiblepilot.com --site-b=https://ansiblebyexample.com
  
  %(prog)s --config=config.yaml --output=results.csv
  
  %(prog)s --site-a=https://example.com --site-b=https://example.org \\
           --discovery=sitemap --concurrency=16 --rate-limit-rps=5
"""
    )
    
    # Core settings
    parser.add_argument('--config', help='Path to YAML config file')
    parser.add_argument('--site-a', help='URL of first site (e.g., https://ansiblepilot.com)')
    parser.add_argument('--site-b', help='URL of second site (e.g., https://ansiblebyexample.com)')
    
    # Discovery options
    parser.add_argument('--discovery', choices=['sitemap', 'crawl', 'both'], default='both',
                        help='Discovery method (default: both)')
    parser.add_argument('--crawl-max-depth', type=int, default=2,
                        help='Maximum crawl depth (default: 2)')
    parser.add_argument('--sitemaps', nargs='+', help='Override sitemap URLs')
    
    # HTTP options
    parser.add_argument('--concurrency', type=int, default=8,
                        help='Number of concurrent requests (default: 8)')
    parser.add_argument('--rate-limit-rps', type=float, default=2.0,
                        help='Rate limit in requests per second per host (default: 2)')
    parser.add_argument('--timeout-ms', type=int, default=10000,
                        help='Request timeout in milliseconds (default: 10000)')
    parser.add_argument('--max-redirects', type=int, default=5,
                        help='Maximum redirects to follow (default: 5)')
    parser.add_argument('--retry', type=int, default=2,
                        help='Number of retries on network errors (default: 2)')
    
    # URL normalization
    parser.add_argument('--include-query', action='store_true',
                        help='Include query strings in path keys')
    parser.add_argument('--include-fragment', action='store_true',
                        help='Include fragments in path keys')
    
    # Behavior
    parser.add_argument('--follow-robots', type=lambda x: x.lower() == 'true', default=True,
                        help='Respect robots.txt (default: true)')
    parser.add_argument('--user-agent', default='URLCompareBot/1.0 (+contact)',
                        help='User agent string')
    
    # Output
    parser.add_argument('--output', default='urls-compare.csv',
                        help='Output CSV file path (default: urls-compare.csv)')
    
    return parser.parse_args()


def merge_config(args, file_config):
    """Merge command-line args with file config (CLI takes precedence)."""
    config = file_config.copy()
    
    # Override with CLI args
    arg_dict = vars(args)
    for key, value in arg_dict.items():
        if value is not None:
            # Convert hyphenated keys to underscored
            config_key = key.replace('-', '_')
            config[config_key] = value
    
    return config


async def main_async(config):
    """Main async workflow."""
    site_a = config.get('site_a')
    site_b = config.get('site_b')
    
    if not site_a or not site_b:
        print("Error: Both --site-a and --site-b are required", file=sys.stderr)
        return 2
    
    discovery_mode = config.get('discovery', 'both')
    output_path = config.get('output', 'urls-compare.csv')
    
    print(f"\n{'='*60}")
    print("URL Comparison Tool")
    print(f"{'='*60}")
    print(f"Site A: {site_a}")
    print(f"Site B: {site_b}")
    print(f"Discovery: {discovery_mode}")
    print(f"Output: {output_path}")
    print(f"{'='*60}\n")
    
    # Initialize components
    discoverer = URLDiscoverer(config)
    prober = URLProber(config)
    comparator = URLComparator(config)
    
    # Discover URLs for both sites
    print("Phase 1: Discovering URLs...")
    
    print(f"  Discovering URLs for Site A ({site_a})...")
    urls_a = await discoverer.discover(site_a, discovery_mode)
    print(f"  Found {len(urls_a)} URLs on Site A")
    
    print(f"  Discovering URLs for Site B ({site_b})...")
    urls_b = await discoverer.discover(site_b, discovery_mode)
    print(f"  Found {len(urls_b)} URLs on Site B")
    
    total_urls = len(urls_a) + len(urls_b)
    print(f"  Total URLs to probe: {total_urls}\n")
    
    # Probe URLs
    print("Phase 2: Probing URLs...")
    
    print(f"  Probing Site A...")
    with tqdm(total=len(urls_a), desc="  Site A", unit="url") as pbar:
        results_a = {}
        # Probe in batches to update progress
        batch_size = max(1, config.get('concurrency', 8))
        url_list_a = list(urls_a.keys())
        
        for i in range(0, len(url_list_a), batch_size):
            batch = url_list_a[i:i+batch_size]
            batch_results = await prober.probe_urls(batch)
            results_a.update(batch_results)
            pbar.update(len(batch))
    
    print(f"  Probing Site B...")
    with tqdm(total=len(urls_b), desc="  Site B", unit="url") as pbar:
        results_b = {}
        url_list_b = list(urls_b.keys())
        
        for i in range(0, len(url_list_b), batch_size):
            batch = url_list_b[i:i+batch_size]
            batch_results = await prober.probe_urls(batch)
            results_b.update(batch_results)
            pbar.update(len(batch))
    
    print()
    
    # Compare results
    print("Phase 3: Comparing results...")
    comparisons = comparator.compare(urls_a, results_a, urls_b, results_b)
    print(f"  Generated {len(comparisons)} comparisons\n")
    
    # Write CSV output
    print(f"Phase 4: Writing results to {output_path}...")
    CSVWriter.write_csv(comparisons, output_path)
    print(f"  ✓ Written to {output_path}")
    
    # Print summary
    CSVWriter.print_summary(comparisons)
    
    # Determine exit code
    # Exit 1 if there are any errors/issues
    has_errors = any(
        comp.get('notes', '') != '' or 
        comp.get('comparison_class') in ('status_mismatch', 'error_a', 'error_b')
        for comp in comparisons
    )
    
    return 1 if has_errors else 0


def main():
    """Main entry point."""
    try:
        args = parse_args()
        
        # Load config file if specified
        file_config = {}
        if args.config:
            file_config = load_config(args.config)
        elif Path('config.yaml').exists():
            # Try to load default config.yaml
            file_config = load_config('config.yaml')
        
        # Merge configurations
        config = merge_config(args, file_config)
        
        # Run async main
        exit_code = asyncio.run(main_async(config))
        sys.exit(exit_code)
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == '__main__':
    main()
