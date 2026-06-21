"""Test discovery across multiple universities to verify generalization."""
import asyncio
import logging
import time
from pipeline.program_discovery import discover_programs

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

UNIVERSITIES = [
    ("manchester.ac.uk", "University of Manchester"),
    ("ed.ac.uk", "University of Edinburgh"),
    ("mit.edu", "Massachusetts Institute of Technology"),
    ("astate.edu", "Arkansas State University"),
]

async def test_university(domain: str, name: str):
    print(f"\n{'=' * 80}")
    print(f"Testing: {name} ({domain})")
    print(f"{'=' * 80}")
    
    start = time.time()
    
    try:
        programs = await discover_programs(
            domain=domain,
            university_name=name,
            max_programs=500,  # Increased from 200
            skip_gemini_threshold=15,  # Skip Gemini if <15 candidates
        )
        
        elapsed = time.time() - start
        
        print(f"\n[SUCCESS]")
        print(f"  Time: {elapsed:.1f}s")
        print(f"  Programs: {len(programs)}")
        
        if programs:
            from collections import Counter
            levels = Counter(p['degree_level'] for p in programs)
            print(f"  Breakdown:")
            for level, count in sorted(levels.items(), key=lambda x: -x[1])[:5]:
                print(f"    {level}: {count}")
        
        return {"status": "success", "time": elapsed, "programs": len(programs)}
        
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n[FAILED]: {e}")
        return {"status": "failed", "time": elapsed, "error": str(e)}

async def main():
    print("=" * 80)
    print("MULTI-UNIVERSITY DISCOVERY TEST")
    print("=" * 80)
    print("\nTesting discovery pipeline generalization across:")
    for domain, name in UNIVERSITIES:
        print(f"  - {name} ({domain})")
    print()
    
    results = {}
    for domain, name in UNIVERSITIES:
        result = await test_university(domain, name)
        results[name] = result
        await asyncio.sleep(2)  # Brief pause between tests
    
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    
    total_time = sum(r['time'] for r in results.values())
    successes = sum(1 for r in results.values() if r['status'] == 'success')
    total_programs = sum(r.get('programs', 0) for r in results.values())
    
    print(f"\nTotal time: {total_time:.1f}s")
    print(f"Success rate: {successes}/{len(UNIVERSITIES)}")
    print(f"Total programs discovered: {total_programs}")
    
    print(f"\nPer-university results:")
    for name, result in results.items():
        status_icon = "[OK]" if result['status'] == 'success' else "[FAIL]"
        programs_str = f"{result.get('programs', 0)} programs" if result['status'] == 'success' else result.get('error', 'failed')
        print(f"  {status_icon} {name:40s} {result['time']:6.1f}s  {programs_str}")
    
    print(f"\n{'=' * 80}")
    
    if successes == len(UNIVERSITIES):
        print("[ALL TESTS PASSED] - Pipeline generalizes well!")
    elif successes > 0:
        print(f"[PARTIAL SUCCESS] - {successes}/{len(UNIVERSITIES)} universities worked")
    else:
        print("[ALL TESTS FAILED] - Pipeline needs work")
    
    print(f"{'=' * 80}")

asyncio.run(main())
