# Example: Quick start script
# This demonstrates the simplest possible usage

python3 url-compare.py \
  --site-a=https://ansiblepilot.com \
  --site-b=https://ansiblebyexample.com \
  --discovery=both \
  --output=comparison-results.csv

# The tool will:
# 1. Discover URLs from sitemaps and crawling
# 2. Probe each URL on both sites
# 3. Generate a detailed comparison CSV
# 4. Print a summary report

echo "Results written to comparison-results.csv"
