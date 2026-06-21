"""Test Manchester discovery with new instrumentation — polls until complete."""
import asyncio
import httpx
import time
import json

async def test():
    print("="*80)
    print("MANCHESTER DISCOVERY TEST - With New Timing Instrumentation")
    print("="*80)
    print("\nThis will show detailed timing breakdowns:")
    print("  - Auto-confirmation phase timing")
    print("  - Candidate fetch phase timing")
    print("  - Gemini classification with rate limiter waits")
    print("  - Wall-clock timestamps for each phase\n")
    print("="*80 + "\n")
    
    async with httpx.AsyncClient(timeout=300.0) as client:

        # POST to start discovery
        resp = await client.post("http://localhost:8000/api/v1/discover", json={
            "university_name": "University of Manchester",
            "domain": "manchester.ac.uk"
        })
        data = resp.json()
        discovery_id = data.get("discovery_id")
        status = data.get("status")
        print(f"Started: id={discovery_id}  status={status}\n")

        if not discovery_id:
            print("ERROR: no discovery_id returned")
            print(data)
            return

        # Poll until complete
        start = time.time()
        last_status = None
        while True:
            await asyncio.sleep(5)
            poll = await client.get(f"http://localhost:8000/api/v1/discover/{discovery_id}")
            result = poll.json()
            current_status = result.get("status")
            elapsed = time.time() - start
            
            if current_status != last_status:
                print(f"  [{elapsed:.0f}s] status={current_status}")
                last_status = current_status

            if current_status in ("success", "failed", "no_programs_found", "error", "partial"):
                break
            if elapsed > 600:
                print("Timeout after 10 minutes")
                break

        elapsed = time.time() - start
        programs = result.get("programs", [])
        
        print(f"\n{'='*80}")
        print("DISCOVERY RESULTS")
        print(f"{'='*80}")
        print(f"Time:           {result.get('elapsed_seconds', elapsed):.1f}s")
        print(f"Status:         {result.get('status')}")
        print(f"Domain:         {result.get('domain')}")
        print(f"Programs found: {len(programs)}")

        levels = {}
        for p in programs:
            lvl = p.get("degree_level", "Unknown")
            levels[lvl] = levels.get(lvl, 0) + 1
        print(f"\nDegree breakdown:")
        for level, count in sorted(levels.items(), key=lambda x: -x[1]):
            print(f"  {level:15s}: {count:3d} programs")

        print(f"\n{'='*80}")
        print("SAMPLE PROGRAMS (First 20)")
        print(f"{'='*80}")
        for i, p in enumerate(programs[:20], 1):
            print(f"{i:2d}. [{p.get('degree_level', 'Unknown'):12s}] {p.get('program_name', 'N/A')}")
            print(f"    {p.get('url', 'N/A')}")
            print(f"    Confidence: {p.get('confidence', 0):.2f}")

        if result.get("error"):
            print(f"\nError: {result['error']}")
        
        print(f"\n{'='*80}")
        print("CHECK BACKEND LOGS FOR DETAILED TIMING BREAKDOWN")
        print(f"{'='*80}")
        print("\nLook for:")
        print("  [program_discovery] t=X.Xs: Starting auto-confirm phase")
        print("  [program_discovery] t=X.Xs: Starting candidate fetch phase")
        print("  [program_discovery] t=X.Xs: Starting Gemini classification phase")
        print("  [program_discovery] Stage 3 TIMING BREAKDOWN:")
        print("    Phase 1 - Auto-confirm:    X.Xs")
        print("    Phase 2 - Candidate fetch: X.Xs  ← KEY METRIC")
        print("    Phase 3 - Gemini classify: X.Xs")
        print("      └─ Gemini API time:      X.Xs")
        print("      └─ Overhead:             X.Xs")
        print("\n" + "="*80 + "\n")

asyncio.run(test())
