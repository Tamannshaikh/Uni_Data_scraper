"""Test Arkansas State discovery — polls until complete."""
import asyncio
import httpx
import time
import json

async def test():
    async with httpx.AsyncClient(timeout=300.0) as client:

        # POST to start discovery
        resp = await client.post("http://localhost:8000/api/v1/discover", json={
            "university_name": "Arkansas State University",
            "domain": "astate.edu"
        })
        data = resp.json()
        discovery_id = data.get("discovery_id")
        status = data.get("status")
        print(f"Started: id={discovery_id}  status={status}")

        if not discovery_id:
            print("ERROR: no discovery_id returned")
            print(data)
            return

        # Poll until complete
        start = time.time()
        while True:
            await asyncio.sleep(3)
            poll = await client.get(f"http://localhost:8000/api/v1/discover/{discovery_id}")
            result = poll.json()
            current_status = result.get("status")
            elapsed = time.time() - start
            print(f"  [{elapsed:.0f}s] status={current_status}")

            if current_status in ("success", "failed", "no_programs_found", "error"):
                break
            if elapsed > 300:
                print("Timeout after 5 minutes")
                break

        elapsed = time.time() - start
        programs = result.get("programs", [])
        print(f"\n{'='*50}")
        print(f"Time:           {result.get('elapsed_seconds', elapsed):.1f}s  (was 135.3s)")
        print(f"Status:         {result.get('status')}")
        print(f"Domain:         {result.get('domain')}")
        print(f"Programs found: {len(programs)}  (was 11)")

        levels = {}
        for p in programs:
            lvl = p.get("degree_level", "Unknown")
            levels[lvl] = levels.get(lvl, 0) + 1
        print(f"Degree breakdown: {json.dumps(levels, indent=2)}")

        print(f"\nFirst 15 programs:")
        for p in programs[:15]:
            print(f"  [{p['degree_level']:12s}] {p['program_name']}")
            print(f"                   {p['url']}")

        if result.get("error"):
            print(f"\nError: {result['error']}")

asyncio.run(test())
