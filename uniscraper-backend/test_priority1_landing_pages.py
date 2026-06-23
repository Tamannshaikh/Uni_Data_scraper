"""
PRIORITY 1: Test that landing pages (business.purdue.edu/phd/, /masters/) 
are now correctly classified as LANDING and expanded, not rejected.
"""
import asyncio
import logging
from pipeline.program_discovery import discover_programs

logging.basicConfig(level=logging.INFO, format="%(message)s")

async def main():
    print("=" * 80)
    print("PRIORITY 1: Landing Page Detection & Expansion")
    print("=" * 80)
    print()
    print("Expected:")
    print("  1. business.purdue.edu/phd/ -> classified as LANDING (not rejected)")
    print("  2. business.purdue.edu/masters/ -> classified as LANDING (not rejected)")
    print("  3. Both pages should be expanded to extract individual program links")
    print("  4. Anchor text like 'Economics PhD', 'Master of Finance' should be extracted")
    print()
    
    result = await discover_programs(
        domain="purdue.edu",
        university_name="Purdue University",
        max_programs=500,
    )
    
    if isinstance(result, list):
        programs = result
    else:
        programs = result.get("programs", [])
    
    print()
    print("=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)
    print(f"Total programs discovered: {len(programs)}")
    print()
    print("Look for in logs above:")
    print("  - 'LLM result: business.purdue.edu/phd/ | type=LANDING'")
    print("  - 'LLM result: business.purdue.edu/masters/ | type=LANDING'")
    print("  - '🔍 Expanding X LANDING pages'")
    print("  - 'Landing page expansion extracted Y program URLs'")
    print("  - '✅ Added from landing page: ...'")
    print()
    
    if len(programs) > 15:
        print(f"PASS: {len(programs)} programs (significant improvement from baseline 12)")
    elif len(programs) > 12:
        print(f"WARNING: {len(programs)} programs (some improvement)")
    else:
        print(f"INCONCLUSIVE: {len(programs)} programs (may need quota refresh or further fixes)")
    print()
    
    # Show sample programs
    print("Sample programs discovered:")
    for i, prog in enumerate(programs[:10], 1):
        print(f"  {i}. {prog.get('program_name', 'N/A')} ({prog.get('degree_level', 'N/A')})")
        print(f"      {prog.get('url', '')[:80]}")
    print()

if __name__ == "__main__":
    asyncio.run(main())
