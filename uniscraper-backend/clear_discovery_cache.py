"""Clear discovery cache from MongoDB."""
import asyncio
from database import get_db

async def clear_cache():
    db = get_db()
    result = await db.discovery_results.delete_many({})
    print(f"Cleared {result.deleted_count} cached discovery results")

asyncio.run(clear_cache())
