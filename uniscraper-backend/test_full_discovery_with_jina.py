#!/usr/bin/env python3
"""
Test the complete discovery pipeline with Jina integration.
This shows the final output that the website will display.
"""
import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from pipeline.program_discovery import discover_programs


async def test_full_discovery():
    domain = "unimelb.edu.au"
    university_name = "University of Melbourne"
    
    print(f"\n{'='*70}")
    print(f"TESTING FULL DISCOVERY PIPELINE")
    print(f"{'='*70}")
    print(f"University: {university_name}")
    print(f"Domain: {domain}")
    print(f"{'='*70}\n")
    
    print("Running discovery pipeline (Jina + extractors)...")
    print("This may take 1-2 minutes...\n")
    
    programs = await discover_programs(
        domain=domain,
        university_name=university_name,
        max_pages=30,
        max_programs=50  # Limit for testing
    )
    
    print(f"\n{'='*70}")
    print(f"FINAL RESULTS (What the website will show)")
    print(f"{'='*70}\n")
    
    print(f"University: {university_name}")
    print(f"Programs Found: {len(programs)}")
    print(f"\n{'-'*70}\n")
    
    if programs:
        print("PROGRAM LIST:\n")
        for i, prog in enumerate(programs[:20], 1):  # Show first 20
            name = prog.get("program_name", "Unknown")
            level = prog.get("degree_level", "")
            url = prog.get("url", "")
            print(f"{i:2d}. {name}")
            if level:
                print(f"    Level: {level}")
            print(f"    URL: {url}")
            print()
        
        if len(programs) > 20:
            print(f"... and {len(programs) - 20} more programs\n")
    else:
        print("No programs found\n")
    
    print(f"{'='*70}\n")
    
    # Show JSON output format
    print("JSON Output Format (for API):\n")
    sample_output = {
        "university": university_name,
        "domain": domain,
        "programs_count": len(programs),
        "programs": programs[:3]  # Show first 3 as example
    }
    print(json.dumps(sample_output, indent=2))
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(test_full_discovery())
