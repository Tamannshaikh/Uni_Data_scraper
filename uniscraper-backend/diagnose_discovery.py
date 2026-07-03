#!/usr/bin/env python3
"""
Diagnose discovery coverage issues.
Print ALL URLs found at each stage to understand filtering.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from services.jina_search import search_and_extract_catalog_urls
from config import settings


UNIVERSITIES = [
    {"name": "Arizona State University", "domain": "asu.edu"},
    {"name": "University of California Los Angeles", "domain": "ucla.edu"},
    {"name": "Ohio State University", "domain": "osu.edu"},
]


async def diagnose_university(name: str, domain: str):
    """Diagnose discovery for a single university."""
    print(f"\n{'='*80}")
    print(f"DIAGNOSING: {name}")
    print(f"Domain: {domain}")
    print(f"{'='*80}\n")
    
    # Call Jina search with verbose output
    catalog_urls = await search_and_extract_catalog_urls(
        domain,
        name,
        api_key=settings.jina_api_key,
        verbose=True  # Enable verbose diagnostics
    )
    
    print(f"\n{'='*80}")
    print(f"FINAL CATALOG URLs RETURNED: {len(catalog_urls)}")
    print(f"{'='*80}")
    
    for i, url in enumerate(catalog_urls[:20], 1):  # Show top 20
        print(f"{i:2d}. {url}")
    
    if len(catalog_urls) > 20:
        print(f"... and {len(catalog_urls) - 20} more")
    
    print(f"\n{'='*80}\n")


async def main():
    """Diagnose all universities."""
    print(f"\n{'#'*80}")
    print(f"DISCOVERY DIAGNOSIS")
    print(f"{'#'*80}")
    print(f"Purpose: Understand what URLs Jina finds and how they're scored")
    print(f"{'#'*80}\n")
    
    for uni in UNIVERSITIES:
        await diagnose_university(uni["name"], uni["domain"])
        print("\n")


if __name__ == "__main__":
    asyncio.run(main())
