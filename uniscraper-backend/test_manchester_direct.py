"""Direct Manchester test bypassing cache."""
import asyncio
from pipeline.program_discovery import discover_programs

async def test():
    print("=" * 80)
    print("DIRECT MANCHESTER DISCOVERY - Slug Optimization Test")
    print("=" * 80)
    
    programs = await discover_programs(
        domain="manchester.ac.uk",
        university_name="University of Manchester",
        max_pages=30
    )
    
    print(f"\nFound {len(programs)} programs")
    print("\nFirst 10 programs:")
    for i, prog in enumerate(programs[:10], 1):
        print(f"{i}. [{prog['degree_level']}] {prog['program_name']}")
        print(f"   {prog['url']}")

asyncio.run(test())
