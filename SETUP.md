# Setup Guide for URL Comparison Tool

## Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Make the Script Executable (Optional)

```bash
chmod +x url-compare.py
```

### 3. Test the Installation

```bash
# Run a simple test
python url-compare.py --help
```

### 4. Run Your First Comparison

```bash
python url-compare.py \
  --site-a=https://ansiblepilot.com \
  --site-b=https://ansiblebyexample.com \
  --discovery=sitemap \
  --output=test-results.csv
```

## Virtual Environment Setup (Recommended)

Using a virtual environment keeps dependencies isolated:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Run the tool
python url-compare.py --help
```

## Verify Installation

Run the unit tests to verify everything is working:

```bash
python -m pytest test_url_normalizer.py -v
```

Expected output:
```
test_url_normalizer.py::TestURLNormalizer::test_basic_normalization PASSED
test_url_normalizer.py::TestURLNormalizer::test_default_port_removal PASSED
...
```

## Configuration

1. Copy the example config:
```bash
cp config.yaml my-config.yaml
```

2. Edit `my-config.yaml` with your settings

3. Run with your config:
```bash
python url-compare.py --config=my-config.yaml
```

## Troubleshooting

### Import Errors

If you see import errors, ensure all dependencies are installed:
```bash
pip install -r requirements.txt --upgrade
```

### Permission Denied

Make the script executable:
```bash
chmod +x url-compare.py
```

### SSL Certificate Errors

If you encounter SSL errors, you may need to update certificates:
```bash
pip install --upgrade certifi
```

### Rate Limiting Issues

If you're being rate limited, reduce concurrency:
```bash
python url-compare.py \
  --site-a=https://example.com \
  --site-b=https://example.org \
  --concurrency=2 \
  --rate-limit-rps=1
```

## Next Steps

1. Read the [README.md](README.md) for full documentation
2. Check [example.sh](example.sh) for usage examples
3. Customize [config.yaml](config.yaml) for your needs

## System Requirements

- **Python**: 3.8 or higher
- **RAM**: 512MB minimum (more for large sites)
- **Disk**: Minimal (CSV outputs are typically < 10MB)
- **Network**: Internet connection required for probing

## Platform Support

✅ Linux  
✅ macOS  
✅ Windows (with minor path adjustments)

## Getting Help

- Check the README.md for detailed documentation
- Run with `--help` to see all options
- Review the example config.yaml for all settings
