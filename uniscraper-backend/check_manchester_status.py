"""Check Manchester discovery status in DB."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

async def main():
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.db_name]
    
    result = await db.discovery_results.find_one(
        {'normalized_name': 'universityofmanchester'},
        sort=[('created_at', -1)]
    )
    
    if result:
        print(f"Status: {result.get('status')}")
        print(f"Discovery ID: {result.get('_id')}")
        print(f"Programs: {len(result.get('programs', []))}")
        print(f"Error: {result.get('error')}")
        print(f"Created: {result.get('created_at')}")
    else:
        print("No Manchester discovery found")
    
    client.close()

asyncio.run(main())
