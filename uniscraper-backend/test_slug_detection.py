"""Test slug detection logic directly."""
from pipeline.program_discovery import _has_obvious_degree_slug

test_urls = [
    "https://www.manchester.ac.uk/study/masters/courses/list/08025/msc-aerospace-engineering/",
    "https://www.manchester.ac.uk/study/masters/courses/list/01388/msc-management-and-information-systems-change-and-development/",
    "https://www.manchester.ac.uk/study/postgraduate-research/programmes/list/03014/phd-german-studies/",
    "https://www.manchester.ac.uk/study/masters/courses/list/11521/pgce-secondary-english/",
    "https://www.manchester.ac.uk/study/masters/courses/list/18940/msc-advanced-clinical-optometric-practice/",
    "https://www.manchester.ac.uk/study/masters/fees-and-funding/",  # Should NOT match
    "https://www.manchester.ac.uk/study/masters/",  # Should NOT match
    "https://www.alliancembs.manchester.ac.uk/study/masters/",  # Should NOT match
]

print("=" * 80)
print("SLUG DETECTION TEST")
print("=" * 80)

matched_count = 0
for url in test_urls:
    has_slug, degree_level = _has_obvious_degree_slug(url)
    status = "✓ MATCH" if has_slug else "✗ NO MATCH"
    print(f"\n{status}: {url}")
    if has_slug:
        print(f"  → Degree level: {degree_level}")
        matched_count += 1

print(f"\n{'=' * 80}")
print(f"RESULTS: {matched_count}/{len(test_urls)} URLs matched")
print(f"Expected: 5/{len(test_urls)} URLs to match")
print("=" * 80)
