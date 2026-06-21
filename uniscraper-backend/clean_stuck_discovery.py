"""Mark stuck discovery as failed and clear cache"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def clean():
    client = AsyncIOMotorClient('mongodb+srv://patilniks69_db_user:Ryussei0120@cluster0.0gpoypz.mongodb.net/')
    db = client['uniscraper']
    
    # Mark stuck discovery as failed
    result = await db.discovery_results.update_one(
        {"discovery_id": "305fe450-004b-4652-b395-25b58ff837a3"},
        {"$set": {"status": "failed", "error": "Cancelled by auto-reload during instrumentation test"}}
    )
    print(f"Marked stuck discovery as failed: {result.modified_count} updated")
    
    # Clear all Manchester discoveries to start fresh
    result = await db.discovery_results.delete_many({"domain": "manchester.ac.uk"})
    print(f"Cleared {result.deleted_count} Manchester discovery results")
    
    client.close()

print("Cleaning stuck discovery...")
asyncio.run(clean())
print("Done! Ready for fresh run.")
