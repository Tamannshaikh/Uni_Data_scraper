"""
Test FIX 2: Verify scoring penalties prevent junk from ranking in top 10
"""
import asyncio
import logging
from pipeline.program_discovery import discover_programs

# Set logging to capture the "Top 10 URLs by confidence" output
logging.basicConfig(level=logging.INFO, format="%(message)s")

async def main():
    print("=" * 80)
    print("FIX 2 VERIFICATION: Scoring Penalties")
    print("=" * 80)
    print()
    print("Checking if junk pages (FAQ, cohort, graduates) are filtered from top 10...")
    print()
    
    result = await discover_programs(
        domain="purdue.edu",
        university_name="Purdue University",
        max_programs=500,
    )
    
    # The logs will show "Top 10 URLs by confidence" during execution
    # We just need to see the final results
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
    print("Look for 'Top 10 URLs by confidence' in the logs above.")
    print("PASS criteria: No /faq, /cohort/, or /graduates/ in top 10")
    print()

if __name__ == "__main__":
    asyncio.run(main())
