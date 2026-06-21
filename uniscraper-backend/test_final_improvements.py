"""
Final verification test with all improvements:
1. Expanded auto-confirmation patterns (target: 60%+ reduction)
2. Confidence-based prioritization (best candidates first)
3. Gemini throughput logging (understand bottleneck)
4. Terminal state handling (partial results)
"""
import asyncio
import sys
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s: %(message)s"
)

sys.path.insert(0, ".")

from pipeline.program_discovery import discover_programs
from utils.program_filters import filter_graduate_programs

async def test():
    print("\n" + "="*80)
    print("FINAL IMPROVEMENTS VERIFICATION - MANCHESTER")
    print("="*80)
    print("\nTarget metrics:")
    print("  1. Auto-confirmation: 180+ / 300 candidates (60%+ reduction)")
    print("  2. Gemini calls: <120 remaining")
    print("  3. High-confidence candidates classified first")
    print("  4. Complete or meaningful partial result within 4 minutes")
    print("  5. Graduate-only output (0 undergraduate contamination)")
    
    start = time.time()
    
    print("\n" + "-"*80)
    print("Starting discovery...")
    print("-"*80)
    
    all_programs = await discover_programs("manchester.ac.uk", "University of Manchester")
    
    elapsed = time.time() - start
    
    print(f"\n{'='*80}")
    print(f"RESULTS")
    print(f"{'='*80}")
    print(f"\nTotal time:     {elapsed:.1f}s")
    print(f"Total programs: {len(all_programs)}")
    
    if len(all_programs) == 0:
        print("\n❌ No programs found")
        return
    
    # Degree breakdown
    from collections import Counter
    all_levels = Counter(p.get("degree_level", "Unknown") for p in all_programs)
    print(f"\nAll programs by degree level:")
    for level, count in sorted(all_levels.items(), key=lambda x: -x[1]):
        print(f"  {level:15s}: {count}")
    
    # Graduate filtering
    grad_programs = filter_graduate_programs(all_programs)
    print(f"\nGraduate programs: {len(grad_programs)}/{len(all_programs)}")
    
    # Validation
    UNDERGRAD_LEVELS = {"Bachelor's", "Associate's", "Unspecified"}
    contamination = sum(count for level, count in all_levels.items() if level in UNDERGRAD_LEVELS)
    
    print(f"\n{'='*80}")
    print("KEY METRICS")
    print("="*80)
    
    # Check logs for auto-confirmation rate
    print("\nAuto-confirmation effectiveness:")
    print("  Check logs for: 'X auto-confirmed, Y need Gemini'")
    print("  Target: 180+ auto-confirmed (60% of 300 candidates)")
    
    print("\nGemini throughput:")
    print("  Check logs for: 'Gemini batch N: X candidates classified in Y.Ys'")
    print("  This shows per-batch processing time")
    
    print("\nGraduate filtering:")
    if contamination == 0 and len(grad_programs) > 0:
        print(f"  ✓ Clean: {len(grad_programs)} graduate programs, 0 undergraduate")
    else:
        print(f"  ⚠️  Contamination: {contamination} undergraduate programs found")
    
    print(f"\nCompletion:")
    if elapsed < 300:
        print(f"  ✓ Completed in {elapsed:.1f}s (< 5 minutes)")
    else:
        print(f"  ⚠️  Took {elapsed:.1f}s (>= 5 minutes)")
    
    # Sample output
    print(f"\nSample programs (first 15):")
    for p in all_programs[:15]:
        print(f"  [{p['degree_level']:12s}] {p['program_name'][:60]}")
    
    print(f"\n{'='*80}")
    print("ASSESSMENT")
    print("="*80)
    print("\nReview the logs above to verify:")
    print("  1. Auto-confirmation rate (should be 60%+ of candidates)")
    print("  2. Gemini batch timing (to understand throughput bottleneck)")
    print("  3. No 429 errors (rate limiter working)")
    print("  4. Confidence prioritization (best candidates processed first)")
    print("  5. Graduate filtering (0 contamination)")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(test())
