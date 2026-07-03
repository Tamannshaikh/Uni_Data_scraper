#!/usr/bin/env python3
"""
Test Jina AI Search integration - programmatic URL filtering (no AI).
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from services.jina_search import search_and_extract_catalog_urls
from config import settings


async def test_jina_integration():
    """Test Jina AI Search + programmatic URL filtering."""
    
    # Test university
    domain = "unimelb.edu.au"
    university_name = "University of Melbourne"
    
    print(f"\n{'='*70}")
    print(f"Testing Jina AI Search Integration (Programmatic Filtering)")
    print(f"{'='*70}")
    print(f"University: {university_name}")
    print(f"Domain: {domain}")
    print(f"{'='*70}\n")
    
    # Check API key
    if not settings.jina_api_key:
        print("❌ ERROR: JINA_API_KEY not found in .env")
        print("\n📝 To get a FREE Jina API key (10M tokens):")
        print("   1. Visit: https://jina.ai/reader")
        print("   2. Click 'Get your API key' or 'key' button")
        print("   3. Copy the key and add to .env:")
        print("      JINA_API_KEY=jina_xxxxx")
        print("\n   No credit card required - 10 million free tokens!")
        return
    
    print("✓ Jina API key found\n")
    
    # Step 1: Jina Search + URL extraction
    print("Step 1: Searching with Jina AI and extracting URLs...")
    print("-" * 70)
    
    candidate_urls = await search_and_extract_catalog_urls(
        domain, 
        university_name,
        api_key=settings.jina_api_key
    )
    
    if not candidate_urls:
        print("❌ No candidate URLs found")
        print("   Check if your API key is valid")
        return
    
    print(f"✓ Found {len(candidate_urls)} candidate catalog URLs")
    
    print(f"\n{'='*70}")
    print(f"RESULTS - Top Candidate URLs (Programmatically Filtered)")
    print(f"{'='*70}")
    
    for i, url in enumerate(candidate_urls[:10], 1):
        print(f"{i:2d}. {url}")
    
    print(f"{'='*70}\n")
    
    print("✓ SUCCESS: Jina search + programmatic filtering completed")
    print("\nNext steps:")
    print("  1. These URLs will be crawled by the pipeline")
    print("  2. Program extractor runs on each page")
    print("  3. Page with most degrees = catalog page")
    print("  4. Final catalog returned with all degree URLs\n")


if __name__ == "__main__":
    asyncio.run(test_jina_integration())
