"""HTTP probing with redirect following and metadata extraction."""

import asyncio
import time
import re
from typing import Dict, Optional
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


class ProbeResult:
    """Result of probing a single URL."""
    
    def __init__(self, url):
        self.url = url
        self.initial_status = None
        self.final_status = None
        self.redirect_hops = 0
        self.first_redirect_target = None
        self.final_url = url
        self.response_time_ms = None
        self.content_type = None
        self.canonical_url = None
        self.title = None
        self.title_hash = None
        self.notes = []
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'url': self.url,
            'initial_status': self.initial_status,
            'final_status': self.final_status,
            'redirect_hops': self.redirect_hops,
            'first_redirect_target': self.first_redirect_target,
            'final_url': self.final_url,
            'response_time_ms': self.response_time_ms,
            'content_type': self.content_type,
            'canonical_url': self.canonical_url,
            'title': self.title,
            'title_hash': self.title_hash,
            'notes': '; '.join(self.notes) if self.notes else ''
        }


class URLProber:
    """Probe URLs with redirect following and metadata extraction."""
    
    def __init__(self, config):
        """
        Initialize prober.
        
        Args:
            config: Dictionary with configuration options
        """
        self.config = config
        self.timeout = config.get('timeout_ms', 10000) / 1000.0
        self.user_agent = config.get('user_agent', 'URLCompareBot/1.0')
        self.max_redirects = config.get('max_redirects', 5)
        self.retry_count = config.get('retry', 2)
        self.rate_limit_rps = config.get('rate_limit_rps', 2)
        self.follow_robots = config.get('follow_robots', True)
        self.robot_parsers = {}
        
        # Rate limiting: sleep time between requests per host
        self.min_delay = 1.0 / self.rate_limit_rps if self.rate_limit_rps > 0 else 0
        self.last_request_time = {}
    
    async def probe_urls(self, urls, robot_allowed=None):
        """
        Probe multiple URLs with rate limiting.
        
        Args:
            urls: Iterable of URLs to probe
            robot_allowed: Optional dict mapping URL to boolean if robots check already done
        
        Returns:
            Dictionary mapping URL to ProbeResult
        """
        results = {}
        semaphore = asyncio.Semaphore(self.config.get('concurrency', 8))
        
        async def probe_with_limit(url):
            async with semaphore:
                # Check robots.txt if needed
                if self.follow_robots and robot_allowed is not None:
                    if not robot_allowed.get(url, True):
                        result = ProbeResult(url)
                        result.notes.append('robots_disallow')
                        return url, result
                
                # Rate limit per host
                await self._rate_limit(url)
                
                # Probe with retries
                result = await self._probe_with_retry(url)
                return url, result
        
        tasks = [probe_with_limit(url) for url in urls]
        
        for coro in asyncio.as_completed(tasks):
            url, result = await coro
            results[url] = result
        
        return results
    
    async def _rate_limit(self, url):
        """Apply rate limiting per host."""
        parsed = urlparse(url)
        host = parsed.netloc
        
        if host in self.last_request_time:
            elapsed = time.time() - self.last_request_time[host]
            if elapsed < self.min_delay:
                await asyncio.sleep(self.min_delay - elapsed)
        
        self.last_request_time[host] = time.time()
    
    async def _probe_with_retry(self, url):
        """Probe a URL with retry logic."""
        result = ProbeResult(url)
        
        for attempt in range(self.retry_count + 1):
            try:
                await self._probe(url, result)
                return result
            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as e:
                if attempt == self.retry_count:
                    if isinstance(e, httpx.TimeoutException):
                        result.notes.append('timeout')
                    else:
                        result.notes.append('network_error')
                else:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                result.notes.append(f'error: {str(e)[:50]}')
                return result
        
        return result
    
    async def _probe(self, url, result):
        """
        Probe a single URL.
        
        Populates the ProbeResult object.
        """
        start_time = time.time()
        
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=False,
            headers={'User-Agent': self.user_agent}
        ) as client:
            
            # Try HEAD first
            method = 'HEAD'
            response = None
            
            try:
                response = await client.head(url)
                
                # If HEAD returns 405 or doesn't give us enough info, try GET
                if response.status_code == 405:
                    method = 'GET'
                    response = await client.get(url, follow_redirects=False)
            except Exception:
                # If HEAD fails, try GET
                method = 'GET'
                try:
                    response = await client.get(url, follow_redirects=False)
                except Exception as e:
                    raise
            
            result.initial_status = response.status_code
            result.final_status = response.status_code
            result.content_type = response.headers.get('content-type', '').split(';')[0].strip()
            
            # Follow redirects manually to track hops
            current_url = url
            redirect_count = 0
            visited_urls = {url}
            
            while response.status_code in (301, 302, 303, 307, 308) and redirect_count < self.max_redirects:
                location = response.headers.get('location')
                if not location:
                    break
                
                # Resolve relative redirects
                from urllib.parse import urljoin
                next_url = urljoin(current_url, location)
                
                if redirect_count == 0:
                    result.first_redirect_target = next_url
                
                # Check for redirect loop
                if next_url in visited_urls:
                    result.notes.append('redirect_loop')
                    break
                
                visited_urls.add(next_url)
                current_url = next_url
                redirect_count += 1
                
                # Apply rate limiting for redirected host
                await self._rate_limit(current_url)
                
                # Fetch the redirected URL
                try:
                    response = await client.get(current_url, follow_redirects=False)
                except Exception as e:
                    result.notes.append(f'redirect_error: {str(e)[:30]}')
                    break
            
            if redirect_count >= self.max_redirects and response.status_code in (301, 302, 303, 307, 308):
                result.notes.append('max_redirects_exceeded')
            
            result.redirect_hops = redirect_count
            result.final_url = current_url
            result.final_status = response.status_code
            result.response_time_ms = int((time.time() - start_time) * 1000)
            
            # Extract metadata if HTML and 200
            if result.final_status == 200 and 'text/html' in result.content_type:
                # Need to fetch content if we used HEAD or followed redirects
                if method == 'HEAD' or redirect_count > 0:
                    try:
                        response = await client.get(current_url, follow_redirects=False)
                    except Exception:
                        pass  # Keep the result we have
                
                if response.status_code == 200:
                    await self._extract_html_metadata(response, result)
            
            # Handle specific status codes
            if result.final_status == 429:
                result.notes.append('rate_limited')
    
    async def _extract_html_metadata(self, response, result):
        """Extract metadata from HTML response."""
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title_tag = soup.find('title')
            if title_tag:
                result.title = title_tag.get_text().strip()
                # Compute simple hash of title
                import hashlib
                result.title_hash = hashlib.sha1(result.title.encode()).hexdigest()[:12]
            
            # Extract canonical URL
            canonical = soup.find('link', rel='canonical')
            if canonical and canonical.get('href'):
                result.canonical_url = canonical['href']
        
        except Exception:
            # If HTML parsing fails, just skip metadata
            pass
