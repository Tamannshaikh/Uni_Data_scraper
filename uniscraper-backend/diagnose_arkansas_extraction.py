"""
Diagnostic script to investigate why 84% of Arkansas candidate fetches fail.

From logs: 303/361 URLs return no_content (status=0) despite many being HTTP 200.

This script tests 10 failed URLs to identify the root cause.
"""
import asyncio
import logging
import httpx
from pipeline.program_discovery import _fetch_html, _get_title, _get_snippet, _word_count, _is_soft_404

logging.basicConfig(
    level=logging.WARNING,  # Reduce noise
    format='%(levelname)s:%(name)s:%(message)s'
)

# Sample URLs that failed with no_content in the Arkansas run
TEST_URLS = [
    "https://www.astate.edu/programs/minor-in-english.html",
    "https://www.astate.edu/programs/bs-in-public-health.html",
    "https://www.astate.edu/programs/mm-in-music-composition.html",
    "https://www.astate.edu/programs/msa-in-agriculture.html",
    "https://www.astate.edu/programs/certificate-in-computed-tomography.html",
    "https://www.astate.edu/programs/minor-in-religious-studies.html",
    "https://www.astate.edu/programs/certificate-in-business-analytics.html",
    "https://www.astate.edu/programs/ms-in-exercise-science.html",
    "https://www.astate.edu/programs/bfa-in-art-art-education.html",
    "https://www.astate.edu/programs/minor-in-sociology.html",
]


async def diagnose_url(url: str) -> dict:
    """Diagnose why a URL fails extraction."""
    
    print(f"\n{'='*80}")
    print(f"URL: {url}")
    print('='*80)
    
    result = {
        "url": url,
        "http_status": None,
        "html_length": 0,
        "word_count": 0,
        "title": None,
        "snippet_length": 0,
        "failure_reason": None,
        "is_soft_404": False,
    }
    
    # Test 1: Direct HTTP request
    print("\n[Test 1] Direct HTTP request with httpx...")
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.get(url)
            result["http_status"] = response.status_code
            raw_html = response.text
            result["html_length"] = len(raw_html)
            
            print(f"  HTTP Status: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('content-type', 'unknown')}")
            print(f"  HTML Length: {len(raw_html):,} bytes")
            print(f"  First 200 chars: {raw_html[:200]}")
            
            if response.status_code != 200:
                result["failure_reason"] = f"HTTP {response.status_code}"
                print(f"  [FAIL] Non-200 status code")
                return result
                
            if not raw_html or len(raw_html) < 100:
                result["failure_reason"] = "Empty or too short HTML"
                print(f"  [FAIL] HTML too short")
                return result
                
    except Exception as e:
        result["failure_reason"] = f"HTTP error: {type(e).__name__}"
        print(f"  [FAIL] HTTP request failed: {e}")
        return result
    
    # Test 2: _fetch_html (uses Crawl4AI or fallback)
    print("\n[Test 2] Using _fetch_html (pipeline method)...")
    try:
        html, status = await _fetch_html(url, timeout=10.0)
        
        print(f"  Returned Status: {status}")
        print(f"  Returned HTML Length: {len(html) if html else 0:,} bytes")
        
        if status != 200:
            result["failure_reason"] = f"_fetch_html status={status}"
            print(f"  [FAIL] _fetch_html returned status {status}")
            return result
            
        if not html:
            result["failure_reason"] = "_fetch_html returned empty HTML"
            print(f"  [FAIL] _fetch_html returned no content")
            return result
            
    except Exception as e:
        result["failure_reason"] = f"_fetch_html error: {type(e).__name__}"
        print(f"  [FAIL] _fetch_html failed: {e}")
        return result
    
    # Test 3: Word count validation
    print("\n[Test 3] Word count validation...")
    word_count = _word_count(html)
    result["word_count"] = word_count
    
    print(f"  Word count: {word_count}")
    
    if word_count < 50:
        result["failure_reason"] = f"Word count too low ({word_count} < 50)"
        print(f"  [FAIL] Word count {word_count} below threshold (50)")
        print(f"  Text preview: {html[:300]}")
        return result
    
    # Test 4: Title extraction
    print("\n[Test 4] Title extraction...")
    title = _get_title(html)
    result["title"] = title
    
    print(f"  Title: {title}")
    
    if not title:
        result["failure_reason"] = "No title found"
        print(f"  [WARN] No title extracted")
    
    # Test 5: Soft 404 detection
    print("\n[Test 5] Soft 404 detection...")
    is_404 = _is_soft_404(title)
    result["is_soft_404"] = is_404
    
    if is_404:
        result["failure_reason"] = "Soft 404 detected"
        print(f"  [FAIL] Title indicates soft 404: {title}")
        return result
    
    # Test 6: Snippet extraction
    print("\n[Test 6] Snippet extraction...")
    snippet = _get_snippet(html, max_words=200)
    result["snippet_length"] = len(snippet)
    
    print(f"  Snippet length: {len(snippet)} chars")
    print(f"  Snippet preview: {snippet[:200]}")
    
    # Success!
    print("\n[SUCCESS] All validations passed!")
    print(f"  This URL should NOT have failed with no_content")
    result["failure_reason"] = None
    
    return result


async def main():
    print("="*80)
    print("ARKANSAS EXTRACTION FAILURE DIAGNOSTIC")
    print("="*80)
    print(f"\nTesting {len(TEST_URLS)} URLs that failed with no_content...")
    print("\nGoal: Identify why pages that return HTTP 200 fail extraction")
    
    results = []
    for url in TEST_URLS:
        result = await diagnose_url(url)
        results.append(result)
        await asyncio.sleep(0.5)  # Brief pause between tests
    
    # Summary
    print("\n" + "="*80)
    print("DIAGNOSTIC SUMMARY")
    print("="*80)
    
    from collections import Counter
    failure_reasons = Counter(r["failure_reason"] for r in results)
    
    print(f"\nTotal URLs tested: {len(results)}")
    print(f"Successful extractions: {sum(1 for r in results if r['failure_reason'] is None)}")
    print(f"Failed extractions: {sum(1 for r in results if r['failure_reason'] is not None)}")
    
    print(f"\nFailure reasons:")
    for reason, count in failure_reasons.most_common():
        if reason:
            print(f"  {reason}: {count}")
    
    # Statistics
    print(f"\nStatistics:")
    print(f"  Avg HTML length: {sum(r['html_length'] for r in results) / len(results):,.0f} bytes")
    print(f"  Avg word count: {sum(r['word_count'] for r in results) / len(results):.0f}")
    print(f"  URLs with title: {sum(1 for r in results if r['title'])}/{len(results)}")
    print(f"  Soft 404s: {sum(1 for r in results if r['is_soft_404'])}/{len(results)}")
    
    # Detailed results
    print(f"\n" + "="*80)
    print("DETAILED RESULTS")
    print("="*80)
    
    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['url'].split('/')[-1]}")
        print(f"   Status: {r['http_status']}")
        print(f"   HTML: {r['html_length']:,} bytes, {r['word_count']} words")
        print(f"   Title: {r['title'] or '(none)'}")
        print(f"   Result: {r['failure_reason'] or 'SUCCESS'}")
    
    # Recommendations
    print(f"\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    if failure_reasons.get("Word count too low (X < 50)"):
        print("\n1. Word count threshold (50) may be too strict for Arkansas pages")
        print("   Consider: Lower threshold to 30, or use different validation")
    
    if failure_reasons.get("_fetch_html returned empty HTML"):
        print("\n2. Crawl4AI extraction is failing on Arkansas HTML structure")
        print("   Consider: Use raw HTML fallback, or investigate Crawl4AI config")
    
    if failure_reasons.get("_fetch_html status=0"):
        print("\n3. _fetch_html returning status=0 indicates internal extraction error")
        print("   Consider: Add more detailed logging in _fetch_html to see why")
    
    if sum(1 for r in results if r['failure_reason'] is None) == len(results):
        print("\n✅ All test URLs pass extraction in isolation!")
        print("   The failure may be concurrent-request related, rate limiting,")
        print("   or timeout issues when processing hundreds of URLs simultaneously.")


if __name__ == "__main__":
    asyncio.run(main())
