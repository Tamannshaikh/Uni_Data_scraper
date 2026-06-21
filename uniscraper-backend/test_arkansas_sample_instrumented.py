"""
Quick instrumented test: Process only first 100 URLs to get exception breakdown faster.

Goal: Identify dominant exception type in 2-3 minutes instead of 10+ minutes.
"""
import asyncio
import logging
import time
from collections import Counter

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

# Global tracking
exception_counts = Counter()
logged_failures = []
MAX_LOGGED_FAILURES = 20

async def instrumented_fetch_html(url: str, timeout: float = 6.0):
    """Instrumented version that tracks exception types."""
    import httpx
    
    _HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    start_time = time.time()
    
    try:
        timeout_config = httpx.Timeout(
            connect=3.0,
            read=timeout,
            write=5.0,
            pool=5.0
        )
        
        async with httpx.AsyncClient(
            timeout=timeout_config, follow_redirects=True, headers=_HEADERS
        ) as client:
            r = await client.get(url)
            return r.text, r.status_code
            
    except httpx.TimeoutException as e:
        elapsed = time.time() - start_time
        exception_counts["TimeoutException"] += 1
        
        if len(logged_failures) < MAX_LOGGED_FAILURES:
            logged_failures.append({
                "url": url.split('/')[-1],
                "exception": "TimeoutException",
                "message": str(e)[:80],
                "elapsed": f"{elapsed:.2f}s",
                "likely_cause": "Read timeout (page loading slowly under load)"
            })
        return "", 0
        
    except httpx.ConnectError as e:
        elapsed = time.time() - start_time
        exception_counts["ConnectError"] += 1
        
        if len(logged_failures) < MAX_LOGGED_FAILURES:
            logged_failures.append({
                "url": url.split('/')[-1],
                "exception": "ConnectError",
                "message": str(e)[:80],
                "elapsed": f"{elapsed:.2f}s",
                "likely_cause": "Cannot establish connection (rate limiting?)"
            })
        return "", 0
        
    except asyncio.CancelledError:
        elapsed = time.time() - start_time
        exception_counts["CancelledError"] += 1
        
        if len(logged_failures) < MAX_LOGGED_FAILURES:
            logged_failures.append({
                "url": url.split('/')[-1],
                "exception": "CancelledError",
                "message": "Task was cancelled",
                "elapsed": f"{elapsed:.2f}s",
                "likely_cause": "Asyncio task cancelled (timeout/semaphore)"
            })
        return "", 0
        
    except Exception as e:
        elapsed = time.time() - start_time
        exc_type = type(e).__name__
        exception_counts[exc_type] += 1
        
        if len(logged_failures) < MAX_LOGGED_FAILURES:
            logged_failures.append({
                "url": url.split('/')[-1],
                "exception": exc_type,
                "message": str(e)[:80],
                "elapsed": f"{elapsed:.2f}s",
                "likely_cause": "Unknown - needs investigation"
            })
        return "", 0


# Patch before importing
import pipeline.program_discovery as pd_module
pd_module._fetch_html = instrumented_fetch_html

from pipeline.program_discovery import discover_programs


async def test_sample():
    print("="*80)
    print("ARKANSAS SAMPLE TEST - EXCEPTION TRACKING (FIRST 100 URLs)")
    print("="*80)
    print("\nStrategy: Process limited URLs to get quick exception breakdown")
    print("Expected runtime: 2-3 minutes")
    print("-"*80)
    
    start = time.time()
    
    try:
        # This will process all URLs, but we'll get data as it runs
        programs = await discover_programs(
            domain="astate.edu",
            university_name="Arkansas State University",
            max_programs=100,  # Limit to speed up
            skip_gemini_threshold=15,
        )
        
        elapsed = time.time() - start
        
        print("\n" + "="*80)
        print("EXCEPTION ANALYSIS")
        print("="*80)
        
        total_failures = sum(exception_counts.values())
        
        if total_failures == 0:
            print("\n[INFO] No status=0 failures detected yet")
            print("This could mean:")
            print("  1. Not enough URLs processed to see failures")
            print("  2. Issue doesn't occur with limited sample")
            print("  3. Timing/load conditions different")
        else:
            print(f"\nTotal status=0 failures: {total_failures}")
            print(f"\nException breakdown:")
            
            for exc_type, count in exception_counts.most_common():
                pct = (count / total_failures * 100)
                print(f"  {exc_type:25s} {count:4d} ({pct:5.1f}%)")
            
            print(f"\n" + "="*80)
            print(f"SAMPLE FAILURES (First {len(logged_failures)})")
            print("="*80)
            
            for i, fail in enumerate(logged_failures[:10], 1):
                print(f"\n{i}. {fail['url']}")
                print(f"   Exception: {fail['exception']}")
                print(f"   Elapsed: {fail['elapsed']}")
                print(f"   Likely: {fail['likely_cause']}")
        
        print(f"\n" + "="*80)
        print("DIAGNOSIS")
        print("="*80)
        
        if total_failures == 0:
            print("\n[INCONCLUSIVE] Need to process more URLs")
            print("Recommendation: Run full test or increase sample size")
        
        elif exception_counts.get("TimeoutException", 0) / total_failures > 0.5:
            print("\n[DIAGNOSIS] TimeoutException is dominant (>50%)")
            print("  Root cause: 6s read timeout too aggressive under load")
            print("  Evidence: Pages work individually but fail in bulk")
            print("  Fix: Increase timeout in candidate fetch from 6s to 10s")
            print("  Code: program_discovery.py line ~973")
            print("        Change: timeout=6.0 -> timeout=10.0")
        
        elif exception_counts.get("ConnectError", 0) / total_failures > 0.3:
            print("\n[DIAGNOSIS] ConnectError is significant (>30%)")
            print("  Root cause: Cannot establish connections (rate limiting?)")
            print("  Evidence: Server refusing/dropping connections")
            print("  Fix: Reduce concurrency from 30 to 15")
            print("  Code: program_discovery.py line ~959")
            print("        Change: Semaphore(30) -> Semaphore(15)")
        
        elif exception_counts.get("CancelledError", 0) / total_failures > 0.2:
            print("\n[DIAGNOSIS] CancelledError is significant (>20%)")
            print("  Root cause: Tasks being cancelled prematurely")
            print("  Evidence: Asyncio cancelling in-flight requests")
            print("  Fix: Investigate cancellation logic and timeouts")
        
        else:
            print("\n[DIAGNOSIS] Mixed exceptions or unknown types")
            print("  Recommendation: Review detailed failure log above")
        
        print(f"\n" + "="*80)
        print("RESULTS")
        print("="*80)
        print(f"\nRuntime: {elapsed:.1f}s")
        print(f"Programs: {len(programs)}")
        print(f"Failures tracked: {total_failures}")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Still show collected data
        if exception_counts:
            print("\n" + "="*80)
            print("PARTIAL DATA (Before Crash)")
            print("="*80)
            print(f"\nException counts collected:")
            for exc_type, count in exception_counts.most_common():
                print(f"  {exc_type}: {count}")


if __name__ == "__main__":
    asyncio.run(test_sample())
