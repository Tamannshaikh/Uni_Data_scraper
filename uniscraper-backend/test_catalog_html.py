#!/usr/bin/env python3
"""
Test if catalog pages return static HTML or need JS rendering.
"""
import asyncio
import httpx


CATALOG_URLS = [
    ("ASU", "https://degrees.apps.asu.edu/masters-phd"),
    ("ASU Alt", "https://degrees.apps.asu.edu/masters-phd/major-list/letter/all"),
    ("UCLA", "https://grad.ucla.edu/academics/masters-studies"),
    ("UCLA Alt", "https://www.ucla.edu/academics/programs-and-majors"),
    ("Ohio State", "https://artsandsciences.osu.edu/academics/programs/graduate"),
    ("Ohio State Alt", "https://gpadmissions.osu.edu/programs/programs.aspx"),
]


async def test_url(name: str, url: str):
    """Test if URL returns usable HTML."""
    print(f"\n{'='*80}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*80}\n")
    
    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        ) as client:
            response = await client.get(url)
            
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
            print(f"Content length: {len(response.text)} chars")
            
            html = response.text
            
            # Check if it's just a JS shell
            is_js_shell = (
                '<div id="root"></div>' in html or
                '<div id="app"></div>' in html or
                (html.count('<script') > 10 and html.count('<a ') < 5)
            )
            
            # Check for program indicators
            has_masters = "master" in html.lower()
            has_phd = "phd" in html.lower() or "doctor" in html.lower()
            has_links = html.count('<a ') > 10
            has_program_words = "program" in html.lower()
            
            print(f"\n{'='*40}")
            print(f"ANALYSIS:")
            print(f"{'='*40}")
            print(f"JS shell page: {is_js_shell}")
            print(f"Has 'master': {has_masters}")
            print(f"Has 'phd/doctor': {has_phd}")
            print(f"Has links (<a>): {has_links} ({html.count('<a ')} found)")
            print(f"Has 'program': {has_program_words}")
            
            # Show first 3000 chars
            print(f"\n{'='*40}")
            print(f"FIRST 3000 CHARS:")
            print(f"{'='*40}")
            print(html[:3000])
            
            # Verdict
            print(f"\n{'='*40}")
            if is_js_shell:
                print(f"VERDICT: ❌ JS-RENDERED - needs Jina Reader or Playwright")
            elif has_links and (has_masters or has_phd) and has_program_words:
                print(f"VERDICT: ✅ STATIC HTML - simple httpx works")
            elif has_masters or has_phd:
                print(f"VERDICT: ⚠️  PARTIAL - has degree keywords but few links")
            else:
                print(f"VERDICT: ❓ UNCLEAR - needs manual inspection")
            print(f"{'='*40}\n")
            
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}\n")


async def main():
    """Test all catalog URLs."""
    print(f"\n{'#'*80}")
    print(f"CATALOG HTML TEST")
    print(f"{'#'*80}")
    print(f"Testing if catalog pages return static HTML or need JS rendering")
    print(f"{'#'*80}\n")
    
    for name, url in CATALOG_URLS:
        await test_url(name, url)
        await asyncio.sleep(1)  # Be nice to servers


if __name__ == "__main__":
    asyncio.run(main())
