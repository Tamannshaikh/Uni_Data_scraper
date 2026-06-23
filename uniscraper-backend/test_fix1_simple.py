"""
Simple test to verify FIX 1: Heuristic fallback rejection
"""
import asyncio
import logging
from pipeline.program_discovery import discover_programs

logging.basicConfig(level=logging.INFO, format="%(message)s")

async def main():
    print("=" * 80)
    print("FIX 1 VERIFICATION: Heuristic Fallback Rejection")
    print("=" * 80)
    print()
    
    result = await discover_programs(
        domain="purdue.edu",
        university_name="Purdue University",
        max_programs=500,
    )
    
    # Handle both list and dict return types
    if isinstance(result, list):
        programs = result
    else:
        programs = result.get("programs", [])
    
    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total programs: {len(programs)}")
    print()
    
    # Check for event/seminar/news pages
    bad_patterns = ['/seminar', '/lecture', '/event', '/happenings', '/news/', '/article']
    contaminated = []
    
    for prog in programs:
        url_lower = prog['url'].lower()
        name_lower = prog['program_name'].lower()
        if any(pat in url_lower or pat in name_lower for pat in bad_patterns):
            contaminated.append(prog)
    
    if contaminated:
        print(f"FAIL: Found {len(contaminated)} event/seminar/news pages:")
        for p in contaminated[:5]:
            print(f"  - {p['program_name']}")
            print(f"    {p['url'][:80]}")
    else:
        print("PASS: No event/seminar/news pages in output")
    print()
    
    # Show first 10 programs
    print("First 10 programs:")
    for i, p in enumerate(programs[:10], 1):
        print(f"{i}. {p['program_name'][:50]:50} | {p['degree_level']}")
    print()

if __name__ == "__main__":
    asyncio.run(main())
