#!/usr/bin/env python3
"""
Test ASU discovery with improved extraction.
"""
import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

from pipeline.simple_discovery import discover_programs_simple


async def main():
    """Test ASU discovery."""
    print(f"\n{'='*80}")
    print(f"Testing ASU Discovery")
    print(f"{'='*80}\n")
    
    start_time = time.time()
    
    programs = await discover_programs_simple(
        domain="asu.edu",
        university_name="Arizona State University",
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
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
