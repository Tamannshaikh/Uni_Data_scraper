"""Clear Manchester discovery cache to allow fresh test run"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def clear():
    client = AsyncIOMotorClient('mongodb+srv://patilniks69_db_user:Ryussei0120@cluster0.0gpoypz.mongodb.net/')
    db = client['uniscraper']
    
    # Clear discovery results
    result = await db.discovery_results.delete_many({
        'domain': 'manchester.ac.uk'
    })
    print(f'Deleted {result.deleted_count} Manchester discovery results')
    
    client.close()

print("Clearing Manchester discovery cache...")
asyncio.run(clear())
print("Done! Now run: .\\venv\\Scripts\\python.exe test_discovery_manchester.py")
