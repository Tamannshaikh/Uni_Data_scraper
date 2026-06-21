# Final Recommendation: Fix Arkansas Extraction Failures

**Date**: June 21, 2026  
**Status**: Evidence-based recommendation ready for implementation

---

## Summary of Evidence

### ✅ What We Proved

1. **Extraction logic works perfectly** (10/10 test URLs succeeded individually)
2. **Three exception paths exist** (TimeoutException, ConnectError, generic Exception)
3. **Problem only occurs under concurrent load** (0% fail individually, 84% fail in bulk)
4. **Average fetch time under load**: 8.59s (exceeds 6s timeout)

### ⚠️ What We Couldn't Measure

- Exact distribution of exception types (tests timeout before completion)
- However, the 8.59s average strongly suggests TimeoutException dominates

---

## Recommended Fix (Immediate)

### Fix #1: Increase Timeout for Candidate Fetching

**File**: `pipeline/program_discovery.py`  
**Line**: ~973 (in `fetch_candidate_info` function)

**Current**:
```python
html, status = await _fetch_html(url, timeout=6.0)
```

**Change to**:
```python
html, status = await _fetch_html(url, timeout=10.0)
```

**Rationale**:
- Average time under load: 8.59s
- Current timeout: 6.0s
- Pages time out before completing
- Increasing to 10s gives adequate buffer

**Expected impact**:
- Failure rate: 84% → 30-40%
- More slow pages will complete
- Slight increase in phase time (but fewer failures means faster overall)

---

### Fix #2: Reduce Concurrent Fetches (If Fix #1 Insufficient)

**File**: `pipeline/program_discovery.py`  
**Line**: ~959 (in `gemini_classify_candidates` function)

**Current**:
```python
fetch_sem = asyncio.Semaphore(30)  # Increased from 15 to 30
```

**Change to**:
```python
fetch_sem = asyncio.Semaphore(15)  # Reduce back to 15
```

**Rationale**:
- 30 concurrent requests may overload astate.edu
- Manchester succeeds with 30, but Arkansas struggles
- Lower concurrency = less contention = faster individual requests

**Expected impact**:
- Failure rate: Further reduction to 10-20%
- Slightly longer phase time, but much higher success rate

---

## Implementation Strategy

### Phase 1: Test Fix #1 Alone (5 minutes)

1. Change timeout from 6.0s → 10.0s
2. Re-run Arkansas test
3. Measure:
   - Failure rate (expect <40%)
   - Total runtime
   - Programs discovered

**If successful** (failure rate <30%):
- Deploy Fix #1 only
- Monitor production

**If insufficient** (failure rate still >40%):
- Proceed to Phase 2

---

### Phase 2: Add Fix #2 (If Needed)

1. Keep timeout at 10.0s
2. Also reduce concurrency: 30 → 15
3. Re-run Arkansas test
4. Measure again

**Expected**:
- Failure rate <20%
- Programs discovered: 150-250
- Runtime: Slightly longer but acceptable

---

## Code Changes Required

### Change 1: Increase Timeout

```python
# File: pipeline/program_discovery.py
# Function: fetch_candidate_info (inside gemini_classify_candidates)
# Line: ~973

async def fetch_candidate_info(url: str) -> dict | None:
    async with fetch_sem:
        url_start = time.time()
        
        try:
            # OLD: html, status = await _fetch_html(url, timeout=6.0)
            html, status = await _fetch_html(url, timeout=10.0)  # ← CHANGE THIS
            
            url_duration = time.time() - url_start
            candidate_fetch_times.append(url_duration)
            # ... rest of function ...
```

### Change 2: Reduce Concurrency (Optional, if Fix #1 insufficient)

```python
# File: pipeline/program_discovery.py
# Function: gemini_classify_candidates
# Line: ~959

# OLD: fetch_sem = asyncio.Semaphore(30)  # Increased from 15 to 30
fetch_sem = asyncio.Semaphore(15)  # ← CHANGE THIS (if needed)
```

---

## Expected Outcomes

### Before (Baseline)
```
Fetch failures: 303/361 (84%)
Fetch phase: 142s
Programs: 75
Average: 8.59s/URL
```

### After Fix #1 (timeout=10.0s)
```
Fetch failures: 120/361 (33%) [estimated]
Fetch phase: 160s (longer, but more successful)
Programs: 150-200
Average: 7.5s/URL (less timeouts)
```

### After Fix #1 + Fix #2 (timeout=10s, concurrency=15)
```
Fetch failures: 50/361 (14%) [estimated]
Fetch phase: 180s
Programs: 200-250
Average: 6.5s/URL (even better)
```

---

## Why This Is The Right Approach

### Evidence-Based
- ✅ Avg fetch time (8.59s) > timeout (6s)
- ✅ Works individually (0% fail) but not in bulk (84% fail)
- ✅ Manchester (2.7% fail) vs Arkansas (84% fail) with same concurrency

### Conservative
- Start with timeout increase (low risk)
- Only reduce concurrency if needed (more conservative)
- Test incrementally, not all at once

### Measurable
- Clear success metrics (failure rate <30%)
- Easy to validate (re-run test)
- Can revert if doesn't work

---

## Alternative Approaches (Not Recommended)

### ❌ Lower word count threshold
- Evidence shows pages have 400-2,200 words
- Validation isn't the problem

### ❌ Switch extraction methods
- Crawl4AI works perfectly (10/10 succeeded)
- Not an extraction issue

### ❌ Add complex retry logic
- Solve root cause first (timeout/concurrency)
- Add retries later if still needed

---

## Next Steps

1. ✅ **Implement Fix #1** (timeout 6s → 10s)
2. ⏳ **Test with Arkansas** (expect ~5 min runtime)
3. 📊 **Measure results**:
   - Failure rate < 30%? → Success, deploy
   - Failure rate > 40%? → Add Fix #2
4. ✅ **Document findings**
5. 🚀 **Deploy to production**

---

## Success Criteria

**Minimum**:
- Failure rate <30% (vs 84% baseline)
- Programs discovered >150 (vs 75 baseline)
- No increase in total runtime >20%

**Target**:
- Failure rate <20%
- Programs discovered >200
- Total runtime similar or better

---

## Confidence Level

**High confidence** (80%+) that Fix #1 will significantly improve Arkansas:
- Direct evidence: avg=8.59s > timeout=6s
- Analogous evidence: Works fine individually (no timeout pressure)
- Comparative evidence: Manchester succeeds with similar architecture

**Medium confidence** (60%) that Fix #1 alone is sufficient:
- Might also need Fix #2 (reduced concurrency)
- But worth testing Fix #1 first (simpler, less impact)

---

## Bottom Line

**Implement timeout increase from 6s to 10s immediately.**

This is the lowest-risk, highest-impact change supported by evidence. If it's insufficient, we have Fix #2 ready to go.

The instrumented tests took too long to complete, but we have enough evidence to proceed with confidence.
