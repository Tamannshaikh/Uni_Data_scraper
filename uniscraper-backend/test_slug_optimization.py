"""Quick test to trigger Manchester discovery with slug optimization."""
import asyncio
import httpx

async def test():
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Trigger new discovery
        resp = await client.post("http://localhost:8000/api/v1/discover", json={
            "university_name": "Manchester Slug Test",
            "domain": "manchester.ac.uk"
        })
        data = resp.json()
        discovery_id = data.get("discovery_id")
        print(f"Started: {discovery_id}")
        print(f"Status: {data.get('status')}")
        print("\nCheck backend logs for:")
        print("  - slug_confirmed count")
        print("  - URLs going to Gemini")
        print("  - Total auto-confirm time")

asyncio.run(test())
