"""
Unit tests for URL normalization.

Run with: python -m pytest test_url_normalizer.py
"""

import pytest
from url_normalizer import URLNormalizer, normalize_url


class TestURLNormalizer:
    """Tests for URL normalization functionality."""
    
    def test_basic_normalization(self):
        """Test basic URL normalization."""
        normalizer = URLNormalizer()
        
        url = "https://Example.COM/path/"
        normalized, path_key = normalizer.normalize(url)
        
        assert normalized == "https://example.com/path"
        assert path_key == "/path"
    
    def test_default_port_removal(self):
        """Test that default ports are removed."""
        normalizer = URLNormalizer()
        
        # HTTP default port
        url1 = "http://example.com:80/path"
        normalized1, _ = normalizer.normalize(url1)
        assert ":80" not in normalized1
        
        # HTTPS default port
        url2 = "https://example.com:443/path"
        normalized2, _ = normalizer.normalize(url2)
        assert ":443" not in normalized2
        
        # Non-default port should be kept
        url3 = "https://example.com:8080/path"
        normalized3, _ = normalizer.normalize(url3)
        assert ":8080" in normalized3
    
    def test_trailing_slash_removal(self):
        """Test trailing slash handling."""
        normalizer = URLNormalizer()
        
        # Non-root paths should have trailing slash removed
        url1 = "https://example.com/path/"
        _, path_key1 = normalizer.normalize(url1)
        assert path_key1 == "/path"
        
        # Root should keep slash
        url2 = "https://example.com/"
        _, path_key2 = normalizer.normalize(url2)
        assert path_key2 == "/"
    
    def test_query_string_removal(self):
        """Test that query strings are removed by default."""
        normalizer = URLNormalizer(include_query=False)
        
        url = "https://example.com/path?query=param&other=value"
        normalized, path_key = normalizer.normalize(url)
        
        assert "?" not in path_key
        assert "query" not in path_key
    
    def test_query_string_inclusion(self):
        """Test query string inclusion when enabled."""
        normalizer = URLNormalizer(include_query=True)
        
        url = "https://example.com/path?b=2&a=1"
        normalized, path_key = normalizer.normalize(url)
        
        # Query params should be sorted
        assert "?" in path_key
        assert "a=1" in path_key
        assert "b=2" in path_key
    
    def test_tracking_param_removal(self):
        """Test removal of tracking parameters."""
        normalizer = URLNormalizer(include_query=True)
        
        url = "https://example.com/path?real=value&utm_source=test&fbclid=123"
        normalized, path_key = normalizer.normalize(url)
        
        # Real params should be kept
        assert "real=value" in path_key
        
        # Tracking params should be removed
        assert "utm_source" not in path_key
        assert "fbclid" not in path_key
    
    def test_fragment_removal(self):
        """Test that fragments are removed by default."""
        normalizer = URLNormalizer(include_fragment=False)
        
        url = "https://example.com/path#section"
        normalized, path_key = normalizer.normalize(url)
        
        assert "#" not in path_key
        assert "section" not in path_key
    
    def test_duplicate_slash_collapse(self):
        """Test collapsing of duplicate slashes."""
        normalizer = URLNormalizer()
        
        url = "https://example.com//path///to////page"
        normalized, path_key = normalizer.normalize(url)
        
        assert path_key == "/path/to/page"
    
    def test_convenience_function(self):
        """Test the convenience function."""
        url = "HTTPS://Example.com:443/Path/"
        normalized, path_key = normalize_url(url)
        
        assert normalized == "https://example.com/Path"
        assert path_key == "/Path"


class TestPathKeyExtraction:
    """Tests for path key extraction."""
    
    def test_extract_path_key(self):
        """Test extracting just the path key."""
        normalizer = URLNormalizer()
        
        url = "https://example.com/path"
        path_key = normalizer.extract_path_key(url)
        
        assert path_key == "/path"
    
    def test_path_key_consistency(self):
        """Test that similar URLs produce the same path key."""
        normalizer = URLNormalizer()
        
        urls = [
            "https://example.com/path",
            "HTTPS://EXAMPLE.COM/path",
            "https://example.com:443/path",
            "https://example.com/path/",
        ]
        
        path_keys = [normalizer.extract_path_key(url) for url in urls]
        
        # All should normalize to the same path key
        assert len(set(path_keys)) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
