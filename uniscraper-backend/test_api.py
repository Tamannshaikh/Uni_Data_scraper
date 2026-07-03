#!/usr/bin/env python3
"""
Test the discovery API endpoint
"""
import httpx
import asyncio
import time


async def test_api():
    base_url = "http://localhost:8000/api/v1"
    
    print("\n" + "="*70)
    print("TESTING DISCOVERY API ENDPOINT")
    print("="*70 + "\n")
    
    # Start discovery
    print("1. Starting discovery for University of Melbourne...")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/discover",
            json={"university_name": "University of Melbourne"}
        )
        
        if response.status_code != 202:
            print(f"❌ Failed: HTTP {response.status_code}")
            print(response.text)
            return
        
        result = response.json()
        discovery_id = result["discovery_id"]
        status = result["status"]
        
        print(f"✓ Discovery started")
        print(f"  ID: {discovery_id}")
        print(f"  Status: {status}\n")
        
        if status == "cached":
            print("⚡ Using cached result\n")
        
        # Poll for results
        print("2. Polling for results (max 3 minutes)...\n")
        max_attempts = 36  # 3 minutes (5 second intervals)
        attempt = 0
        
        while attempt < max_attempts:
            await asyncio.sleep(5)
            attempt += 1
            
            response = await client.get(f"{base_url}/discover/{discovery_id}")
            
            if response.status_code != 200:
                print(f"❌ Failed to poll: HTTP {response.status_code}")
                return
            
            data = response.json()
            current_status = data["status"]
            
            print(f"[Attempt {attempt}] Status: {current_status}", end="")
            
            if current_status == "success":
                print(" ✓\n")
                break
            elif current_status in ["failed", "no_programs_found"]:
                print(f" ❌\n")
                print(f"Error: {data.get('error')}")
                print(f"Reason: {data.get('reason')}")
                return
            else:
                print()  # Still processing
        
        if current_status != "success":
            print(f"\n⏱️ Timeout after {max_attempts * 5} seconds")
            return
        
        # Show results
        print("="*70)
        print("RESULTS")
        print("="*70 + "\n")
        
        print(f"University: {data['university_name']}")
        print(f"Domain: {data['domain']}")
        print(f"Programs Found: {data['programs_count']}")
        print(f"Time: {data.get('elapsed_seconds', 0):.1f}s\n")
        
        if data['programs_count'] > 0:
            print("-"*70)
            print("PROGRAM LIST:\n")
            
            programs = data['programs']
            for i, prog in enumerate(programs[:20], 1):
                name = prog.get('program_name', 'Unknown')
                level = prog.get('degree_level', '')
                url = prog.get('url', '')
                
                print(f"{i:2d}. {name}")
                if level:
                    print(f"    Level: {level}")
                if url:
                    # Shorten URL for display
                    display_url = url if len(url) <= 70 else url[:67] + "..."
                    print(f"    URL: {display_url}")
                print()
            
            if data['programs_count'] > 20:
                print(f"... and {data['programs_count'] - 20} more programs\n")
        
        print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(test_api())
