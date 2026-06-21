"""
Comprehensive verification test for program discovery improvements:
1. Stage 1 cap raised to 300
2. Inter-batch delay reduced to 0.5s
3. Post-classification filtering for Master's/PhD

Tests both Manchester and Arkansas State University.
"""
import asyncio
import httpx
import time
import json
import motor.motor_asyncio
from config import settings

MONGODB_URI = settings.mongodb_uri
DATABASE_NAME = settings.db_name

async def clear_discovery_cache(university_name: str):
    """Clear discovery cache for a specific university."""
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    col = db["discovery_results"]
    
    result = await col.delete_many({
        "normalized_name": university_name.lower().replace(" ", "")
    })
    client.close()
    return result.deleted_count

async def test_manchester():
    """Test Manchester with new settings."""
    print("\n" + "="*80)
    print("TESTING: UNIVERSITY OF MANCHESTER")
    print("="*80)
    print("\nExpectations:")
    print("  - Stage 1: ~250-300 candidates collected")
    print("  - Stage 3: ~20 Gemini batches (300/15)")
    print("  - Final: 30-60+ confirmed Master's/PhD programs")
    print("  - Time: <3 minutes total")
    print("  - Filtering: Only Master's, PhD, Doctoral, MBA programs")
    
    # Clear cache
    print("\n1. Clearing Manchester cache...")
    deleted = await clear_discovery_cache("University of Manchester")
    print(f"   Deleted {deleted} cached result(s)")
    
    # Start discovery
    print("\n2. Starting discovery...")
    async with httpx.AsyncClient(timeout=300.0) as client:
        start = time.time()
        
        resp = await client.post("http://localhost:8000/api/v1/discover", json={
            "university_name": "University of Manchester",
            "domain": "manchester.ac.uk"
        })
        data = resp.json()
        discovery_id = data.get("discovery_id")
        status = data.get("status")
        print(f"   Discovery ID: {discovery_id}")
        print(f"   Status: {status}")
        
        if not discovery_id:
            print("   ERROR: no discovery_id returned")
            print(data)
            return None
        
        # Poll until complete
        print("\n3. Polling for completion...")
        poll_count = 0
        while True:
            await asyncio.sleep(3)
            poll_count += 1
            poll = await client.get(f"http://localhost:8000/api/v1/discover/{discovery_id}")
            result = poll.json()
            current_status = result.get("status")
            elapsed = time.time() - start
            print(f"   Poll #{poll_count} [{elapsed:.0f}s]: status={current_status}")
            
            if current_status in ("success", "failed", "no_programs_found", "error"):
                break
            if elapsed > 300:
                print("   Timeout after 5 minutes")
                break
        
        elapsed = time.time() - start
        programs = result.get("programs", [])
        
        # Results
        print("\n" + "="*80)
        print("MANCHESTER RESULTS")
        print("="*80)
        print(f"\nTime:           {elapsed:.1f}s  (target: <180s)")
        print(f"Status:         {result.get('status')}")
        print(f"Programs found: {len(programs)}  (expected: 30-60+)")
        
        # Degree breakdown
        from collections import Counter
        levels = Counter(p.get("degree_level", "Unknown") for p in programs)
        print(f"\nDegree breakdown:")
        for level, count in sorted(levels.items(), key=lambda x: -x[1]):
            print(f"  {level:15s}: {count}")
        
        # Check for contamination (should be ZERO Bachelor's/etc. due to filtering)
        unwanted = sum(count for level, count in levels.items() 
                      if level not in ["Master's", "PhD", "Doctoral", "MBA"])
        if unwanted > 0:
            print(f"\n⚠️  WARNING: {unwanted} programs with unwanted degree levels!")
        else:
            print(f"\n✓ All programs are Master's/PhD/Doctoral/MBA (filtering works!)")
        
        # Random spot-check
        print(f"\nRandom 5 programs:")
        import random
        sample = random.sample(programs, min(5, len(programs)))
        for p in sample:
            print(f"  [{p['degree_level']:12s}] {p['program_name'][:60]}")
            print(f"                   {p['url']}")
        
        if result.get("error"):
            print(f"\n❌ Error: {result['error']}")
        
        return result

async def test_arkansas():
    """Test Arkansas State as regression check."""
    print("\n" + "="*80)
    print("TESTING: ARKANSAS STATE UNIVERSITY (Regression Check)")
    print("="*80)
    print("\nExpectations:")
    print("  - Programs: ~97 (baseline from previous runs)")
    print("  - No filtering (no FILTER_DEGREE_LEVELS set for Arkansas)")
    print("  - No degradation from Manchester changes")
    
    # Clear cache
    print("\n1. Clearing Arkansas cache...")
    deleted = await clear_discovery_cache("Arkansas State University")
    print(f"   Deleted {deleted} cached result(s)")
    
    # Start discovery
    print("\n2. Starting discovery...")
    async with httpx.AsyncClient(timeout=300.0) as client:
        start = time.time()
        
        resp = await client.post("http://localhost:8000/api/v1/discover", json={
            "university_name": "Arkansas State University",
            "domain": "astate.edu"
        })
        data = resp.json()
        discovery_id = data.get("discovery_id")
        status = data.get("status")
        print(f"   Discovery ID: {discovery_id}")
        print(f"   Status: {status}")
        
        if not discovery_id:
            print("   ERROR: no discovery_id returned")
            print(data)
            return None
        
        # Poll until complete
        print("\n3. Polling for completion...")
        poll_count = 0
        while True:
            await asyncio.sleep(3)
            poll_count += 1
            poll = await client.get(f"http://localhost:8000/api/v1/discover/{discovery_id}")
            result = poll.json()
            current_status = result.get("status")
            elapsed = time.time() - start
            print(f"   Poll #{poll_count} [{elapsed:.0f}s]: status={current_status}")
            
            if current_status in ("success", "failed", "no_programs_found", "error"):
                break
            if elapsed > 300:
                print("   Timeout after 5 minutes")
                break
        
        elapsed = time.time() - start
        programs = result.get("programs", [])
        
        # Results
        print("\n" + "="*80)
        print("ARKANSAS STATE RESULTS")
        print("="*80)
        print(f"\nTime:           {elapsed:.1f}s")
        print(f"Status:         {result.get('status')}")
        print(f"Programs found: {len(programs)}  (baseline: ~97)")
        
        # Degree breakdown
        from collections import Counter
        levels = Counter(p.get("degree_level", "Unknown") for p in programs)
        print(f"\nDegree breakdown:")
        for level, count in sorted(levels.items(), key=lambda x: -x[1]):
            print(f"  {level:15s}: {count}")
        
        # Check for regression
        if len(programs) < 85:
            print(f"\n⚠️  WARNING: Significantly fewer programs than baseline (97)")
        elif len(programs) > 85:
            print(f"\n✓ Program count matches baseline (no regression)")
        
        # First 10 programs
        print(f"\nFirst 10 programs:")
        for p in programs[:10]:
            print(f"  [{p['degree_level']:12s}] {p['program_name'][:60]}")
        
        if result.get("error"):
            print(f"\n❌ Error: {result['error']}")
        
        return result

async def main():
    print("\n" + "="*80)
    print("DISCOVERY VERIFICATION TEST SUITE")
    print("="*80)
    print("\nChanges being verified:")
    print("  1. Stage 1 candidate cap: 150 → 300")
    print("  2. Inter-batch delay: 2s → 0.5s")
    print("  3. Post-classification filtering for Master's/PhD")
    print("\nNOTE: Make sure backend is running on localhost:8000")
    print("="*80)
    
    print("\nStarting tests in 2 seconds...")
    await asyncio.sleep(2)
    
    # Test Manchester
    manchester_result = await test_manchester()
    
    # Wait a bit between tests
    print("\n\n⏳ Waiting 5 seconds before Arkansas test...")
    await asyncio.sleep(5)
    
    # Test Arkansas
    arkansas_result = await test_arkansas()
    
    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    if manchester_result:
        m_programs = len(manchester_result.get("programs", []))
        m_time = manchester_result.get("elapsed_seconds", 0)
        print(f"\n✓ Manchester: {m_programs} programs in {m_time:.1f}s")
        
        from collections import Counter
        m_levels = Counter(p.get("degree_level") for p in manchester_result.get("programs", []))
        unwanted = sum(count for level, count in m_levels.items() 
                      if level not in ["Master's", "PhD", "Doctoral", "MBA"])
        if unwanted == 0:
            print(f"  ✓ Filtering: All programs are Master's/PhD/Doctoral/MBA")
        else:
            print(f"  ⚠️  Filtering: {unwanted} unwanted degree levels found")
    else:
        print(f"\n❌ Manchester: Test failed")
    
    if arkansas_result:
        a_programs = len(arkansas_result.get("programs", []))
        a_time = arkansas_result.get("elapsed_seconds", 0)
        print(f"\n✓ Arkansas: {a_programs} programs in {a_time:.1f}s")
        if a_programs >= 85:
            print(f"  ✓ Regression: Program count matches baseline (~97)")
        else:
            print(f"  ⚠️  Regression: Fewer programs than baseline (expected ~97)")
    else:
        print(f"\n❌ Arkansas: Test failed")
    
    print("\n" + "="*80)
    print("Next steps:")
    print("  1. Review backend logs for Stage 1/3 confirmation")
    print("  2. Spot-check random programs for quality")
    print("  3. If all looks good, commit changes")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
