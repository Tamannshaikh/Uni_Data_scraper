#!/usr/bin/env python3
"""
Test the SIMPLE discovery pipeline:
Jina → Catalog Pages → Extract Programs → Done

NO SerpAPI, NO OpenRouter, NO AI classification
"""
import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from pipeline.simple_discovery import discover_programs_simple


async def test():
    domain = "unimelb.edu.au"
    university_name = "University of Melbourne"
    
    print(f"\n{'='*70}")
    print(f"SIMPLE DISCOVERY TEST")
    print(f"{'='*70}")
    print(f"University: {university_name}")
    print(f"Domain: {domain}")
    print(f"{'='*70}\n")
    
    print("Pipeline: Jina → Catalog Pages → Extract → Done\n")
    print("Running discovery (this will take 1-2 minutes)...\n")
    
    programs = await discover_programs_simple(
        domain=domain,
        university_name=university_name,
        max_catalog_pages=12  # Balanced for speed vs coverage
    )
    
    print(f"\n{'='*70}")
    print(f"RESULTS")
    print(f"{'='*70}\n")
    
    print(f"University: {university_name}")
    print(f"Programs Found: {len(programs)}\n")
    
    if programs:
        print(f"{'-'*70}\n")
        print("PROGRAM LIST:\n")
        
        for i, prog in enumerate(programs[:30], 1):
            name = prog.get("program_name", "Unknown")
            level = prog.get("degree_level", "")
            url = prog.get("url", "")
            
            # Highlight programs without URLs
            if not url:
                print(f"{i:2d}. {name} ⚠️ NO URL")
            else:
                print(f"{i:2d}. {name}")
            
            if level:
                print(f"    Level: {level}")
            if url and len(url) < 80:
                print(f"    URL: {url}")
            print()
        
        if len(programs) > 30:
            print(f"... and {len(programs) - 30} more programs\n")
        
        print(f"{'-'*70}\n")
        
        # Show quality metrics
        phd_count = sum(1 for p in programs if 'phd' in p['degree_level'].lower())
        masters_count = sum(1 for p in programs if 'master' in p['degree_level'].lower())
        with_url = sum(1 for p in programs if p.get('url'))
        without_url = len(programs) - with_url
        
        print("Quality Metrics:")
        print(f"  PhD programs: {phd_count}")
        print(f"  Master's programs: {masters_count}")
        print(f"  Other: {len(programs) - phd_count - masters_count}")
        print(f"\n  WITH URLs: {with_url}/{len(programs)} ({with_url * 100 // len(programs)}%)")
        print(f"  WITHOUT URLs: {without_url}/{len(programs)} ({without_url * 100 // len(programs)}%)")
        
        if without_url > 0:
            print(f"\n  ⚠️ WARNING: {without_url} programs have no URL")
            print("  These cannot be scraped for detailed information!")
            print("\n  Programs without URLs:")
            for p in programs:
                if not p.get('url'):
                    print(f"    - {p['program_name']}")
        
    else:
        print("No programs found\n")
    
    print(f"\n{'='*70}\n")
    
    # Show sample JSON
    if programs:
        print("Sample JSON Output:\n")
        sample = {
            "university": university_name,
            "domain": domain,
            "programs_count": len(programs),
            "programs": programs[:3]
        }
        print(json.dumps(sample, indent=2))
        print(f"\n{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(test())
