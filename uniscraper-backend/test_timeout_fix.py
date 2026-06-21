"""
Quick test to validate Fix #1: Timeout increase from 6s to 10s

Compares results with previous run to measure improvement.
"""
import asyncio
import logging
import time
from pipeline.program_discovery import discover_programs

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

async def test_timeout_fix():
    print("="*80)
    print("ARKANSAS TEST - FIX #1 VALIDATION (Timeout 6s -> 10s)")
    print("="*80)
    print("\nChange implemented:")
    print("  File: pipeline/program_discovery.py, line ~973")
    print("  Before: timeout=6.0")
    print("  After:  timeout=10.0")
    print("\nBaseline (timeout=6s):")
    print("  Fetch failures: 303/361 (84%)")
    print("  Programs: 75")
    print("  Fetch phase: 142s")
    print("\nExpected (timeout=10s):")
    print("  Fetch failures: <40%")
    print("  Programs: 150-200")
    print("  Fetch phase: ~160s")
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
        print("COMPARISON WITH BASELINE")
        print("="*80)
        
        baseline_programs = 75
        baseline_time = 318.5
        
        print(f"\nPrograms discovered:")
        print(f"  Baseline (6s timeout):  {baseline_programs}")
        print(f"  Current (10s timeout):  {len(programs)}")
        improvement = len(programs) - baseline_programs
        improvement_pct = (improvement / baseline_programs * 100) if baseline_programs > 0 else 0
        print(f"  Improvement: {'+' if improvement > 0 else ''}{improvement} ({'+' if improvement_pct > 0 else ''}{improvement_pct:.1f}%)")
        
        print(f"\nRuntime:")
        print(f"  Baseline: {baseline_time:.1f}s")
        print(f"  Current:  {elapsed:.1f}s")
        time_diff = elapsed - baseline_time
        print(f"  Difference: {'+' if time_diff > 0 else ''}{time_diff:.1f}s")
        
        print("\n" + "="*80)
        print("VALIDATION")
        print("="*80)
        
        if len(programs) >= 150:
            print("\n[PASS] Discovered 150+ programs (target met)")
        elif len(programs) > baseline_programs:
            print(f"\n[PARTIAL] Improved from {baseline_programs} to {len(programs)}, but below target (150)")
        else:
            print(f"\n[FAIL] No improvement in program count")
        
        print("\nNote: Check logs above for:")
        print("  - Fetch failure rate (should be <40%)")
        print("  - Fetch phase duration")
        print("  - If still high failures, consider Fix #2 (reduce concurrency)")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_timeout_fix())
