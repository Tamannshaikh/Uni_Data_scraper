#!/usr/bin/env python3
"""
Debug version - see what Gemini receives and responds with
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from services.jina_search import search_program_catalog, ask_gemini_for_catalog_url
from config import settings


async def test_debug():
    domain = "unimelb.edu.au"
    university_name = "University of Melbourne"
    
    print("Fetching Jina results...")
    search_content = await search_program_catalog(
        domain, 
        university_name,
        api_key=settings.jina_api_key
    )
    
    if not search_content:
        print("No search results")
        return
    
    print(f"\nJina returned {len(search_content)} chars")
    print("\nFirst 2000 chars of search content:")
    print("=" * 70)
    print(search_content[:2000])
    print("=" * 70)
    
    print("\n\nCalling Gemini...")
    catalog_result = await ask_gemini_for_catalog_url(
        university_name,
        domain,
        search_content,
        settings.gemini_api_key
    )
    
    print("\nGemini result:")
    print(catalog_result)


if __name__ == "__main__":
    asyncio.run(test_debug())
