"""
Isolated fetch stress test: Test _fetch_html directly under different configurations.

Goal: Determine if timeout OR concurrency OR both are the bottleneck.
Runtime: 3-5 minutes total (not 10+ minutes for full discovery).
"""
import asyncio
import logging
import time
from collections import Counter
import httpx

logging.basicConfig(
    level=logging.WARNING,  # Reduce noise
    format='%(levelname)s:%(name)s:%(message)s'
)

# Test URLs from Arkansas (known to fail in bulk)
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
    "https://www.astate.edu/programs/graduate-certificate-in-financial-management.html",
    "https://www.astate.edu/programs/bs-in-global-supply-chain-management.html",
    "https://www.astate.edu/programs/certificate-in-engineering-management-systems.html",
    "https://www.astate.edu/programs/minor-in-management.html",
    "https://www.astate.edu/programs/ms-in-engineering-management.html",
    "https://www.astate.edu/programs/bs-in-mathematics.html",
    "https://www.astate.edu/programs/bs-in-disaster-preparedness-and-emergency-management.html",
    "https://www.astate.edu/programs/minor-in-mathematics.html",
    "https://www.astate.edu/programs/certificate-in-livestock-business-management.html",
    "https://www.astate.edu/programs/bs-in-construction-management.html",
    "https://www.astate.edu/programs/bs-in-marketing.html",
    "https://www.astate.edu/programs/minor-in-marketing.html",
    "https://www.astate.edu/programs/ms-in-mathematics.html",
    "https://www.astate.edu/programs/mse-in-mathematics.html",
    "https://www.astate.edu/programs/bs-in-finance-financial-management.html",
    "https://www.astate.edu/programs/bs-in-engineering-management-systems.html",
    "https://www.astate.edu/programs/bs-in-mass-communications-creative-media.html",
    "https://www.astate.edu/programs/certificate-in-strategic-communication-social-media-management.html",
    "https://www.astate.edu/programs/graduate-certificate-in-engineering-management.html",
    "https://www.astate.edu/programs/bs-in-entrepreneurial-management-and-strategic-leadership.html",
    "https://www.astate.edu/programs/bs-in-hospitality-and-event-tourism-management.html",
    "https://www.astate.edu/programs/minor-in-hospitality-and-event-tourism-management.html",
    "https://www.astate.edu/programs/graduate-certificate-in-marketing.html",
    "https://www.astate.edu/programs/graduate-certificate-in-global-supply-chain-management.html",
    "https://www.astate.edu/programs/msmc-in-mass-communications-journalism.html",
    "https://www.astate.edu/programs/certificate-in-advanced-materials-and-manufacturing.html",
    "https://www.astate.edu/programs/bs-in-mass-communications-sports-media.html",
    "https://www.astate.edu/programs/bs-in-engineering-technology-manufacturing-and-cad.html",
    "https://www.astate.edu/programs/bs-in-fashion-merchandising-and-marketing.html",
    "https://www.astate.edu/programs/bse-in-mathematics.html",
    "https://www.astate.edu/programs/bs-in-marketing-sales-leadership.html",
    "https://www.astate.edu/programs/msmc-in-mass-communications-radio-television.html",
    "https://www.astate.edu/programs/bs-in-sport-management.html",
    "https://www.astate.edu/programs/post-bachelors-certificate-in-advanced-medical-imaging-and-therapy-mammography.html",
    "https://www.astate.edu/programs/minor-in-financial-wealth-management.html",
    "https://www.astate.edu/programs/bs-in-mass-communications.html",
    "https://www.astate.edu/programs/bsrs-in-radiologic-sciences-magnetic-resonance-imaging.html",
    "https://www.astate.edu/programs/bs-in-entrepreneurial-management-and-strategic-leadership-human-resource-management.html",
    "https://www.astate.edu/programs/bsrs-in-radiologic-sciences-mammography-breast-sonography.html",
    "https://www.astate.edu/programs/macc-master-of-accountancy-with-data-analytics.html",
] * 2  # Duplicate to get 100 total requests


_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


async def fetch_with_tracking(url: str, timeout: float, sem: asyncio.Semaphore, results: dict):
    """Fetch with exception tracking."""
    async with sem:
        start = time.time()
        
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
                elapsed = time.time() - start
                
                results["success"] += 1
                results["times"].append(elapsed)
                return True
                
        except httpx.TimeoutException as e:
            elapsed = time.time() - start
            results["TimeoutException"] += 1
            results["times"].append(elapsed)
            return False
            
        except httpx.ConnectError as e:
            elapsed = time.time() - start
            results["ConnectError"] += 1
            results["times"].append(elapsed)
            return False
            
        except asyncio.CancelledError:
            elapsed = time.time() - start
            results["CancelledError"] += 1
            results["times"].append(elapsed)
            return False
            
        except Exception as e:
            elapsed = time.time() - start
            exc_type = type(e).__name__
            results[exc_type] = results.get(exc_type, 0) + 1
            results["times"].append(elapsed)
            return False


async def run_test(concurrency: int, timeout: float, test_name: str):
    """Run stress test with given configuration."""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'='*80}")
    print(f"Configuration: concurrency={concurrency}, timeout={timeout}s")
    print(f"URLs to fetch: {len(TEST_URLS)}")
    
    results = {
        "success": 0,
        "TimeoutException": 0,
        "ConnectError": 0,
        "CancelledError": 0,
        "times": []
    }
    
    sem = asyncio.Semaphore(concurrency)
    start = time.time()
    
    tasks = [fetch_with_tracking(url, timeout, sem, results) for url in TEST_URLS]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    elapsed = time.time() - start
    
    # Calculate stats
    total_requests = len(TEST_URLS)
    total_failures = total_requests - results["success"]
    failure_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
    
    avg_time = sum(results["times"]) / len(results["times"]) if results["times"] else 0
    
    print(f"\nResults:")
    print(f"  Total time: {elapsed:.1f}s")
    print(f"  Successful: {results['success']}/{total_requests} ({100 - failure_rate:.1f}%)")
    print(f"  Failed: {total_failures}/{total_requests} ({failure_rate:.1f}%)")
    print(f"  Avg fetch time: {avg_time:.2f}s")
    
    if total_failures > 0:
        print(f"\nFailure breakdown:")
        for exc_type in ["TimeoutException", "ConnectError", "CancelledError"]:
            count = results.get(exc_type, 0)
            if count > 0:
                pct = (count / total_failures * 100)
                print(f"  {exc_type:20s} {count:4d} ({pct:5.1f}% of failures)")
        
        # Other exceptions
        other_count = 0
        for key, val in results.items():
            if key not in ["success", "TimeoutException", "ConnectError", "CancelledError", "times"]:
                other_count += val
        if other_count > 0:
            print(f"  {'Other exceptions':20s} {other_count:4d}")
    
    return {
        "config": f"concurrency={concurrency}, timeout={timeout}s",
        "success_rate": 100 - failure_rate,
        "failure_rate": failure_rate,
        "dominant_exception": max(
            [(k, v) for k, v in results.items() if k not in ["success", "times"]],
            key=lambda x: x[1],
            default=("none", 0)
        )[0] if total_failures > 0 else "none",
        "avg_time": avg_time,
        "total_time": elapsed
    }


async def main():
    print("="*80)
    print("FETCH LAYER STRESS TEST - ISOLATE TIMEOUT VS CONCURRENCY")
    print("="*80)
    print(f"\nTesting {len(TEST_URLS)} Arkansas URLs under different configurations")
    print("Goal: Determine which factor (timeout or concurrency) causes failures")
    
    results = []
    
    # Test 1: Baseline (original settings that fail)
    result1 = await run_test(
        concurrency=30,
        timeout=6.0,
        test_name="Baseline (concurrency=30, timeout=6s)"
    )
    results.append(result1)
    await asyncio.sleep(2)  # Brief cooldown
    
    # Test 2: Increased timeout only
    result2 = await run_test(
        concurrency=30,
        timeout=10.0,
        test_name="Fix #1: Increased Timeout (concurrency=30, timeout=10s)"
    )
    results.append(result2)
    await asyncio.sleep(2)
    
    # Test 3: Reduced concurrency only  
    result3 = await run_test(
        concurrency=15,
        timeout=6.0,
        test_name="Fix #2: Reduced Concurrency (concurrency=15, timeout=6s)"
    )
    results.append(result3)
    await asyncio.sleep(2)
    
    # Test 4: Both fixes
    result4 = await run_test(
        concurrency=15,
        timeout=10.0,
        test_name="Fix #1+#2: Both (concurrency=15, timeout=10s)"
    )
    results.append(result4)
    
    # Summary
    print(f"\n{'='*80}")
    print("COMPARATIVE SUMMARY")
    print(f"{'='*80}")
    print(f"\n{'Configuration':<45} {'Success':>10} {'Fail':>10} {'Dominant Exception':>20}")
    print("-"*90)
    
    for r in results:
        config_short = r['config'].replace('concurrency=', 'c=').replace('timeout=', 't=')
        print(f"{config_short:<45} {r['success_rate']:>9.1f}% {r['failure_rate']:>9.1f}% {r['dominant_exception']:>20}")
    
    print(f"\n{'='*80}")
    print("DIAGNOSIS")
    print(f"{'='*80}")
    
    baseline_fail = results[0]['failure_rate']
    timeout_fail = results[1]['failure_rate']
    concurrency_fail = results[2]['failure_rate']
    both_fail = results[3]['failure_rate']
    
    print(f"\nBaseline failure rate: {baseline_fail:.1f}%")
    
    if timeout_fail < baseline_fail * 0.5:
        print(f"\n[CONFIRMED] Timeout increase alone reduces failures by >50%")
        print(f"  Baseline: {baseline_fail:.1f}% -> Timeout fix: {timeout_fail:.1f}%")
        print(f"  Root cause: 6s timeout too aggressive")
        print(f"  Fix: Keep timeout=10s")
    elif concurrency_fail < baseline_fail * 0.5:
        print(f"\n[CONFIRMED] Concurrency reduction alone reduces failures by >50%")
        print(f"  Baseline: {baseline_fail:.1f}% -> Concurrency fix: {concurrency_fail:.1f}%")
        print(f"  Root cause: 30 concurrent requests overload")
        print(f"  Fix: Reduce to concurrency=15")
    elif both_fail < baseline_fail * 0.5:
        print(f"\n[CONFIRMED] Both fixes needed to reduce failures by >50%")
        print(f"  Baseline: {baseline_fail:.1f}% -> Both fixes: {both_fail:.1f}%")
        print(f"  Root cause: Combination of timeout + concurrency")
        print(f"  Fix: timeout=10s AND concurrency=15")
    else:
        print(f"\n[INCONCLUSIVE] Fixes don't significantly reduce failures")
        print(f"  Baseline: {baseline_fail:.1f}%")
        print(f"  Timeout fix: {timeout_fail:.1f}%")
        print(f"  Concurrency fix: {concurrency_fail:.1f}%")
        print(f"  Both: {both_fail:.1f}%")
        print(f"  Root cause: May be rate limiting, connection pooling, or other")
        print(f"  Recommendation: Investigate dominant exception type")


if __name__ == "__main__":
    asyncio.run(main())
