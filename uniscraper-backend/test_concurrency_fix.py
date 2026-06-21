"""
Validation test for CORRECT fix: Concurrency reduction from 30 to 15.

Based on stress test results showing 69% improvement with this change.
"""
import asyncio
import logging
import time
from pipeline.program_discovery import discover_programs

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

async def test_concurrency_fix():
    print("="*80)
    print("ARKANSAS VALIDATION - CORRECT FIX (Concurrency 30 -> 15)")
    print("="*80)
    print("\nFix implemented:")
    print("  File: pipeline/program_discovery.py, line ~959")
    print("  Before: fetch_sem = asyncio.Semaphore(30)")
    print("  After:  fetch_sem = asyncio.Semaphore(15)")
    print("\nStress test results:")
    print("  Concurrency=30: 62% failure rate, avg=14.68s/URL")
    print("  Concurrency=15: 19% failure rate, avg=7.11s/URL")
    print("  Improvement: 69% reduction in failures!")
    print("\nBaseline (full discovery, c=30):")
    print("  Fetch failures: 303/361 (84%)")
    print("  Programs: 75")
    print("  Fetch phase: 142s")
    print("\nExpected (full discovery, c=15):")
    print("  Fetch failures: ~70/361 (19%)")
    print("  Programs: 200-250")
    print("  Fetch phase: ~120s")
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
        
        if programs:
            from collections import Counter
            levels = Counter(p.get('degree_level', 'Unknown') for p in programs)
            print(f"\nDegree breakdown:")
            for level, count in sorted(levels.items(), key=lambda x: -x[1])[:5]:
                print(f"  {level}: {count}")
        
        print("\n" + "="*80)
        print("COMPARISON")
        print("="*80)
        
        baseline_programs = 75
        baseline_time = 318.5
        
        print(f"\nPrograms:")
        print(f"  Baseline (c=30):  {baseline_programs}")
        print(f"  Current (c=15):   {len(programs)}")
        improvement = len(programs) - baseline_programs
        improvement_pct = (improvement / baseline_programs * 100) if baseline_programs > 0 else 0
        print(f"  Improvement:      {'+' if improvement > 0 else ''}{improvement} ({'+' if improvement_pct > 0 else ''}{improvement_pct:.0f}%)")
        
        print(f"\nRuntime:")
        print(f"  Baseline: {baseline_time:.1f}s")
        print(f"  Current:  {elapsed:.1f}s")
        
        print("\n" + "="*80)
        print("VALIDATION")
        print("="*80)
        
        if len(programs) >= 200:
            print("\n[PASS] Discovered 200+ programs")
            print("  Concurrency reduction successfully fixed Arkansas!")
        elif len(programs) >= 150:
            print(f"\n[PARTIAL PASS] {len(programs)} programs (target was 200+)")
            print("  Significant improvement but below ideal")
        elif len(programs) > baseline_programs:
            print(f"\n[MARGINAL] Improved to {len(programs)} (from {baseline_programs})")
            print("  Some improvement but may need additional fixes")
        else:
            print(f"\n[UNEXPECTED] No improvement")
            print("  This contradicts stress test results - investigate")
        
        print("\nNote: Check logs for fetch failure rate")
        print("      Stress test showed 19% - should be similar")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_concurrency_fix())
