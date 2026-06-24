"""
Test the tightened landing page extraction with scoring system
"""
import asyncio
import logging
from pipeline.program_discovery import discover_programs

logging.basicConfig(level=logging.INFO, format="%(message)s")

async def main():
    print("=" * 80)
    print("TIGHTENED EXTRACTION TEST")
    print("=" * 80)
    print()
    print("Expected improvements:")
    print("  1. No more 'home.php' or empty program names")
    print("  2. Anchor text logged for each extracted link")
    print("  3. Score-based filtering (score >= 5 required)")
    print("  4. Rejection logging for debugging")
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
    print("VERIFICATION")
    print("=" * 80)
    print(f"Total programs: {len(programs)}")
    print()
    
    # Check for bad extractions
    bad_extractions = []
    for prog in programs:
        name = prog.get("program_name", "")
        url = prog.get("url", "")
        
        # Check for home.php
        if "home.php" in url:
            bad_extractions.append(f"  BAD: home.php in URL: {url}")
        
        # Check for empty/generic names
        if not name or name in ["", " ", "N/A"]:
            bad_extractions.append(f"  BAD: Empty name for {url}")
        
        # Check for generic navigation names
        if name.lower() in ["home", "learn more", "apply", "overview"]:
            bad_extractions.append(f"  BAD: Generic name '{name}' for {url}")
    
    if bad_extractions:
        print("Found bad extractions:")
        for bad in bad_extractions[:10]:
            print(bad)
        print()
        print(f"FAIL: {len(bad_extractions)} bad extractions found")
    else:
        print("PASS: No bad extractions found!")
        print("  - No home.php URLs")
        print("  - No empty program names")
        print("  - No generic navigation text")
    
    print()
    print("Sample programs:")
    for i, prog in enumerate(programs[:10], 1):
        print(f"  {i}. {prog.get('program_name', 'N/A')} ({prog.get('degree_level', 'N/A')})")
    print()

if __name__ == "__main__":
    asyncio.run(main())
