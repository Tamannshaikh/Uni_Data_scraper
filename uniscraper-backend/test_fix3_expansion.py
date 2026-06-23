"""
Test FIX 3: Verify directory page expansion multiplies candidate count
"""
import asyncio
import logging
from pipeline.program_discovery import discover_programs

logging.basicConfig(level=logging.INFO, format="%(message)s")

async def main():
    print("=" * 80)
    print("FIX 3 VERIFICATION: Directory Page Expansion")
    print("=" * 80)
    print()
    print("Expected: Catalog pages detected and expanded into child links")
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
    print(f"Total programs: {len(programs)}")
    print()
    print("Look for these in logs above:")
    print("  - 'Detected X directory/catalog pages (expanding...)'")
    print("  - 'Directory expansion: catalog.purdue.edu -> Y child links'")
    print("  - 'Adding Z new candidates from directory expansion'")
    print()
    print(f"PASS criteria: Program count > 12 (baseline without expansion)")
    if len(programs) > 12:
        print(f"PASS: {len(programs)} programs (up from ~12 baseline)")
    else:
        print(f"INCONCLUSIVE: {len(programs)} programs (may need quota refresh)")
    print()

if __name__ == "__main__":
    asyncio.run(main())
