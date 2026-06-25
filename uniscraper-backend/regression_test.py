"""
Regression test suite with automatic failure detection.

Runs all configured universities and checks:
1. Minimum program count (catches extraction breakage)
2. Forbidden phrases (catches junk leakage)
3. URL validity (catches malformed links)

Exit code 0 = all pass, 1 = any failure.
"""
import asyncio
import sys
import logging
from pipeline.fetcher import fetch_page
from pipeline.extractors import extract_programs
from UNIVERSITY_CONFIG import UNIVERSITY_CONFIG

logging.basicConfig(level=logging.WARNING)  # Quiet unless errors


# ============================================================================
# Supported strategies (only these should report PASS/FAIL)
# ============================================================================
SUPPORTED_STRATEGIES = {
    "anchor",
    "table",
    "heading",
    "plain_text_list",
    "heading_with_button",
}


# ============================================================================
# Expected minimums (set conservatively to catch breakage)
# ============================================================================
EXPECTED_MIN_PROGRAMS = {
    "uark.edu": 5,      # Currently 10
    "ucsd.edu": 150,    # Currently 186
    "mit.edu": 40,      # Currently 46
    "purdue.edu": 150,  # Currently 190
}


# ============================================================================
# Known programs (must appear in extracted list to pass)
# ============================================================================
KNOWN_PROGRAMS = {
    "uark.edu": [
        "Master of Accountancy",
    ],
    "ucsd.edu": [
        "Bioengineering",
        "Computer Science",
    ],
    "mit.edu": [
        "Architecture",
        "Economics",
        "MIT Sloan MBA Program",
    ],
    "purdue.edu": [
        "Mechanical Engineering",
        "Business Analytics",
        "Computer Science",
    ],
}


# ============================================================================
# Forbidden phrases (should NEVER appear in extracted program names)
# ============================================================================
FORBIDDEN_PHRASES = [
    # Navigation/UI (exact phrases to avoid false positives)
    "follow us",
    "contact us",
    "more info",
    "learn more",
    "view details",
    "read more",
    "exploreplus_icon",  # Specific to Purdue junk
    "informationplus_icon",  # Specific to UI elements
    "campus map",
    "need help",
    
    # Deadlines (specific date patterns)
    "master's: july",
    "phd: october",
    "deadline:",
    "application deadline",
    
    # Admin/support phrases
    "financial aid",
    "apply now",
    "admission requirements",  # When standalone
    
    # Common junk patterns
    "plus_icon",
    "click here",
    "download pdf",
]


# ============================================================================
# Test runner
# ============================================================================

async def test_university(domain: str, config: dict) -> dict:
    """
    Test one university and return results.
    
    Returns:
        {
            "domain": str,
            "status": "PASS" | "FAIL" | "SKIPPED",
            "programs_count": int,
            "errors": list[str],
            "programs": list[dict]
        }
    """
    errors = []
    
    # Check if strategy is supported
    if config['strategy'] not in SUPPORTED_STRATEGIES:
        return {
            "domain": domain,
            "status": "SKIPPED",
            "programs_count": 0,
            "errors": [f"Strategy '{config['strategy']}' not implemented yet"],
            "programs": []
        }
    
    # Fetch
    result = await fetch_page(config['url'])
    if not result.get('html'):
        return {
            "domain": domain,
            "status": "FAIL",
            "programs_count": 0,
            "errors": [f"FETCH FAILED: {result.get('error', 'Unknown error')}"],
            "programs": []
        }
    
    # Extract
    programs = extract_programs(
        strategy=config['strategy'],
        base_url=config['url'],
        html=result['html']
    )
    
    extracted_names = [p['degree_name'] for p in programs]
    
    # Check 1: Minimum program count
    min_expected = EXPECTED_MIN_PROGRAMS.get(domain, 0)
    if len(programs) < min_expected:
        errors.append(
            f"Program count {len(programs)} below minimum {min_expected}"
        )
    
    # Check 2: Known programs must be present
    if domain in KNOWN_PROGRAMS:
        for expected_name in KNOWN_PROGRAMS[domain]:
            found = any(
                expected_name.lower() in name.lower()
                for name in extracted_names
            )
            if not found:
                errors.append(
                    f"Known program '{expected_name}' not found in extracted list"
                )
    
    # Check 3: Forbidden phrases
    for prog in programs:
        name_lower = prog['degree_name'].lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in name_lower:
                errors.append(
                    f"Forbidden phrase '{phrase}' in: {prog['degree_name'][:80]}"
                )
    
    # Check 4: URL validity
    for prog in programs:
        url = prog['url']
        if not url.startswith('http'):
            errors.append(
                f"Invalid URL for {prog['degree_name'][:50]}: {url[:100]}"
            )
    
    status = "PASS" if len(errors) == 0 else "FAIL"
    
    return {
        "domain": domain,
        "status": status,
        "programs_count": len(programs),
        "errors": errors,
        "programs": programs
    }


async def main():
    """Run regression tests on all configured universities."""
    print("="*80)
    print("REGRESSION TEST SUITE")
    print("="*80)
    
    all_results = []
    
    for domain, config in UNIVERSITY_CONFIG.items():
        print(f"\nTesting: {domain} ({config['strategy']})")
        
        try:
            result = await test_university(domain, config)
            all_results.append(result)
            
            if result['status'] == "PASS":
                print(f"  ✅ PASS — {result['programs_count']} programs")
            elif result['status'] == "SKIPPED":
                print(f"  ⏭️  SKIPPED — {result['errors'][0] if result['errors'] else 'strategy not implemented'}")
            else:  # FAIL
                print(f"  ❌ FAIL — {len(result['errors'])} errors")
                for error in result['errors'][:3]:  # Show first 3
                    print(f"     - {error}")
                if len(result['errors']) > 3:
                    print(f"     ... and {len(result['errors']) - 3} more errors")
        
        except Exception as e:
            print(f"  ❌ EXCEPTION: {e}")
            all_results.append({
                "domain": domain,
                "status": "FAIL",
                "programs_count": 0,
                "errors": [f"Exception: {str(e)}"],
                "programs": []
            })
    
    # Summary
    print("\n" + "="*80)
    print("REGRESSION TEST SUMMARY")
    print("="*80)
    
    passed_count = sum(1 for r in all_results if r['status'] == "PASS")
    skipped_count = sum(1 for r in all_results if r['status'] == "SKIPPED")
    failed_count = sum(1 for r in all_results if r['status'] == "FAIL")
    total_count = len(all_results)
    
    for result in all_results:
        if result['status'] == "PASS":
            status_icon = "✅"
        elif result['status'] == "SKIPPED":
            status_icon = "⏭️ "
        else:
            status_icon = "❌"
        
        print(f"{status_icon} {result['domain']:20s} — {result['programs_count']:3d} programs — {result['status']}")
    
    print("\n" + "="*80)
    if failed_count == 0:
        if skipped_count > 0:
            print(f"✅ {passed_count} PASSED, {skipped_count} SKIPPED (strategies not implemented)")
        else:
            print(f"✅ ALL {total_count} UNIVERSITIES PASSED")
        print("="*80)
        return 0
    else:
        print(f"❌ {failed_count} FAILED, {passed_count} PASSED, {skipped_count} SKIPPED")
        print("="*80)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
