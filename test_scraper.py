#!/usr/bin/env python3
"""
Quick test script to verify Firecrawl scraping functionality
"""

import os
from dotenv import load_dotenv
from firecrawl import Firecrawl

load_dotenv()

# Initialize Firecrawl
firecrawl = Firecrawl(api_key=os.environ.get("FIRECRAWL_API_KEY"))

# Test URL
url = "https://chatgpt.com/share/68c69638-63e0-8008-91d4-b88234b78a8d"

print(f"Testing Firecrawl on: {url}")
print(f"API Key exists: {bool(os.environ.get('FIRECRAWL_API_KEY'))}")
print("=" * 50)

try:
    # Scrape with markdown and summary formats
    doc = firecrawl.scrape(url, formats=["markdown", "summary"])

    # Access data directly from Document object attributes
    if doc and hasattr(doc, 'markdown'):
        print("✅ Success: True")
        
        # Display markdown content
        markdown = doc.markdown
        print(f"📄 Markdown length: {len(markdown)} chars")
        print("📄 Markdown preview (first 500 chars):")
        print(markdown[:500])
        print("...")
        
        # Display summary
        if hasattr(doc, 'summary') and doc.summary:
            summary = doc.summary
            print(f"📋 Summary length: {len(summary)} chars")
            print("📋 Summary:")
            print(summary)
        
        # Display metadata
        if hasattr(doc, 'metadata') and doc.metadata:
            metadata = doc.metadata
            print("🏷️  Metadata:")
            print(f"   Title: {getattr(metadata, 'title', 'N/A')}")
            print(f"   URL: {getattr(metadata, 'url', 'N/A')}")
            print(f"   Status: {getattr(metadata, 'status_code', 'N/A')}")
    else:
        print("❌ Success: False")
        print(f"Document object: {doc}")
        print(f"Document type: {type(doc)}")

except Exception as e:
    print(f"❌ Exception occurred: {str(e)}")
    import traceback
    traceback.print_exc()