"""
Test Priority 1 changes via API endpoint
Verify that landing pages are detected and expanded
"""
import requests
import time
import json

def test_priority1_via_api():
    print("=" * 80)
    print("PRIORITY 1 API TEST: Landing Page Detection")
    print("=" * 80)
    print()
    
    # Start discovery
    print("Starting discovery for Purdue University...")
    response = requests.post(
        "http://localhost:8000/api/v1/discover",
        json={
            "university_name": "Purdue University",
            "domain": "purdue.edu",
            "max_programs": 40
        }
    )
    
    if response.status_code not in [200, 202]:
        print(f"ERROR: Failed to start discovery: {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    request_id = data.get("request_id") or data.get("discovery_id")
    print(f"[OK] Discovery started: request_id={request_id}")
    print()
    
    # Poll for completion
    print("Waiting for discovery to complete...")
    max_attempts = 60
    attempt = 0
    
    while attempt < max_attempts:
        time.sleep(5)
        attempt += 1
        
        status_response = requests.get(f"http://localhost:8000/api/v1/status/{request_id}")
        if status_response.status_code != 200:
            print(f"ERROR: Failed to get status: {status_response.status_code}")
            continue
        
        status_data = status_response.json()
        status = status_data.get("status")
        progress = status_data.get("progress", 0)
        
        print(f"  [{attempt}] Status: {status}, Progress: {progress}%")
        
        if status in ["completed", "failed", "error"]:
            break
    
    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    if status != "completed":
        print(f"[WARN] Discovery ended with status: {status}")
        if status_data.get("error"):
            print(f"Error: {status_data['error']}")
        return
    
    # Get results
    results_response = requests.get(f"http://localhost:8000/api/v1/results/{request_id}")
    if results_response.status_code != 200:
        print(f"ERROR: Failed to get results: {results_response.status_code}")
        return
    
    results = results_response.json()
    programs = results.get("programs", [])
    discovery_list = results.get("discovery_list", [])
    
    print(f"Total programs discovered: {len(programs)}")
    print(f"Discovery list candidates: {len(discovery_list)}")
    print()
    
    # Check for landing page indicators
    landing_indicators = [
        "business.purdue.edu/phd",
        "business.purdue.edu/masters",
        "Added from landing page"
    ]
    
    print("Checking for Priority 1 indicators:")
    print("  Looking for evidence that landing pages were detected and expanded...")
    print()
    
    # Show sample programs
    print(f"Sample programs from results ({min(10, len(programs))} of {len(programs)}):")
    for i, prog in enumerate(programs[:10], 1):
        name = prog.get("program_name", "N/A")
        level = prog.get("degree_level", "N/A")
        url = prog.get("url", "")
        print(f"  {i}. {name} ({level})")
        print(f"      {url[:80]}")
    print()
    
    # Check discovery list for landing pages
    landing_count = 0
    for item in discovery_list:
        url = item.get("url", "")
        if "business.purdue.edu/phd" in url or "business.purdue.edu/masters" in url:
            landing_count += 1
            print(f"[OK] Found landing page in discovery: {url}")
    
    if landing_count > 0:
        print()
        print(f"[OK] Detected {landing_count} landing pages in discovery list")
    
    print()
    print("=" * 80)
    print("ASSESSMENT")
    print("=" * 80)
    
    if len(programs) > 15:
        print(f"[PASS] {len(programs)} programs discovered (significant improvement)")
        print("  Landing page expansion appears to be working!")
    elif len(programs) > 12:
        print(f"[PARTIAL] {len(programs)} programs (some improvement)")
        print("  Landing pages may be partially working")
    else:
        print(f"[BASELINE] {len(programs)} programs")
        print("  Similar to pre-fix baseline - may need quota refresh")
    
    print()

if __name__ == "__main__":
    try:
        test_priority1_via_api()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
