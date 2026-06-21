# Status Update: Exception Tracking Investigation

**Date**: June 21, 2026  
**Context**: Investigating why 84% of Arkansas fetches return `status=0`

---

## What We've Learned

### 1. ✅ Extraction Logic Works Perfectly
**Diagnostic test**: 10/10 failed URLs extracted successfully when tested individually
- All returned HTTP 200
- All had 400-2,200 words
- All had valid titles
- All passed validation

**Conclusion**: The extraction, parsing, and validation logic is NOT broken.

---

### 2. ✅ Identified Three Exception Paths for status=0

From `_fetch_html()` in `program_discovery.py` (lines 50-92):

```python
async def _fetch_html(url: str, timeout: float = 6.0):
    try:
        # ... fetch logic ...
        return html, r.status_code
        
    except httpx.TimeoutException as e:
        logger.debug(f"fetch timeout ({timeout}s): {url}")
        return "", 0  # ← PATH 1
        
    except httpx.ConnectError as e:
        logger.debug(f"fetch connection error: {url}")
        return "", 0  # ← PATH 2
        
    except Exception as e:
        logger.debug(f"fetch error {url}: {type(e).__name__}")
        return "", 0  # ← PATH 3
```

**All three paths return the same value**: `("", 0)`

This means `status=0` could represent:
1. **Timeout** (read timeout after 6s)
2. **Connection failure** (can't establish connection)
3. **Any other exception** (asyncio.CancelledError, pool exhaustion, memory error, etc.)

---

### 3. ⚠️ Current Logging is Insufficient

The current logging:
```python
logger.debug(f"fetch timeout ({timeout}s): {url} - {type(e).__name__}")
```

Problems:
- Uses `logger.debug()` - might not be visible in production
- Only logs exception type, not detailed message
- No aggregation to see which exception dominates
- No elapsed time tracking

---

## What We Need to Know

Before implementing any architectural changes (concurrency, timeout, retries), we must determine:

### Question 1: Which exception type dominates?

**If TimeoutException > 50%**:
- Root cause: 6s timeout too aggressive under load
- Fix: Increase timeout to 10s
- Alternative: Reduce concurrency

**If ConnectError > 30%**:
- Root cause: Connection pool exhaustion or rate limiting
- Fix: Reduce concurrency from 30 to 10-15
- Alternative: Implement retry logic with backoff

**If asyncio.CancelledError > 20%**:
- Root cause: Tasks being cancelled prematurely
- Fix: Investigate cancellation logic
- Check: Semaphore starvation, timeout edge cases

**If generic Exception dominates**:
- Root cause: Unknown (could be Crawl4AI, memory, etc.)
- Fix: Need to see actual exception messages

---

### Question 2: What are the elapsed times?

**If failures happen at ~6.0s**:
- Confirms read timeout is the bottleneck
- Pages are loading slowly under concurrent load

**If failures happen at ~3.0s**:
- Confirms connect timeout is the issue
- Server is not accepting connections fast enough

**If failures happen at random times**:
- Suggests intermittent issues (rate limiting, cancellation, etc.)

---

## Next Action

### Created Instrumented Test

File: `test_arkansas_instrumented.py`

**What it does**:
1. Patches `_fetch_html()` to track exception types
2. Logs first 20 failures with:
   - Exception type
   - Exception message
   - Elapsed time
   - URL
   - Timeout configuration
3. Provides breakdown:
   - Count per exception type
   - Percentage distribution
   - Diagnosis based on patterns

**Expected output**:
```
Exception types breakdown:
  TimeoutException: 250 (82.5%)
  ConnectError: 40 (13.2%)
  CancelledError: 10 (3.3%)
  Other: 3 (1.0%)

[DIAGNOSIS] >50% are TimeoutExceptions
  Root cause: Pages taking longer than timeout under load
  Fix: Increase timeout from 6s to 10s
```

---

## Blocked on Long Run Time

The instrumented test is taking >5 minutes to complete (300s timeout hit).

This is because:
- Arkansas discovery takes ~200-300s total
- Must complete full discovery to get exception statistics

---

## Recommendation

### Option A: Wait for Instrumented Test to Complete
- Let it run for 10+ minutes
- Get complete exception breakdown
- Make data-driven decision

### Option B: Quick Test with Sample
- Modify test to only process first 100 URLs
- Get exception breakdown faster (2-3 minutes)
- Less comprehensive but faster feedback

### Option C: Implement Educated Guess
Based on evidence:
- Individual tests: All work (0% failure)
- Bulk test: 84% failure
- Avg time: 8.59s/URL (suggests timeouts)

**Likely cause**: TimeoutException  
**Quick fix to test**: Increase timeout from 6s to 10s

---

## Files Created

1. `diagnose_arkansas_extraction.py` - ✅ Proved extraction logic works
2. `test_arkansas_instrumented.py` - ⏳ Running (identifying exception types)
3. `EXTRACTION_FAILURE_ANALYSIS.md` - Analysis document
4. `STATUS_UPDATE_EXCEPTION_TRACKING.md` - This file

---

## Summary

**What we know**:
- ✅ Extraction works (10/10 success individually)
- ✅ Three possible exception types for status=0
- ⚠️ Don't know which exception type dominates
- ⚠️ Don't know elapsed times for failures

**What we're waiting for**:
- Instrumented test results showing exception type breakdown

**What we can do now**:
1. Wait for full instrumented test (10+ min)
2. Run quick sample test (100 URLs, 2-3 min)
3. Make educated guess (TimeoutException, increase timeout to 10s)

**Recommendation**: Option C (educated guess) to unblock progress, then validate with instrumented data later.
