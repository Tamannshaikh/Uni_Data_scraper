#!/usr/bin/env python3
"""
Test UCLA discovery with verbose logging.
"""
import asyncio
import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(__file__))

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(name)s - %(message)s'
)

from pipeline.simple_discovery import discover_programs_simple


async def main():
    """Test UCLA discovery."""
    print(f"\n{'='*80}")
    print(f"Testing UCLA Discovery (Verbose)")
    print(f"{'='*80}\n")
    
    start_time = time.time()
    
    programs = await discover_programs_simple(
        domain="ucla.edu",
        university_name="University of California Los Angeles",
        max_catalog_pages=12
    )
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*80}")
    print(f"RESULTS")
    print(f"{'='*80}")
    print(f"Programs found: {len(programs)}")
    print(f"Time: {elapsed:.1f}s")
    
    if programs:
        # Count by degree level
        phd = sum(1 for p in programs if 'phd' in p.get('degree_level', '').lower())
        masters = sum(1 for p in programs if 'master' in p.get('degree_level', '').lower())
        
        print(f"PhD programs: {phd}")
        print(f"Master's programs: {masters}")
        
        # URL coverage
        with_url = sum(1 for p in programs if p.get('url'))
        print(f"With URLs: {with_url}/{len(programs)} ({with_url*100//len(programs)}%)")
        
        print(f"\nFirst 20 programs:")
        for i, prog in enumerate(programs[:20], 1):
            print(f"{i:2d}. {prog['program_name']}")
            if prog.get('url'):
                url = prog['url']
                if len(url) > 70:
                    url = url[:67] + "..."
                print(f"     {url}")
    else:
        print("No programs found - check debug logs above for issues")
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
