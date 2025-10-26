"""URL discovery via sitemaps and crawling."""

import asyncio
import gzip
import re
from typing import Set, Dict, List
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from lxml import etree


class URLDiscoverer:
    """Discover URLs via sitemaps and/or crawling."""
    
    def __init__(self, config):
        """
        Initialize discoverer.
        
        Args:
            config: Dictionary with configuration options
        """
        self.config = config
        self.timeout = config.get('timeout_ms', 10000) / 1000.0
        self.user_agent = config.get('user_agent', 'URLCompareBot/1.0')
        self.follow_robots = config.get('follow_robots', True)
        self.crawl_max_depth = config.get('crawl_max_depth', 2)
        self.exclude_extensions = set(config.get('exclude_extensions', []))
        self.robot_parsers = {}
    
    async def discover(self, site_url, discovery_mode='both'):
        """
        Discover all URLs for a site.
        
        Args:
            site_url: Base URL of the site
            discovery_mode: 'sitemap', 'crawl', or 'both'
        
        Returns:
            Dictionary mapping URL to source ('sitemap', 'crawl', 'both')
        """
        urls = {}
        
        if discovery_mode in ('sitemap', 'both'):
            sitemap_urls = await self._discover_from_sitemap(site_url)
            for url in sitemap_urls:
                urls[url] = 'sitemap'
        
        if discovery_mode in ('crawl', 'both'):
            crawl_urls = await self._discover_from_crawl(site_url)
            for url in crawl_urls:
                if url in urls:
                    urls[url] = 'both'
                else:
                    urls[url] = 'crawl'
        
        return urls
    
    async def _discover_from_sitemap(self, site_url):
        """Discover URLs from sitemap(s)."""
        urls = set()
        
        # Try default sitemap locations
        sitemap_urls = self.config.get('sitemaps', [
            f"{site_url.rstrip('/')}/sitemap.xml",
            f"{site_url.rstrip('/')}/sitemap_index.xml"
        ])
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for sitemap_url in sitemap_urls:
                try:
                    discovered = await self._parse_sitemap(client, sitemap_url, site_url)
                    urls.update(discovered)
                except Exception as e:
                    print(f"  Warning: Could not fetch sitemap {sitemap_url}: {e}")
        
        return urls
    
    async def _parse_sitemap(self, client, sitemap_url, base_url):
        """Parse a sitemap file (handles regular and gzipped)."""
        urls = set()
        
        try:
            response = await client.get(
                sitemap_url,
                headers={'User-Agent': self.user_agent},
                follow_redirects=True
            )
            
            if response.status_code != 200:
                return urls
            
            content = response.content
            
            # Handle gzipped sitemaps
            if sitemap_url.endswith('.gz') or response.headers.get('content-type') == 'application/gzip':
                try:
                    content = gzip.decompress(content)
                except Exception:
                    pass  # Not gzipped or corrupt
            
            # Parse XML
            try:
                root = etree.fromstring(content)
            except Exception as e:
                print(f"  Warning: Could not parse sitemap XML {sitemap_url}: {e}")
                return urls
            
            # Define namespaces
            namespaces = {
                'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'xhtml': 'http://www.w3.org/1999/xhtml'
            }
            
            # Check if this is a sitemap index
            sitemaps = root.findall('.//sm:sitemap/sm:loc', namespaces)
            if sitemaps:
                # This is a sitemap index, recursively parse child sitemaps
                for sitemap in sitemaps:
                    child_url = sitemap.text.strip()
                    child_urls = await self._parse_sitemap(client, child_url, base_url)
                    urls.update(child_urls)
            else:
                # This is a regular sitemap, extract URLs
                locs = root.findall('.//sm:loc', namespaces)
                for loc in locs:
                    url = loc.text.strip()
                    # Only include URLs from the same domain
                    if url.startswith(base_url):
                        urls.add(url)
        
        except Exception as e:
            print(f"  Warning: Error parsing sitemap {sitemap_url}: {e}")
        
        return urls
    
    async def _discover_from_crawl(self, site_url):
        """Discover URLs by crawling the site."""
        urls = set()
        visited = set()
        to_visit = [(site_url, 0)]  # (url, depth)
        
        # Parse base domain
        parsed_base = urlparse(site_url)
        base_domain = parsed_base.netloc
        
        # Load robots.txt
        if self.follow_robots:
            await self._load_robots_txt(site_url)
        
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={'User-Agent': self.user_agent}
        ) as client:
            
            while to_visit:
                current_url, depth = to_visit.pop(0)
                
                if current_url in visited or depth > self.crawl_max_depth:
                    continue
                
                if not self._is_allowed_by_robots(current_url):
                    continue
                
                visited.add(current_url)
                urls.add(current_url)
                
                # Don't extract links if at max depth
                if depth >= self.crawl_max_depth:
                    continue
                
                # Fetch and parse the page
                try:
                    response = await client.get(current_url)
                    
                    if response.status_code != 200:
                        continue
                    
                    content_type = response.headers.get('content-type', '').lower()
                    if 'text/html' not in content_type:
                        continue
                    
                    # Extract links
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        
                        # Check for nofollow
                        if self.follow_robots:
                            rel = link.get('rel', [])
                            if 'nofollow' in rel:
                                continue
                        
                        # Resolve relative URLs
                        absolute_url = urljoin(current_url, href)
                        
                        # Parse and validate
                        parsed = urlparse(absolute_url)
                        
                        # Only same domain
                        if parsed.netloc != base_domain:
                            continue
                        
                        # Skip fragments
                        absolute_url = absolute_url.split('#')[0]
                        
                        # Skip excluded extensions
                        if self._has_excluded_extension(parsed.path):
                            continue
                        
                        # Add to queue if not visited
                        if absolute_url not in visited and (absolute_url, depth + 1) not in to_visit:
                            to_visit.append((absolute_url, depth + 1))
                
                except Exception as e:
                    # Silently skip pages that fail to load
                    pass
        
        return urls
    
    async def _load_robots_txt(self, site_url):
        """Load and parse robots.txt for a site."""
        parsed = urlparse(site_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = f"{base_url}/robots.txt"
        
        if base_url in self.robot_parsers:
            return
        
        parser = RobotFileParser()
        parser.set_url(robots_url)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    robots_url,
                    headers={'User-Agent': self.user_agent}
                )
                
                if response.status_code == 200:
                    parser.parse(response.text.splitlines())
        except Exception:
            # If robots.txt doesn't exist or fails, allow all
            pass
        
        self.robot_parsers[base_url] = parser
    
    def _is_allowed_by_robots(self, url):
        """Check if URL is allowed by robots.txt."""
        if not self.follow_robots:
            return True
        
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        if base_url not in self.robot_parsers:
            return True
        
        parser = self.robot_parsers[base_url]
        return parser.can_fetch(self.user_agent, url)
    
    def _has_excluded_extension(self, path):
        """Check if path has an excluded extension."""
        for ext in self.exclude_extensions:
            if path.lower().endswith(ext.lower()):
                return True
        return False
