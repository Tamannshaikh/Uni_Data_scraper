"""
Re-validation test for Arkansas State University after tuple-unpacking fix.
Gathers comprehensive metrics for comparison with previous run.
"""
import asyncio
import logging
import time
from pipeline.program_discovery import discover_programs

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

async def test_arkansas():
    print("="*80)
    print("ARKANSAS STATE UNIVERSITY - REVALIDATION TEST")
    print("="*80)
    print("\nPrevious run (with bug):")
    print("  - Crashed after Stage 4 sibling expansion")
    print("  - 52 programs from Stage 3")
    print("  - 77 programs total before crash")
    print("  - 318.5s runtime (before crash)")
    print("  - 89% extraction failure rate (329/368)")
    print("  - 368 Gemini candidates")
    print("  - 9 slug confirmations")
    print("  - 43 auto-confirmed")
    print("\nCurrent run (after tuple-unpacking fix):")
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
        
        print(f"\n[SUCCESS] Discovery completed without crash")
        print(f"\nTotal runtime: {elapsed:.1f}s")
        print(f"Total programs discovered: {len(programs)}")
        
        if programs:
            from collections import Counter
            
            # Degree level breakdown
            levels = Counter(p.get('degree_level', 'Unknown') for p in programs)
            print(f"\nDegree level breakdown:")
            for level, count in sorted(levels.items(), key=lambda x: -x[1]):
                print(f"  {level}: {count}")
            
            # Sample programs
            print(f"\nSample programs (first 10):")
            for i, prog in enumerate(programs[:10], 1):
                print(f"  {i}. {prog.get('program_name', 'Unknown')} ({prog.get('degree_level', 'Unknown')})")
        
        # Comparison with previous run
        print("\n" + "="*80)
        print("COMPARISON WITH PREVIOUS RUN")
        print("="*80)
        
        prev_programs = 77  # Before crash
        prev_time = 318.5  # Before crash
        
        print(f"\nPrograms discovered:")
        print(f"  Previous: {prev_programs} (before crash)")
        print(f"  Current:  {len(programs)}")
        print(f"  Change:   {'+' if len(programs) >= prev_programs else ''}{len(programs) - prev_programs}")
        
        print(f"\nRuntime:")
        print(f"  Previous: {prev_time:.1f}s (before crash)")
        print(f"  Current:  {elapsed:.1f}s")
        print(f"  Change:   {'+' if elapsed >= prev_time else ''}{elapsed - prev_time:.1f}s")
        
        print("\n" + "="*80)
        print("VALIDATION STATUS")
        print("="*80)
        
        if len(programs) >= 50:
            print("\n[PASS] Discovered 50+ programs - Fix successful!")
        else:
            print(f"\n[WARN] Only {len(programs)} programs discovered (expected 50+)")
        
        print("\nNote: Check logs above for:")
        print("  - Auto-confirm count")
        print("  - Slug confirmation count")
        print("  - Gemini candidate count")
        print("  - Extraction failure rate")
        print("  - Sibling expansion completion")
        
        return {
            "status": "success",
            "programs": len(programs),
            "time": elapsed,
            "crashed": False
        }
        
    except Exception as e:
        elapsed = time.time() - start
        
        print("\n" + "="*80)
        print("ERROR")
        print("="*80)
        print(f"\n[FAILED] Discovery crashed: {e}")
        print(f"Runtime before crash: {elapsed:.1f}s")
        
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        
        return {
            "status": "failed",
            "programs": 0,
            "time": elapsed,
            "crashed": True,
            "error": str(e)
        }

if __name__ == "__main__":
    asyncio.run(test_arkansas())
