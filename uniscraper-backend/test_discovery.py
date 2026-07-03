#!/usr/bin/env python3
"""
Test the full program discovery pipeline with Jina integration
"""
import asyncio
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(__file__))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from pipeline.program_discovery import collect_candidates
from config import settings


async def test_discovery():
    domain = "unimelb.edu.au"
    university_name = "University of Melbourne"
    
    print(f"\n{'='*70}")
    print(f"Testing Program Discovery with Jina AI")
    print(f"{'='*70}")
    print(f"University: {university_name}")
    print(f"Domain: {domain}")
    print(f"{'='*70}\n")
    
    print("API Keys Status:")
    print(f"  Jina API Key: {'✓ Present' if settings.jina_api_key else '✗ Missing'}")
    print(f"  Gemini API Key: {'✓ Present' if settings.gemini_api_key else '✗ Missing'}")
    print(f"  SerpAPI Key: {'✓ Present' if settings.serpapi_key else '✗ Missing'}")
    print()
    
    print("Starting candidate collection...")
    print("-" * 70)
    
    candidates = await collect_candidates(domain, university_name)
    
    print(f"\n{'='*70}")
    print(f"RESULTS")
    print(f"{'='*70}")
    print(f"Total candidates collected: {len(candidates)}")
    
    if candidates:
        print(f"\nFirst 10 candidates:")
        for i, url in enumerate(candidates[:10], 1):
            print(f"  {i}. {url}")
    
    print(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(test_discovery())
