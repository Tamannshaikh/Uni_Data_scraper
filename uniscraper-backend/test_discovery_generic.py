"""Generic discovery test — pass university name and domain as args."""
import asyncio
import httpx
import time
import json
import sys

UNIVERSITY = sys.argv[1] if len(sys.argv) > 1 else "University of Manchester"
DOMAIN = sys.argv[2] if len(sys.argv) > 2 else "manchester.ac.uk"

async def test():
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post("http://localhost:8000/api/v1/discover", json={
            "university_name": UNIVERSITY,
            "domain": DOMAIN,
        })
        data = resp.json()
        discovery_id = data.get("discovery_id")
        status = data.get("status")
        print(f"University:  {UNIVERSITY}")
        print(f"Domain:      {DOMAIN}")
        print(f"Started:     id={discovery_id}  status={status}")

        if not discovery_id:
            print("ERROR:", data)
            return

        start = time.time()
        while True:
            await asyncio.sleep(5)
            poll = await client.get(f"http://localhost:8000/api/v1/discover/{discovery_id}")
            result = poll.json()
            current_status = result.get("status")
            elapsed = time.time() - start
            print(f"  [{elapsed:.0f}s] {current_status}")
            if current_status in ("success", "failed", "no_programs_found", "error"):
                break
            if elapsed > 300:
                print("Timeout after 5 minutes")
                break

        programs = result.get("programs", [])
        print(f"\n{'='*55}")
        print(f"Time:     {result.get('elapsed_seconds', 0):.1f}s")
        print(f"Status:   {result.get('status')}")
        print(f"Domain:   {result.get('domain')}")
        print(f"Programs: {len(programs)}")

        levels = {}
        for p in programs:
            lvl = p.get("degree_level", "?")
            levels[lvl] = levels.get(lvl, 0) + 1
        print(f"Breakdown: {json.dumps(levels, indent=2)}")

        print(f"\nSpot-check (5 random entries):")
        import random
        sample = random.sample(programs, min(5, len(programs)))
        for p in sample:
            print(f"  [{p['degree_level']:12s}] {p['program_name'][:55]}")
            print(f"                   {p['url']}")

        if result.get("error"):
            print(f"\nError: {result['error']}")

asyncio.run(test())
