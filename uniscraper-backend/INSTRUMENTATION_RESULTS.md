# Manchester Discovery Instrumentation Results

## Date: 2026-06-20
## Discovery ID: c3ade875-28ba-40b9-8d43-c5e33a1f59d7

## Executive Summary

**The rate limiter hypothesis was completely wrong. Candidate fetching is the bottleneck.**

## Hard Data

```
Phase 1 - Auto-confirm:      99.1s (40% of total)
Phase 2 - Candidate fetch:  151.4s (60% of total)
Phase 3 - Gemini classify:    0.0s (0% - never reached)
TOTAL WALL-CLOCK TIME:      250.5s
```

**Critical finding:** Hit 240s time limit before Gemini ran even once.

## Breakdown

| Phase | Time | % of Total | Details |
|-------|------|------------|---------|
| Auto-confirm | 99.1s | 39.6% | 113 programs confirmed |
| Candidate fetch | 151.4s | 60.4% | 115/187 candidates fetched |
| Gemini classify | 0.0s | 0% | **Never executed** |
| **Total** | **250.5s** | **100%** | Hit time limit |

## What This Proves

### ✅ Confirmed
1. **Candidate fetching is the primary bottleneck (60%)**
   - 151.4s to fetch 115 candidates
   - ~1.3s per page
   - Should be much faster with proper concurrency

2. **Auto-confirm is surprisingly expensive (40%)**
   - 99.1s for 113 programs
   - ~0.88s per program
   - "Fast path" isn't that fast

3. **Gemini never ran**
   - 0 API calls made
   - 0 seconds consumed
   - Hit time limit before starting

### ❌ Disproven
1. **Rate limiter was NOT the bottleneck**
   - The hypothesis that rate limiter caused delays is false
   - Gemini phase was never reached
   - The fix (removing `_MIN_CALL_GAP`) had zero impact

2. **Gemini was NOT slow**
   - Never got a chance to run
   - Can't be the bottleneck if it never executes

## The Real Problem

**We have TWO bottlenecks, not one:**

### Bottleneck #1: Candidate Fetch (151.4s)
- 187 candidates to process
- Only 115 fetched before timeout
- 72 candidates never fetched
- Average: 1.3s per page

**Expected with proper concurrency:** 
- 15 concurrent requests
- 115 pages should take ~10-15s total
- **Actual: 151.4s (10x slower than expected!)**

**Possible causes:**
- Semaphore too low (under-parallelized)
- Sequential fetching somewhere
- Retries consuming time
- Network latency
- Heavy pages taking long to load

### Bottleneck #2: Auto-Confirm (99.1s)
- 300 total candidates checked
- 113 confirmed as high-confidence
- 187 sent to Stage 2
- Average: ~0.33s per URL check

**Why this is suspicious:**
- Auto-confirm is supposed to be the "fast path"
- Should just be URL pattern matching + quick HTTP check
- 99 seconds suggests it's doing heavy fetching too

**What might be happening:**
- Fetching full pages for auto-confirm
- Not actually "auto" - doing validation
- Semaphore limiting concurrency
- Retries on failures

## What We Don't Know Yet

1. **What happens inside auto-confirm for 99 seconds?**
   - URL pattern matching: instant
   - HTTP requests: 300 × 0.33s = 99s ← Likely this
   - Unknown

2. **Why is candidate fetch so slow?**
   - Actual concurrency level?
   - Retry count?
   - Network latency?
   - Page size/complexity?

3. **How long would Gemini take?**
   - 0s observed (never ran)
   - 115 candidates remaining
   - 8 batches expected
   - Could be 50-100s if allowed to run

## Next Investigation Steps

### Priority 1: Instrument Auto-Confirm Phase

Add timing per request:
```python
logger.info(f"Auto-confirm: Starting {len(candidates)} URLs")
# ... 
logger.info(f"Auto-confirm: {len(confirmed)} confirmed, {len(rejected)} rejected")
logger.info(f"Auto-confirm: Avg time per URL: {avg_time:.2f}s")
logger.info(f"Auto-confirm: Concurrency level: {semaphore._value}")
```

### Priority 2: Instrument Candidate Fetch Phase

Add per-batch timing:
```python
logger.info(f"Fetch batch starting: {len(batch)} URLs")
batch_start = time.time()
# ... fetch ...
batch_duration = time.time() - batch_start
logger.info(f"Fetch batch complete: {len(results)} fetched in {batch_duration:.1f}s")
logger.info(f"  Avg per URL: {batch_duration / len(results):.2f}s")
```

### Priority 3: Raise Time Limit Temporarily

Change from 240s to 600s:
```python
max_duration_seconds: float = 600.0,  # Was 240.0
```

This will allow Gemini to actually run so we can measure its true impact.

### Priority 4: Check Actual Concurrency

Log semaphore state:
```python
logger.info(f"Auto-confirm semaphore: {auto_confirm_sem._value} slots")
logger.info(f"Fetch semaphore: {fetch_sem._value} slots")
```

Verify they're actually being used in parallel.

## Optimization Recommendations (Based on Data)

### Immediate (High Impact):
1. **Increase fetch concurrency**
   ```python
   fetch_sem = asyncio.Semaphore(30)  # Was 15
   ```
   Expected impact: 151s → ~75s (50% improvement)

2. **Increase auto-confirm concurrency**
   ```python
   auto_confirm_sem = asyncio.Semaphore(25)  # Was 10
   ```
   Expected impact: 99s → ~40s (60% improvement)

3. **Raise time limit during testing**
   ```python
   max_duration_seconds = 600.0
   ```
   Allow Gemini to run so we can measure its true cost

### After Deeper Instrumentation:
4. Check if auto-confirm is doing unnecessary fetching
5. Check if retries are happening
6. Consider timeout adjustments
7. Profile network latency

## Comparison to Original Hypothesis

| Hypothesis | Predicted % | Actual % | Result |
|------------|-------------|----------|--------|
| **Candidate fetching** | 50-70% | 60.4% | ✅ **CORRECT** |
| Gemini API | 20-30% | 0% | ❌ Never ran |
| Rate limiter | 5-15% | 0% | ❌ Never ran |
| Auto-confirm overhead | Not predicted | 39.6% | ⚠️ **Surprise finding** |

**User was right:** Candidate fetching dominated the runtime.

**Rate limiter fix was irrelevant:** Gemini never executed, so rate limiter delays weren't the issue.

**New discovery:** Auto-confirm is also unexpectedly expensive at 40% of runtime.

## Production Implications

For Manchester with ~300 program candidates:
- **Current:** 250s total, hits limit, incomplete results
- **With 2x concurrency:** ~125s total, should complete fully
- **With optimized auto-confirm:** ~90s total
- **Target:** <120s for full discovery with Gemini

## Conclusion

The instrumentation succeeded. We now have definitive evidence that:
1. ✅ Page fetching (auto-confirm + candidate fetch) consumes 100% of runtime
2. ✅ Gemini never runs (hits time limit first)
3. ❌ Rate limiter hypothesis was wrong
4. ⚠️ Auto-confirm "fast path" is surprisingly slow

**Next action:** Add deeper instrumentation inside both fetch phases to understand why parallelization isn't working as expected.
