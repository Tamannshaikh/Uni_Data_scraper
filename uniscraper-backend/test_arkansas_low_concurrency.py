"""
Test Arkansas with temporarily reduced concurrency to validate
that high failure rate is due to concurrency/rate limiting, not extraction logic.

This is a TEMPORARY test. If successful, we'll implement adaptive concurrency properly.
"""
import asyncio
import logging
import time
import sys

# Monkey-patch the semaphore value before importing
original_semaphore = asyncio.Semaphore

def patched_semaphore(value):
    # Reduce candidate fetch concurrency from 30 to 10
    if value == 30:
        print(f"[PATCH] Reducing Semaphore({value}) to Semaphore(10) for test")
        return original_semaphore(10)
    return original_semaphore(value)

asyncio.Semaphore = patched_semaphore

from pipeline.program_discovery import discover_programs

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

async def test_arkansas_low_concurrency():
    print("="*80)
    print("ARKANSAS TEST - REDUCED CONCURRENCY (30 -> 10)")
    print("="*80)
    print("\nHypothesis: 84% failure rate is due to too much concurrency")
    print("Test: Reduce from 30 to 10 concurrent fetches")
    print("\nPrevious run (concurrency=30):")
    print("  Fetch failures: 303/361 (84%)")
    print("  Fetch phase: 142s")
    print("  Programs: 75")
    print("\nExpected with concurrency=10:")
    print("  Fetch failures: <30%")
    print("  Fetch phase: ~120s (slightly longer, but more successful)")
    print("  Programs: 150-200")
    print("-"*80)
    
    start = time.time()
    
    try:
        programs = await discover_programs(
            domain="astate.edu",
            university_name="Arkansas State University",
            max_programs=500,
            skip_gemini_threshold=15,
        )
        
        elapsed = time.time() - start
        
        print("\n" + "="*80)
        print("RESULTS")
        print("="*80)
        
        print(f"\n[SUCCESS] Discovery completed")
        print(f"\nTotal runtime: {elapsed:.1f}s")
        print(f"Total programs: {len(programs)}")
        
        print("\n" + "="*80)
        print("COMPARISON")
        print("="*80)
        
        print(f"\nPrograms discovered:")
        print(f"  Concurrency=30: 75")
        print(f"  Concurrency=10: {len(programs)}")
        print(f"  Improvement: {'+' if len(programs) > 75 else ''}{len(programs) - 75} programs")
        
        print(f"\nNote: Check logs above for fetch failure rate")
        print("      If <30%, concurrency hypothesis is confirmed")
        
    except Exception as e:
        print(f"\n[FAILED] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_arkansas_low_concurrency())
