"""URL normalization and path key generation."""

from urllib.parse import urlparse, parse_qs, urlencode, unquote, quote
import re


class URLNormalizer:
    """Normalize URLs according to PRD §7 rules."""
    
    # Tracking parameters to remove
    DEFAULT_TRACKING_PARAMS = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', '_ga', 'mc_cid', 'mc_eid'
    }
    
    def __init__(self, include_query=False, include_fragment=False, tracking_params=None):
        """
        Initialize normalizer.
        
        Args:
            include_query: Whether to include query strings in path key
            include_fragment: Whether to include fragments in path key
            tracking_params: Set of tracking parameters to remove
        """
        self.include_query = include_query
        self.include_fragment = include_fragment
        self.tracking_params = tracking_params or self.DEFAULT_TRACKING_PARAMS
    
    def normalize(self, url):
        """
        Normalize a URL according to PRD rules.
        
        Returns:
            Tuple of (normalized_url, path_key)
        """
        parsed = urlparse(url)
        
        # Lowercase scheme and host
        scheme = parsed.scheme.lower()
        host = parsed.hostname.lower() if parsed.hostname else ''
        port = parsed.port
        
        # Remove default ports
        if (scheme == 'http' and port == 80) or (scheme == 'https' and port == 443):
            port = None
        
        # Build netloc
        if port:
            netloc = f"{host}:{port}"
        else:
            netloc = host
        
        # Normalize path
        path = self._normalize_path(parsed.path)
        
        # Handle query string
        query = ''
        if self.include_query and parsed.query:
            query = self._normalize_query(parsed.query)
        
        # Handle fragment (default: always remove)
        fragment = ''
        if self.include_fragment and parsed.fragment:
            fragment = parsed.fragment
        
        # Build normalized URL
        normalized_url = f"{scheme}://{netloc}{path}"
        if query:
            normalized_url += f"?{query}"
        if fragment:
            normalized_url += f"#{fragment}"
        
        # Build path key (for comparison)
        path_key = path
        if query:
            path_key += f"?{query}"
        
        return normalized_url, path_key
    
    def _normalize_path(self, path):
        """Normalize URL path."""
        if not path:
            return '/'
        
        # Decode percent-encoding where safe, then re-encode
        try:
            path = unquote(path)
            path = quote(path, safe='/:@!$&\'()*+,;=')
        except Exception:
            pass  # Keep original if decode/encode fails
        
        # Collapse duplicate slashes
        path = re.sub(r'/+', '/', path)
        
        # Strip trailing slash except for root
        if len(path) > 1 and path.endswith('/'):
            path = path.rstrip('/')
        
        # Ensure leading slash
        if not path.startswith('/'):
            path = '/' + path
        
        return path
    
    def _normalize_query(self, query_string):
        """
        Normalize query string.
        
        - Remove tracking parameters
        - Sort parameters alphabetically
        - Encode consistently
        """
        try:
            params = parse_qs(query_string, keep_blank_values=True)
            
            # Remove tracking parameters
            filtered_params = {
                k: v for k, v in params.items() 
                if k not in self.tracking_params
            }
            
            if not filtered_params:
                return ''
            
            # Sort and encode
            sorted_items = sorted(filtered_params.items())
            # parse_qs returns lists, but we want single values for encoding
            flat_items = []
            for key, values in sorted_items:
                for value in values:
                    flat_items.append((key, value))
            
            return urlencode(flat_items)
        except Exception:
            # If parsing fails, return empty query
            return ''
    
    def extract_path_key(self, url):
        """
        Extract just the path key from a URL.
        
        This is a convenience method for comparison.
        """
        _, path_key = self.normalize(url)
        return path_key


def normalize_url(url, include_query=False, include_fragment=False, tracking_params=None):
    """
    Convenience function to normalize a single URL.
    
    Returns:
        Tuple of (normalized_url, path_key)
    """
    normalizer = URLNormalizer(include_query, include_fragment, tracking_params)
    return normalizer.normalize(url)
