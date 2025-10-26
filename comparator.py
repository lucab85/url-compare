"""Comparison logic for URL results from two sites."""

from typing import Dict
from url_normalizer import URLNormalizer


class ComparisonClass:
    """Comparison classification constants."""
    SAME_STATUS = 'same_status'
    A_ONLY = 'a_only'
    B_ONLY = 'b_only'
    STATUS_MISMATCH = 'status_mismatch'
    REDIRECT_BOTH = 'redirect_both'
    REDIRECT_MISMATCH = 'redirect_mismatch'
    ERROR_A = 'error_a'
    ERROR_B = 'error_b'


class URLComparator:
    """Compare URL results from two sites."""
    
    def __init__(self, config):
        """
        Initialize comparator.
        
        Args:
            config: Dictionary with configuration options
        """
        self.config = config
        self.normalizer = URLNormalizer(
            include_query=config.get('include_query', False),
            include_fragment=config.get('include_fragment', False),
            tracking_params=set(config.get('tracking_params', []))
        )
    
    def compare(self, urls_a, results_a, urls_b, results_b):
        """
        Compare URLs and results from two sites.
        
        Args:
            urls_a: Dict mapping URL to source for site A
            results_a: Dict mapping URL to ProbeResult for site A
            urls_b: Dict mapping URL to source for site B
            results_b: Dict mapping URL to ProbeResult for site B
        
        Returns:
            List of comparison dictionaries (one per unique path_key)
        """
        # Build path_key indexes
        path_to_urls_a = self._build_path_index(urls_a)
        path_to_urls_b = self._build_path_index(urls_b)
        
        # Get all unique path keys
        all_paths = set(path_to_urls_a.keys()) | set(path_to_urls_b.keys())
        
        comparisons = []
        
        for path_key in sorted(all_paths):
            comparison = self._compare_path(
                path_key,
                path_to_urls_a.get(path_key),
                urls_a,
                results_a,
                path_to_urls_b.get(path_key),
                urls_b,
                results_b
            )
            comparisons.append(comparison)
        
        return comparisons
    
    def _build_path_index(self, urls):
        """
        Build an index from path_key to original URL.
        
        Args:
            urls: Dict mapping URL to source
        
        Returns:
            Dict mapping path_key to original URL
        """
        path_index = {}
        
        for url in urls:
            _, path_key = self.normalizer.normalize(url)
            # If multiple URLs normalize to the same path_key, keep the first one
            if path_key not in path_index:
                path_index[path_key] = url
        
        return path_index
    
    def _compare_path(self, path_key, url_a, urls_a, results_a, url_b, urls_b, results_b):
        """
        Compare a single path_key across both sites.
        
        Returns:
            Dictionary with comparison data
        """
        comparison = {
            'path_key': path_key,
            'present_on_a': url_a is not None,
            'present_on_b': url_b is not None,
        }
        
        # Site A data
        if url_a:
            result_a = results_a.get(url_a)
            source_a = urls_a.get(url_a, 'unknown')
            
            comparison.update({
                'source_a': source_a,
                'initial_status_a': result_a.initial_status if result_a else None,
                'final_status_a': result_a.final_status if result_a else None,
                'redirect_hops_a': result_a.redirect_hops if result_a else 0,
                'first_redirect_target_a': result_a.first_redirect_target if result_a else '',
                'final_url_a': result_a.final_url if result_a else '',
                'response_time_ms_a': result_a.response_time_ms if result_a else None,
                'content_type_a': result_a.content_type if result_a else '',
                'canonical_url_a': result_a.canonical_url if result_a else '',
                'title_a': result_a.title if result_a else '',
                'title_hash_a': result_a.title_hash if result_a else '',
                'notes_a': result_a.notes if result_a else [],
            })
        else:
            comparison.update({
                'source_a': 'none',
                'initial_status_a': None,
                'final_status_a': None,
                'redirect_hops_a': 0,
                'first_redirect_target_a': '',
                'final_url_a': '',
                'response_time_ms_a': None,
                'content_type_a': '',
                'canonical_url_a': '',
                'title_a': '',
                'title_hash_a': '',
                'notes_a': [],
            })
        
        # Site B data
        if url_b:
            result_b = results_b.get(url_b)
            source_b = urls_b.get(url_b, 'unknown')
            
            comparison.update({
                'source_b': source_b,
                'initial_status_b': result_b.initial_status if result_b else None,
                'final_status_b': result_b.final_status if result_b else None,
                'redirect_hops_b': result_b.redirect_hops if result_b else 0,
                'first_redirect_target_b': result_b.first_redirect_target if result_b else '',
                'final_url_b': result_b.final_url if result_b else '',
                'response_time_ms_b': result_b.response_time_ms if result_b else None,
                'content_type_b': result_b.content_type if result_b else '',
                'canonical_url_b': result_b.canonical_url if result_b else '',
                'title_b': result_b.title if result_b else '',
                'title_hash_b': result_b.title_hash if result_b else '',
                'notes_b': result_b.notes if result_b else [],
            })
        else:
            comparison.update({
                'source_b': 'none',
                'initial_status_b': None,
                'final_status_b': None,
                'redirect_hops_b': 0,
                'first_redirect_target_b': '',
                'final_url_b': '',
                'response_time_ms_b': None,
                'content_type_b': '',
                'canonical_url_b': '',
                'title_b': '',
                'title_hash_b': '',
                'notes_b': [],
            })
        
        # Determine comparison class
        comparison['comparison_class'] = self._determine_comparison_class(comparison)
        
        # Combine notes
        notes_list = []
        if comparison['notes_a']:
            for note in comparison['notes_a']:
                notes_list.append(f"A: {note}")
        if comparison['notes_b']:
            for note in comparison['notes_b']:
                notes_list.append(f"B: {note}")
        comparison['notes'] = '; '.join(notes_list)
        
        return comparison
    
    def _determine_comparison_class(self, comparison):
        """
        Determine the comparison class based on results.
        
        See PRD §5.4 for classification logic.
        """
        present_a = comparison['present_on_a']
        present_b = comparison['present_on_b']
        status_a = comparison['final_status_a']
        status_b = comparison['final_status_b']
        
        # Only on one site
        if present_a and not present_b:
            return ComparisonClass.A_ONLY
        if present_b and not present_a:
            return ComparisonClass.B_ONLY
        
        # Both present
        if present_a and present_b:
            # Check for errors
            if status_a and status_a >= 500:
                return ComparisonClass.ERROR_A
            if status_b and status_b >= 500:
                return ComparisonClass.ERROR_B
            
            # Check for redirects
            is_redirect_a = status_a in (301, 302, 303, 307, 308)
            is_redirect_b = status_b in (301, 302, 303, 307, 308)
            
            if is_redirect_a and is_redirect_b:
                # Both redirect - check if to similar location
                final_a = comparison['final_url_a']
                final_b = comparison['final_url_b']
                
                if final_a and final_b:
                    # Extract paths to compare
                    from urllib.parse import urlparse
                    path_a = urlparse(final_a).path
                    path_b = urlparse(final_b).path
                    
                    if path_a == path_b:
                        return ComparisonClass.REDIRECT_BOTH
                    else:
                        return ComparisonClass.REDIRECT_MISMATCH
                
                return ComparisonClass.REDIRECT_BOTH
            
            elif is_redirect_a or is_redirect_b:
                return ComparisonClass.REDIRECT_MISMATCH
            
            # Compare status codes
            if status_a == status_b:
                return ComparisonClass.SAME_STATUS
            else:
                return ComparisonClass.STATUS_MISMATCH
        
        # Default
        return 'unknown'
