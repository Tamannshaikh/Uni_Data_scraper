"""
Test suite for structurally diverse universities.

Tests universities with different characteristics to validate generalization:
- Purdue: Large state university
- Arizona State: Massive online presence
- Northeastern: Urban private university
- Waterloo (Canada): Different domain structure
- Illinois Urbana-Champaign: Distributed departments
- UC Davis: California system structure
- Texas A&M: Complex multi-campus system
"""
import asyncio
import logging
import time
from collections import Counter
from pipeline.program_discovery import discover_programs

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

UNIVERSITIES = [
    {
        "name": "Purdue University",
        "domain": "purdue.edu",
        "expected_min": 150,  # Large state university
        "notes": "Complex departmental structure"
    },
    {
        "name": "Arizona State University",
        "domain": "asu.edu",
        "expected_min": 200,  # Massive online presence
        "notes": "Huge online graduate program catalog"
    },
    {
        "name": "Northeastern University",
        "domain": "northeastern.edu",
        "expected_min": 100,
        "notes": "Urban private university with co-op focus"
    },
    {
        "name": "University of Waterloo",
        "domain": "uwaterloo.ca",
        "expected_min": 80,
        "notes": "Canadian university, different TLD"
    },
    {
        "name": "University of Illinois Urbana-Champaign",
        "domain": "illinois.edu",
        "expected_min": 150,
        "notes": "Distributed across departments"
    },
    {
        "name": "UC Davis",
        "domain": "ucdavis.edu",
        "expected_min": 120,
        "notes": "UC system structure"
    },
    {
        "name": "Texas A&M University",
        "domain": "tamu.edu",
        "expected_min": 150,
        "notes": "Multi-campus system"
    },
]


async def test_university(config: dict) -> dict:
    """Test a single university and return results."""
    print("\n" + "="*80)
    print(f"Testing: {config['name']}")
    print("="*80)
    print(f"Domain: {config['domain']}")
    print(f"Expected minimum: {config['expected_min']} programs")
    print(f"Notes: {config['notes']}")
    print("-"*80)
    
    start_time = time.time()
    
    try:
        programs = await discover_programs(
            domain=config['domain'],
            university_name=config['name'],
            max_programs=500,
            skip_gemini_threshold=15,
        )
        
        elapsed = time.time() - start_time
        
        # Analyze results
        degree_levels = Counter(p.get('degree_level', 'Unknown') for p in programs)
        
        # Check for contamination
        undergrad_count = sum(
            count for level, count in degree_levels.items()
            if any(word in level.lower() for word in ["bachelor", "undergraduate", "bs", "ba", "bsc"])
        )
        
        cert_count = degree_levels.get("Certificate", 0) + degree_levels.get("Certification", 0)
        
        graduate_count = sum(
            count for level, count in degree_levels.items()
            if any(word in level.lower() for word in ["master", "phd", "doctorate", "mba", "ms", "ma"])
        )
        
        # Determine status
        if len(programs) >= config['expected_min']:
            if undergrad_count == 0 and cert_count < len(programs) * 0.1:  # < 10% certs
                status = "✅ PASS"
            else:
                status = "⚠️ PASS (contamination)"
        elif len(programs) >= config['expected_min'] * 0.7:  # 70% of expected
            status = "⚠️ PARTIAL"
        else:
            status = "❌ FAIL"
        
        result = {
            "university": config['name'],
            "domain": config['domain'],
            "status": status,
            "total_programs": len(programs),
            "expected_min": config['expected_min'],
            "runtime_seconds": elapsed,
            "degree_breakdown": dict(degree_levels.most_common(10)),
            "graduate_count": graduate_count,
            "undergrad_count": undergrad_count,
            "cert_count": cert_count,
            "notes": config['notes'],
        }
        
        # Print results
        print(f"\n{status}")
        print(f"\nResults:")
        print(f"  Total programs: {len(programs)}")
        print(f"  Runtime: {elapsed:.1f}s")
        print(f"  Graduate programs: {graduate_count}")
        print(f"  Undergraduate (contamination): {undergrad_count}")
        print(f"  Certificates: {cert_count}")
        
        print(f"\nDegree level breakdown:")
        for level, count in degree_levels.most_common(10):
            percentage = (count / len(programs) * 100) if len(programs) > 0 else 0
            print(f"  {level}: {count} ({percentage:.1f}%)")
        
        if programs:
            print(f"\nSample programs (first 5):")
            for i, prog in enumerate(programs[:5], 1):
                print(f"  {i}. {prog.get('program_name', 'N/A')} ({prog.get('degree_level', 'N/A')})")
                print(f"     {prog.get('url', 'N/A')}")
        
        return result
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "university": config['name'],
            "domain": config['domain'],
            "status": "❌ ERROR",
            "total_programs": 0,
            "expected_min": config['expected_min'],
            "runtime_seconds": elapsed,
            "error": str(e),
            "notes": config['notes'],
        }


async def run_all_tests():
    """Run tests for all universities."""
    print("\n" + "="*80)
    print("DIVERSE UNIVERSITY VALIDATION TEST SUITE")
    print("="*80)
    print(f"\nTesting {len(UNIVERSITIES)} structurally different universities")
    print("Goal: Validate pipeline generalization beyond Manchester/Arkansas")
    print("\nCriteria for success:")
    print("  ✅ PASS: ≥ expected minimum programs, 0 undergrad, < 10% certificates")
    print("  ⚠️ PARTIAL: ≥ 70% of expected, but some contamination")
    print("  ❌ FAIL: < 70% of expected programs")
    print("="*80)
    
    overall_start = time.time()
    results = []
    
    for i, university in enumerate(UNIVERSITIES, 1):
        print(f"\n\n[{i}/{len(UNIVERSITIES)}] Starting test for {university['name']}...")
        result = await test_university(university)
        results.append(result)
        
        # Brief pause between universities to avoid rate limiting
        if i < len(UNIVERSITIES):
            print("\nWaiting 5 seconds before next test...")
            await asyncio.sleep(5)
    
    overall_elapsed = time.time() - overall_start
    
    # Summary report
    print("\n\n" + "="*80)
    print("SUMMARY REPORT")
    print("="*80)
    
    pass_count = sum(1 for r in results if r['status'].startswith("✅"))
    partial_count = sum(1 for r in results if r['status'].startswith("⚠️"))
    fail_count = sum(1 for r in results if r['status'].startswith("❌"))
    
    print(f"\nOverall Results:")
    print(f"  ✅ PASS: {pass_count}/{len(UNIVERSITIES)}")
    print(f"  ⚠️ PARTIAL: {partial_count}/{len(UNIVERSITIES)}")
    print(f"  ❌ FAIL: {fail_count}/{len(UNIVERSITIES)}")
    print(f"\nTotal runtime: {overall_elapsed:.1f}s ({overall_elapsed / 60:.1f} minutes)")
    
    print(f"\nDetailed Results:")
    print(f"{'University':<40} {'Status':<20} {'Programs':<12} {'Runtime':<10}")
    print("-"*80)
    
    for result in results:
        univ_name = result['university'][:38]
        status = result['status']
        programs = f"{result['total_programs']}/{result['expected_min']}"
        runtime = f"{result['runtime_seconds']:.1f}s"
        print(f"{univ_name:<40} {status:<20} {programs:<12} {runtime:<10}")
    
    # Quality analysis
    print(f"\nQuality Metrics:")
    total_programs = sum(r.get('total_programs', 0) for r in results if 'total_programs' in r)
    total_undergrad = sum(r.get('undergrad_count', 0) for r in results if 'undergrad_count' in r)
    total_certs = sum(r.get('cert_count', 0) for r in results if 'cert_count' in r)
    
    if total_programs > 0:
        undergrad_pct = (total_undergrad / total_programs * 100)
        cert_pct = (total_certs / total_programs * 100)
        print(f"  Total programs discovered: {total_programs}")
        print(f"  Undergraduate contamination: {total_undergrad} ({undergrad_pct:.1f}%)")
        print(f"  Certificate programs: {total_certs} ({cert_pct:.1f}%)")
        
        if undergrad_pct == 0:
            print(f"  ✅ Perfect graduate-only filtering!")
        elif undergrad_pct < 2:
            print(f"  ✅ Excellent filtering (< 2% contamination)")
        elif undergrad_pct < 5:
            print(f"  ⚠️ Good filtering (< 5% contamination)")
        else:
            print(f"  ❌ Poor filtering (> 5% contamination)")
    
    # Performance analysis
    avg_runtime = sum(r.get('runtime_seconds', 0) for r in results) / len(results)
    print(f"\nPerformance Metrics:")
    print(f"  Average runtime: {avg_runtime:.1f}s")
    print(f"  Fastest: {min(r.get('runtime_seconds', 9999) for r in results):.1f}s")
    print(f"  Slowest: {max(r.get('runtime_seconds', 0) for r in results):.1f}s")
    
    # Final verdict
    print("\n" + "="*80)
    print("FINAL VERDICT")
    print("="*80)
    
    success_rate = (pass_count / len(UNIVERSITIES) * 100)
    
    if success_rate >= 80 and total_undergrad == 0:
        print("✅ PRODUCTION READY")
        print("   Pipeline generalizes well across diverse university structures")
        print("   Graduate-only filtering is working correctly")
    elif success_rate >= 60:
        print("⚠️ NEEDS IMPROVEMENT")
        print("   Pipeline shows promise but needs refinement for some structures")
    else:
        print("❌ NOT READY")
        print("   Significant issues with generalization across universities")
    
    print("="*80)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
