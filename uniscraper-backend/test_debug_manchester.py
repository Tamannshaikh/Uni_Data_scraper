"""Run discover_programs directly — bypass cache and orchestrator."""
import asyncio, sys, logging
sys.path.insert(0, ".")

# Enable full logging
logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

from pipeline.program_discovery import discover_programs

async def test():
    import time
    start = time.time()
    programs = await discover_programs("manchester.ac.uk", "University of Manchester")
    elapsed = time.time() - start
    
    print(f"\n{'='*55}")
    print(f"Time:     {elapsed:.1f}s")
    print(f"Programs: {len(programs)}")
    
    from collections import Counter
    levels = Counter(p.get("degree_level", "?") for p in programs)
    print(f"Breakdown: {dict(levels)}")
    
    print("\nFirst 10:")
    for p in programs[:10]:
        print(f"  [{p['degree_level']:12s}] {p['program_name'][:55]}")
        print(f"                   {p['url']}")

asyncio.run(test())
