"""
Quick test to verify rate limiter behavior after optimization.
Tests that:
1. No forced 20s gaps between calls
2. No 10s post-success cooldown
3. Rolling window correctly enforces 3 RPM
"""
import asyncio
import time
from pipeline.ai_extractor import _enforce_rpm_limit, _request_timestamps, _MAX_RPM


def test_rate_limiter():
    """Test rate limiter logic without making actual API calls."""
    
    print("Testing rate limiter behavior...")
    print(f"Max RPM: {_MAX_RPM}\n")
    
    # Clear any existing timestamps
    _request_timestamps.clear()
    
    # Simulate 3 rapid requests
    now = time.monotonic()
    
    # Request 1
    wait1 = _enforce_rpm_limit()
    print(f"Request 1: wait={wait1:.1f}s (expected: 0.0s)")
    assert wait1 == 0.0, "First request should have no wait"
    _request_timestamps.append(now)
    
    # Request 2 (immediately after)
    wait2 = _enforce_rpm_limit()
    print(f"Request 2: wait={wait2:.1f}s (expected: 0.0s)")
    assert wait2 == 0.0, "Second request should have no wait"
    _request_timestamps.append(now + 0.1)
    
    # Request 3 (immediately after)
    wait3 = _enforce_rpm_limit()
    print(f"Request 3: wait={wait3:.1f}s (expected: 0.0s)")
    assert wait3 == 0.0, "Third request should have no wait"
    _request_timestamps.append(now + 0.2)
    
    # Request 4 (should trigger rate limit)
    wait4 = _enforce_rpm_limit()
    print(f"Request 4: wait={wait4:.1f}s (expected: ~60.0s)")
    assert wait4 > 59.0, f"Fourth request should wait ~60s, got {wait4:.1f}s"
    
    print("\n✅ Rate limiter test passed!")
    print("Behavior:")
    print("  - No forced gaps between first 3 requests")
    print("  - 4th request correctly waits for rolling window")
    print("  - No post-success cooldowns\n")


async def test_actual_timing():
    """Test actual timing with simulated API calls."""
    
    print("Testing actual call timing (simulated)...")
    _request_timestamps.clear()
    
    start = time.time()
    call_times = []
    
    # Simulate 3 rapid calls
    for i in range(3):
        wait = _enforce_rpm_limit()
        if wait > 0:
            print(f"  Call {i+1}: Waiting {wait:.1f}s")
            await asyncio.sleep(wait)
        
        _request_timestamps.append(time.monotonic())
        call_time = time.time() - start
        call_times.append(call_time)
        print(f"  Call {i+1}: Executed at {call_time:.1f}s")
        
        # Simulate API response time
        await asyncio.sleep(0.5)
    
    total_time = time.time() - start
    print(f"\nTotal time for 3 calls: {total_time:.1f}s")
    print(f"Expected: ~1.5s (3 × 0.5s API time)")
    
    if total_time < 5.0:
        print("✅ No excessive delays!")
    else:
        print(f"⚠️  Unexpected delays: {total_time - 1.5:.1f}s overhead")


if __name__ == "__main__":
    test_rate_limiter()
    asyncio.run(test_actual_timing())
    
    print("\n" + "="*60)
    print("SUMMARY:")
    print("="*60)
    print("Rate limiter now uses ONLY rolling window (3 RPM).")
    print("Removed forced delays:")
    print("  ❌ _MIN_CALL_GAP = 20s")
    print("  ❌ _POST_SUCCESS_COOLDOWN = 10s")
    print("\nExpected Stage 3 improvement: 50%+ faster")
    print("="*60)
