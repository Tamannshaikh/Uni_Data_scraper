"""Check Manchester discovery result directly from database"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json

async def check():
    client = AsyncIOMotorClient('mongodb+srv://patilniks69_db_user:Ryussei0120@cluster0.0gpoypz.mongodb.net/')
    db = client['uniscraper']
    
    # Find most recent Manchester discovery
    result = await db.discovery_results.find_one(
        {'domain': 'manchester.ac.uk'},
        sort=[('created_at', -1)]
    )
    
    if not result:
        print("No Manchester discovery found")
        client.close()
        return
    
    print("="*80)
    print(f"Discovery ID: {result.get('discovery_id')}")
    print(f"Status: {result.get('status')}")
    print(f"Domain: {result.get('domain')}")
    print(f"Created: {result.get('created_at')}")
    print(f"Completed: {result.get('completed_at')}")
    print(f"Elapsed: {result.get('elapsed_seconds')}s")
    print("="*80)
    
    programs = result.get('programs', [])
    print(f"\nPrograms found: {len(programs)}")
    
    levels = {}
    for p in programs:
        lvl = p.get("degree_level", "Unknown")
        levels[lvl] = levels.get(lvl, 0) + 1
    
    print("\nDegree breakdown:")
    for level, count in sorted(levels.items(), key=lambda x: -x[1]):
        print(f"  {level:15s}: {count:3d} programs")
    
    print(f"\nFirst 10 programs:")
    for i, p in enumerate(programs[:10], 1):
        print(f"{i:2d}. [{p.get('degree_level', 'Unknown'):12s}] {p.get('program_name', 'N/A')[:60]}")
    
    # Check for error
    if result.get('error'):
        print(f"\nError: {result['error']}")
    
    print("\n" + "="*80)
    print("NOTE: Backend logging would show detailed timing breakdowns")
    print("The instrumentation adds logs like:")
    print("  [program_discovery] t=X.Xs: Starting auto-confirm phase")
    print("  [program_discovery] Phase 2 - Candidate fetch: X.Xs")
    print("  [program_discovery] Stage 3 TIMING BREAKDOWN")
    print("\nTo see these, the backend server needs to be running and logging to console/file")
    print("="*80)
    
    client.close()

asyncio.run(check())
