#!/usr/bin/env python3
"""
Test fallback URLs to find working catalog pages.
"""
import asyncio
import httpx


UNIVERSITIES = [
    ("Ohio State", "osu.edu", [
        "https://gradsch.osu.edu/graduate-programs",
        "https://gpadmissions.osu.edu/programs/programs.aspx",
        "https://www.osu.edu/academics/graduate-programs",
    ]),
    ("CMU", "cmu.edu", [
        "https://www.cmu.edu/academics/academic-programs-and-majors.html",
        "https://www.cmu.edu/graduate/programs/",
        "https://www.cmu.edu/academics/",
    ]),
]


async def test_url(name: str, url: str):
    """Test if URL is accessible."""
    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        ) as client:
            response = await client.get(url)
            
            status = response.status_code
            length = len(response.text)
            
            # Check for degree keywords
            html = response.text.lower()
            has_master = "master" in html
            has_phd = "phd" in html or "doctor" in html
            
            print(f"  {url}")
            print(f"    Status: {status}, Length: {length}, Master: {has_master}, PhD: {has_phd}")
            
            if status == 200 and (has_master or has_phd):
                return "✅ GOOD"
            else:
                return f"❌ BAD (status={status})"
                
    except Exception as e:
        print(f"  {url}")
        print(f"    ERROR: {type(e).__name__}: {e}")
        return "❌ ERROR"


async def main():
    """Test all fallback URLs."""
    for name, domain, urls in UNIVERSITIES:
        print(f"\n{'='*80}")
        print(f"{name} ({domain})")
        print(f"{'='*80}\n")
        
        for url in urls:
            result = await test_url(name, url)
            print(f"    → {result}\n")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
