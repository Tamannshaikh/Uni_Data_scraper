"""
Quick validation test for Purdue after implementing priority fixes:

1. ✅ Removed skip_gemini_threshold logic
2. ✅ Lowered confidence threshold (0.75 → 0.55)
3. ✅ Expanded auto-confirm patterns
4. ✅ Added Firecrawl fallback for 403/429 errors
5. ✅ Added detailed LLM output logging

Expected improvements:
- Before: 17 programs
- After: 100+ programs (targeting 150+)
"""
import asyncio
import logging
from pipeline.program_discovery import discover_programs
from collections import Counter

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

async def test_purdue():
    print("="*80)
    print("PURDUE VALIDATION TEST - After Priority Fixes")
    print("="*80)
    print("\nFixes implemented:")
    print("  1. Removed skip_gemini_threshold (was preventing classification)")
    print("  2. Lowered confidence threshold: 0.75 -> 0.55")
    print("  3. Expanded auto-confirm patterns (added /graduate/mba/, etc.)")
    print("  4. Added Firecrawl fallback for 403/429 errors")
    print("  5. Added detailed LLM output logging")
    print("\nBaseline (previous run):")
    print("  Programs: 17")
    print("  Runtime: 279.7s")
    print("  Gemini quota: exhausted (503 errors)")
    print("\nTarget:")
    print("  Programs: 150+")
    print("  Improved classification rate")
    print("-"*80)
    
    import time
    start = time.time()
    
    programs = await discover_programs(
        domain="purdue.edu",
        university_name="Purdue University",
        max_programs=500,
    )
    
    elapsed = time.time() - start
    
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    
    print(f"\nTotal programs: {len(programs)}")
    print(f"Runtime: {elapsed:.1f}s")
    
    if programs:
        # Degree breakdown
        degree_levels = Counter(p.get('degree_level', 'Unknown') for p in programs)
        print(f"\nDegree level breakdown:")
        for level, count in degree_levels.most_common():
            percentage = (count / len(programs) * 100)
            print(f"  {level}: {count} ({percentage:.1f}%)")
        
        # Quality check
        undergrad_count = sum(
            count for level, count in degree_levels.items()
            if any(word in level.lower() for word in ["bachelor", "undergraduate", "bs", "ba", "bsc"])
        )
        
        print(f"\nQuality metrics:")
        print(f"  Graduate programs: {len(programs) - undergrad_count}")
        print(f"  Undergraduate (contamination): {undergrad_count}")
        
        # Sample programs
        print(f"\nSample programs (first 10):")
        for i, prog in enumerate(programs[:10], 1):
            print(f"  {i}. {prog.get('program_name', 'N/A')} ({prog.get('degree_level', 'N/A')})")
            print(f"     Confidence: {prog.get('confidence', 0):.2f}")
            print(f"     {prog.get('url', 'N/A')[:80]}")
    
    print("\n" + "="*80)
    print("COMPARISON")
    print("="*80)
    
    baseline = 17
    improvement = len(programs) - baseline
    improvement_pct = (improvement / baseline * 100) if baseline > 0 else 0
    
    print(f"\nPrograms:")
    print(f"  Baseline: {baseline}")
    print(f"  Current:  {len(programs)}")
    print(f"  Change:   {'+' if improvement > 0 else ''}{improvement} ({'+' if improvement_pct > 0 else ''}{improvement_pct:.0f}%)")
    
    print("\n" + "="*80)
    print("VERDICT")
    print("="*80)
    
    if len(programs) >= 150:
        print("\n✅ SUCCESS - Fixes are working!")
        print(f"   Discovered {len(programs)} programs (target: 150+)")
    elif len(programs) >= 100:
        print("\n⚠️ GOOD PROGRESS")
        print(f"   Discovered {len(programs)} programs (target: 150+)")
        print("   Significant improvement but short of target")
    elif len(programs) > baseline:
        print("\n⚠️ SOME IMPROVEMENT")
        print(f"   Discovered {len(programs)} programs (up from {baseline})")
        print("   Still far from target of 150+")
    else:
        print("\n❌ NO IMPROVEMENT")
        print(f"   Still only {len(programs)} programs")
        print("   Fixes did not have expected impact")
    
    print("\nCheck logs above for:")
    print("  - Auto-confirm successes")
    print("  - Firecrawl fallback usage")
    print("  - LLM classification details")
    print("  - Confidence score distribution")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_purdue())
