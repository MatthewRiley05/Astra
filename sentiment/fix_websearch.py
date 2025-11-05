"""
Patch for asset-sentiment-analyzer websearch_funcs.py
Fixes the KeyError: 'q' issue with Google search results
"""

import os

# Path to the package file
PACKAGE_PATH = "/usr/local/lib/python3.11/site-packages/asset_sentiment_analyzer/websearch_funcs.py"

# Read the file
with open(PACKAGE_PATH, "r") as f:
    content = f.read()

# Fix the filter_result function to handle missing 'q' parameter
old_code = """def filter_result(link):
    \"\"\"Filter valid links from Google search results.\"\"\"
    if link.startswith('/url?'):
        link = parse_qs(urlparse(link).query)['q'][0]
    o = urlparse(link)
    if o.netloc and 'google' not in o.netloc:"""

new_code = """def filter_result(link):
    \"\"\"Filter valid links from Google search results.\"\"\"
    if link.startswith('/url?'):
        parsed = parse_qs(urlparse(link).query)
        if 'q' in parsed:
            link = parsed['q'][0]
        else:
            return None  # Skip malformed links
    o = urlparse(link)
    if o.netloc and 'google' not in o.netloc:"""

# Apply the patch
if old_code in content:
    content = content.replace(old_code, new_code)
    with open(PACKAGE_PATH, "w") as f:
        f.write(content)
    print("✓ Patch applied successfully")
else:
    print("⚠ Could not find code to patch (might already be patched)")
