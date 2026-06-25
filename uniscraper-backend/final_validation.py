"""
Final validation: spot-check specific programs from each university.

This confirms:
1. Known real programs are extracted
2. No junk is present
3. URLs are correct
"""
import asyncio
from pipeline.fetcher import fetch_page
from pipeline.extractors import extract_programs
from UNIVERSITY_CONFIG import UNIVERSITY_CONFIG


KNOWN_PROGRAMS = {
    "uark.edu": [
        "Master of Accountancy",
        "M.B.A./J.D.",
    ],
    "ucsd.edu": [
        "Computer Science MS, PhD",
        "Biology MS,† PhD",
        "Business Administration MBA",
    ],
    "mit.edu": [
        "Computational Science and Engineering PhD*",
        "MIT Sloan MBA Program",
        "Economics",
        "Physics",
    ],
    "purdue.edu": [
        "Computer Science",
        "Aeronautics and Astronautics",
        "Biomedical Engineering",
    ],
}

JUNK_PATTERNS = [
    "master's: july",
    "phd: october",
    "follow us",
    "explore",
    "more info",
    "admission requirements",
    "deadline",
    "apply now",
]


async def validate_university(domain: str):
    """Validate extraction for one university."""
    config = UNIVERSITY_CONFIG[domain]
    
    print(f"\n{'='*80}")
    print(f"Validating: {domain}")
    print(f"{'='*80}")
    
    # Fetch
    result = await fetch_page(config['url'])
    if not result.get('html'):
        print(f"❌ FETCH FAILED")
        return False
    
    # Extract
    programs = extract_programs(
        strategy=config['strategy'],
        base_url=config['url'],
        html=result['html']
    )
    
    extracted_names = [p['degree_name'] for p in programs]
    extracted_lower = [name.lower() for name in extracted_names]
    
    # Check 1: Known programs present
    known = KNOWN_PROGRAMS[domain]
    missing = []
    for expected in known:
        if expected.lower() not in extracted_lower:
            missing.append(expected)
    
    if missing:
        print(f"❌ MISSING KNOWN PROGRAMS: {missing}")
        return False
    else:
        print(f"✅ All {len(known)} known programs found")
    
    # Check 2: No junk
    junk_found = []
    for name in extracted_names:
        name_lower = name.lower()
        for pattern in JUNK_PATTERNS:
            if pattern in name_lower:
                junk_found.append(f"'{name}' contains '{pattern}'")
    
    if junk_found:
        print(f"❌ JUNK DETECTED:")
        for item in junk_found:
            print(f"   - {item}")
        return False
    else:
        print(f"✅ No junk patterns detected in {len(extracted_names)} programs")
    
    # Check 3: URL quality
    bad_urls = []
    for prog in programs:
        url = prog['url']
        if not url.startswith('http'):
            bad_urls.append(f"{prog['degree_name']}: {url}")
    
    if bad_urls:
        print(f"❌ BAD URLS:")
        for item in bad_urls:
            print(f"   - {item}")
        return False
    else:
        print(f"✅ All URLs are valid HTTP(S)")
    
    print(f"\n✅ {domain} PASSED ALL CHECKS")
    return True


async def main():
    """Validate all 4 universities."""
    results = {}
    
    for domain in ["uark.edu", "ucsd.edu", "mit.edu", "purdue.edu"]:
        results[domain] = await validate_university(domain)
    
    print(f"\n{'='*80}")
    print("FINAL VALIDATION SUMMARY")
    print(f"{'='*80}")
    
    all_passed = all(results.values())
    
    for domain, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {domain}")
    
    print(f"\n{'='*80}")
    if all_passed:
        print("🎉 ALL 4 UNIVERSITIES PASSED VALIDATION")
        print("Ready to add more universities to the config.")
    else:
        print("❌ VALIDATION FAILED")
        print("Fix failing universities before adding more.")
    print(f"{'='*80}")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
