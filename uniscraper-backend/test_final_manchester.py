"""Final Manchester test with all optimizations."""
import asyncio
import logging
from pipeline.program_discovery import discover_programs

# Enable INFO logging to see all metrics
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

async def test():
    print("=" * 80)
    print("MANCHESTER DISCOVERY - FINAL TEST WITH ALL OPTIMIZATIONS")
    print("=" * 80)
    print("\nOptimizations applied:")
    print("  [x] Slug-based auto-confirm (no fetch for msc-, phd-, etc.)")
    print("  [x] Reduced fetch timeout (5s instead of 8s)")
    print("  [x] 403 Forbidden early exit (no retries)")
    print("  [x] Better exception logging")
    print("=" * 80)
    print()
    
    import time
    start = time.time()
    
    programs = await discover_programs(
        domain="manchester.ac.uk",
        university_name="University of Manchester",
        max_pages=30
    )
    
    elapsed = time.time() - start
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total time:      {elapsed:.1f}s")
    print(f"Programs found:  {len(programs)}")
    
    # Breakdown by degree level
    from collections import Counter
    levels = Counter(p['degree_level'] for p in programs)
    print(f"\nDegree breakdown:")
    for level, count in sorted(levels.items(), key=lambda x: -x[1]):
        print(f"  {level:15s}: {count:3d}")
    
    print(f"\nFirst 15 programs:")
    for i, prog in enumerate(programs[:15], 1):
        print(f"{i:2d}. [{prog['degree_level']:12s}] {prog['program_name']}")
        print(f"    {prog['url']}")
    
    print("\n" + "=" * 80)
    print("Check logs above for detailed timing breakdown")
    print("=" * 80)

asyncio.run(test())
