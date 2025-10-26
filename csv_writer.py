"""CSV output writer for comparison results."""

import csv
from typing import List, Dict


class CSVWriter:
    """Write comparison results to CSV according to PRD §9 specification."""
    
    # Column order as specified in PRD
    COLUMNS = [
        'path_key',
        'present_on_a',
        'present_on_b',
        'source_a',
        'source_b',
        'initial_status_a',
        'final_status_a',
        'redirect_hops_a',
        'first_redirect_target_a',
        'final_url_a',
        'response_time_ms_a',
        'content_type_a',
        'canonical_url_a',
        'initial_status_b',
        'final_status_b',
        'redirect_hops_b',
        'first_redirect_target_b',
        'final_url_b',
        'response_time_ms_b',
        'content_type_b',
        'canonical_url_b',
        'title_a',
        'title_b',
        'title_hash_a',
        'title_hash_b',
        'comparison_class',
        'notes'
    ]
    
    @staticmethod
    def write_csv(comparisons: List[Dict], output_path: str):
        """
        Write comparison results to CSV file.
        
        Args:
            comparisons: List of comparison dictionaries
            output_path: Path to output CSV file
        """
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSVWriter.COLUMNS)
            writer.writeheader()
            
            for comparison in comparisons:
                # Create row with all columns
                row = {}
                for col in CSVWriter.COLUMNS:
                    value = comparison.get(col, '')
                    
                    # Convert boolean to lowercase string
                    if isinstance(value, bool):
                        value = str(value).lower()
                    # Convert None to empty string
                    elif value is None:
                        value = ''
                    # Convert numbers to string
                    elif isinstance(value, (int, float)):
                        value = str(value)
                    # Keep strings as-is
                    else:
                        value = str(value)
                    
                    row[col] = value
                
                writer.writerow(row)
    
    @staticmethod
    def print_summary(comparisons: List[Dict]):
        """
        Print a summary of the comparison results.
        
        Args:
            comparisons: List of comparison dictionaries
        """
        # Count by comparison class
        class_counts = {}
        for comp in comparisons:
            cls = comp.get('comparison_class', 'unknown')
            class_counts[cls] = class_counts.get(cls, 0) + 1
        
        # Count by status for each site
        status_a_counts = {}
        status_b_counts = {}
        
        for comp in comparisons:
            if comp.get('present_on_a'):
                status = comp.get('final_status_a', 'none')
                status_a_counts[status] = status_a_counts.get(status, 0) + 1
            
            if comp.get('present_on_b'):
                status = comp.get('final_status_b', 'none')
                status_b_counts[status] = status_b_counts.get(status, 0) + 1
        
        print("\n" + "="*60)
        print("COMPARISON SUMMARY")
        print("="*60)
        
        print(f"\nTotal unique paths: {len(comparisons)}")
        
        print("\n--- Comparison Classes ---")
        for cls in sorted(class_counts.keys()):
            print(f"  {cls:30s}: {class_counts[cls]:5d}")
        
        print("\n--- Site A Status Codes ---")
        for status in sorted(status_a_counts.keys(), key=lambda x: (x == 'none', x)):
            print(f"  {str(status):10s}: {status_a_counts[status]:5d}")
        
        print("\n--- Site B Status Codes ---")
        for status in sorted(status_b_counts.keys(), key=lambda x: (x == 'none', x)):
            print(f"  {str(status):10s}: {status_b_counts[status]:5d}")
        
        print("\n" + "="*60)
