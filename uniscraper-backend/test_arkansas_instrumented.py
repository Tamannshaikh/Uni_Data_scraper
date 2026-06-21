"""
Instrumented Arkansas test to identify the exact exception types causing status=0 failures.

This patches _fetch_html to log detailed exception information for the first 20 failures.
"""
import asyncio
import logging
import time
from typing import Counter

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

# Global counters for exception tracking
exception_counts = Counter()
logged_failures = []
MAX_LOGGED_FAILURES = 20

# Monkey-patch _fetch_html before importing
original_fetch_html = None

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
            html = r.text
            
            return html, r.status_code
            
    except httpx.TimeoutException as e:
        elapsed = time.time() - start_time
        exception_type = type(e).__name__
        exception_counts[exception_type] += 1
        
        if len(logged_failures) < MAX_LOGGED_FAILURES:
            logged_failures.append({
                "url": url,
                "exception_type": exception_type,
                "exception_msg": str(e)[:100],
                "elapsed": elapsed,
                "timeout_config": f"connect=3s, read={timeout}s"
            })
        
        return "", 0
        
    except httpx.ConnectError as e:
        elapsed = time.time() - start_time
        exception_type = type(e).__name__
        exception_counts[exception_type] += 1
        
        if len(logged_failures) < MAX_LOGGED_FAILURES:
            logged_failures.append({
                "url": url,
                "exception_type": exception_type,
                "exception_msg": str(e)[:100],
                "elapsed": elapsed,
                "timeout_config": f"connect=3s, read={timeout}s"
            })
        
        return "", 0
        
    except asyncio.CancelledError as e:
        # Separate tracking for cancelled tasks
        elapsed = time.time() - start_time
        exception_type = "asyncio.CancelledError"
        exception_counts[exception_type] += 1
        
        if len(logged_failures) < MAX_LOGGED_FAILURES:
            logged_failures.append({
                "url": url,
                "exception_type": exception_type,
                "exception_msg": "Task was cancelled",
                "elapsed": elapsed,
                "timeout_config": f"connect=3s, read={timeout}s"
            })
        
        return "", 0
        
    except Exception as e:
        elapsed = time.time() - start_time
        exception_type = type(e).__name__
        exception_counts[exception_type] += 1
        
        if len(logged_failures) < MAX_LOGGED_FAILURES:
            logged_failures.append({
                "url": url,
                "exception_type": exception_type,
                "exception_msg": str(e)[:100],
                "elapsed": elapsed,
                "timeout_config": f"connect=3s, read={timeout}s"
            })
        
        return "", 0


# Patch before importing
import sys
import pipeline.program_discovery as pd_module
pd_module._fetch_html = instrumented_fetch_html

from pipeline.program_discovery import discover_programs


async def test_arkansas_instrumented():
    print("="*80)
    print("ARKANSAS INSTRUMENTED TEST - EXCEPTION TYPE TRACKING")
    print("="*80)
    print("\nGoal: Identify exact exception types causing status=0 failures")
    print("\nTracking:")
    print("  - Exception type (TimeoutException, ConnectError, CancelledError, etc.)")
    print("  - Exception message")
    print("  - Elapsed time before failure")
    print("  - Timeout configuration")
    print("-"*80)
    
    start = time.time()
    
    try:
        programs = await discover_programs(
            domain="astate.edu",
            university_name="Arkansas State University",
            max_programs=500,
            skip_gemini_threshold=15,
        )
        
        elapsed = time.time() - start
        
        print("\n" + "="*80)
        print("EXCEPTION ANALYSIS")
        print("="*80)
        
        total_failures = sum(exception_counts.values())
        
        print(f"\nTotal status=0 failures: {total_failures}")
        print(f"\nException types breakdown:")
        for exc_type, count in exception_counts.most_common():
            percentage = (count / total_failures * 100) if total_failures > 0 else 0
            print(f"  {exc_type}: {count} ({percentage:.1f}%)")
        
        print(f"\n" + "="*80)
        print(f"FIRST {len(logged_failures)} FAILURES (DETAILED)")
        print("="*80)
        
        for i, failure in enumerate(logged_failures, 1):
            print(f"\n{i}. URL: {failure['url'].split('/')[-1]}")
            print(f"   Exception: {failure['exception_type']}")
            print(f"   Message: {failure['exception_msg']}")
            print(f"   Elapsed: {failure['elapsed']:.2f}s")
            print(f"   Timeout: {failure['timeout_config']}")
        
        print(f"\n" + "="*80)
        print("RESULTS")
        print("="*80)
        
        print(f"\nTotal runtime: {elapsed:.1f}s")
        print(f"Total programs: {len(programs)}")
        print(f"Total failures tracked: {total_failures}")
        
        print(f"\n" + "="*80)
        print("DIAGNOSIS")
        print("="*80)
        
        if exception_counts.get("TimeoutException", 0) > total_failures * 0.5:
            print("\n[DIAGNOSIS] >50% are TimeoutExceptions")
            print("  Root cause: Pages taking longer than timeout under load")
            print("  Fix: Increase timeout from 6s to 10s")
            print("  Alternative: Reduce concurrency to lighten load")
        
        if exception_counts.get("ConnectError", 0) > total_failures * 0.3:
            print("\n[DIAGNOSIS] >30% are ConnectErrors")
            print("  Root cause: Connection pool exhaustion or rate limiting")
            print("  Fix: Reduce concurrency from 30 to 10-15")
            print("  Alternative: Add connection pooling limits")
        
        if exception_counts.get("CancelledError", 0) > total_failures * 0.2:
            print("\n[DIAGNOSIS] >20% are CancelledErrors")
            print("  Root cause: Asyncio tasks being cancelled")
            print("  Fix: Investigate task cancellation logic")
            print("  Check: Semaphore starvation or timeout edge cases")
        
        if len(exception_counts) == 0:
            print("\n[SUCCESS] No status=0 failures detected!")
            print("  Either the issue is resolved or didn't occur in this run")
        
    except Exception as e:
        print(f"\n[FAILED] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_arkansas_instrumented())
