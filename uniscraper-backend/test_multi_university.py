#!/usr/bin/env python3
"""
Test simple discovery pipeline on multiple universities.
NO code changes - just observe and record results.
"""
import asyncio
import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(__file__))

from pipeline.simple_discovery import discover_programs_simple


# Test universities
UNIVERSITIES = [
    {"name": "Arizona State University", "domain": "asu.edu"},
    {"name": "Ohio State University", "domain": "osu.edu"},
    {"name": "Georgia Institute of Technology", "domain": "gatech.edu"},
    {"name": "Carnegie Mellon University", "domain": "cmu.edu"},
    {"name": "University of California Los Angeles", "domain": "ucla.edu"},
]


async def test_university(name: str, domain: str) -> dict:
    """Test discovery for a single university."""
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"Domain: {domain}")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    
    try:
        programs = await discover_programs_simple(
            domain=domain,
            university_name=name,
            max_catalog_pages=12
        )
        
        elapsed = time.time() - start_time
        
        # Calculate metrics
        with_url = sum(1 for p in programs if p.get('url'))
        without_url = len(programs) - with_url
        url_percentage = (with_url * 100 // len(programs)) if programs else 0
        
        phd_count = sum(1 for p in programs if 'phd' in p.get('degree_level', '').lower())
        masters_count = sum(1 for p in programs if 'master' in p.get('degree_level', '').lower())
        
        # Check for junk (common non-program patterns)
        junk_patterns = ['apply', 'contact', 'about', 'news', 'event', 'admission']
        junk_count = sum(
            1 for p in programs 
            if any(pattern in p['program_name'].lower() for pattern in junk_patterns)
        )
        
        result = {
            "name": name,
            "domain": domain,
            "total_programs": len(programs),
            "with_url": with_url,
            "without_url": without_url,
            "url_percentage": url_percentage,
            "phd_count": phd_count,
            "masters_count": masters_count,
            "junk_count": junk_count,
            "elapsed_seconds": round(elapsed, 1),
            "status": "success",
            "sample_programs": programs[:5] if programs else [],
            "error": None
        }
        
        # Print summary
        print(f"\n{'='*70}")
        print(f"RESULTS: {name}")
        print(f"{'='*70}")
        print(f"Programs found: {len(programs)}")
        print(f"With URLs: {with_url}/{len(programs)} ({url_percentage}%)")
        print(f"PhD programs: {phd_count}")
        print(f"Master's programs: {masters_count}")
        print(f"Junk entries: {junk_count}")
        print(f"Time: {elapsed:.1f}s")
        
        if programs:
            print(f"\nSample programs:")
            for i, prog in enumerate(programs[:5], 1):
                print(f"  {i}. {prog['program_name']}")
                if prog.get('url'):
                    url = prog['url']
                    if len(url) > 60:
                        url = url[:57] + "..."
                    print(f"     {url}")
        
        if junk_count > 0:
            print(f"\n⚠️  WARNING: {junk_count} potential junk entries detected")
        
        print(f"{'='*70}\n")
        
        return result
        
    except Exception as e:
        elapsed = time.time() - start_time
        
        print(f"\n❌ ERROR: {name}")
        print(f"   {type(e).__name__}: {str(e)[:100]}")
        print(f"   Time: {elapsed:.1f}s\n")
        
        return {
            "name": name,
            "domain": domain,
            "total_programs": 0,
            "with_url": 0,
            "without_url": 0,
            "url_percentage": 0,
            "phd_count": 0,
            "masters_count": 0,
            "junk_count": 0,
            "elapsed_seconds": round(elapsed, 1),
            "status": "failed",
            "sample_programs": [],
            "error": str(e)[:200]
        }


async def main():
    """Test all universities."""
    print(f"\n{'#'*70}")
    print(f"MULTI-UNIVERSITY DISCOVERY TEST")
    print(f"{'#'*70}")
    print(f"Testing {len(UNIVERSITIES)} universities")
    print(f"NO code changes - observation only")
    print(f"{'#'*70}\n")
    
    results = []
    total_start = time.time()
    
    for uni in UNIVERSITIES:
        result = await test_university(uni["name"], uni["domain"])
        results.append(result)
    
    total_elapsed = time.time() - total_start
    
    # Print summary table
    print(f"\n{'#'*70}")
    print(f"SUMMARY TABLE")
    print(f"{'#'*70}\n")
    
    print(f"{'University':<35} {'Programs':<10} {'URLs':<10} {'Junk':<8} {'Time':<8}")
    print(f"{'-'*70}")
    
    for r in results:
        name = r['name'][:33]
        programs = f"{r['total_programs']}"
        urls = f"{r['url_percentage']}%"
        junk = f"{r['junk_count']}"
        elapsed = f"{r['elapsed_seconds']}s"
        
        print(f"{name:<35} {programs:<10} {urls:<10} {junk:<8} {elapsed:<8}")
    
    print(f"{'-'*70}")
    print(f"Total time: {total_elapsed:.1f}s")
    print(f"\n{'#'*70}\n")
    
    # Save detailed results to JSON
    output_file = "test_results_multi_university.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"✓ Detailed results saved to: {output_file}\n")
    
    # Print observations prompt
    print(f"{'='*70}")
    print("OBSERVATIONS TO RECORD:")
    print(f"{'='*70}")
    print("1. Which universities had good results (50+ programs, 90%+ URLs)?")
    print("2. Which universities failed or had very low counts?")
    print("3. Are there common patterns in junk entries?")
    print("4. Do certain types of universities (US vs UK, large vs small) work better?")
    print("5. Are there catalog structures the pipeline misses?")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
