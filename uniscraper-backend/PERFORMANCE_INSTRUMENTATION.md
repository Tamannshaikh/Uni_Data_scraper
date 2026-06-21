# Performance Instrumentation & Rate Limiter Fix

## Date
2026-06-20

## Problem Statement
Stage 3 (Gemini classification) was consuming ~240 seconds but only showing ~50 seconds of actual Gemini API time. The missing ~190 seconds needed investigation.

## Hypothesis vs. Evidence

### Initial Hypothesis
The rate limiter might be over-aggressive with forced delays between calls.

### Evidence Gaps (Pre-Instrumentation)
The original logs showed:
- Gemini batch 1: 18.3s
- Gemini batch 2: 15.6s
- Gemini batch 3: 16.0s
- Total Stage 3: ~240s

**BUT:** These logs didn't show:
- ❌ Wall-clock timestamps between batches
- ❌ How long candidate fetching actually took
- ❌ Whether rate limiter waits occurred
- ❌ Time gaps between phases

**The 190s could have been:**
1. Candidate fetching (140 URLs × 1s each = 140s)
2. Rate limiter waits (30s × 3 calls = 90s)
3. Both
4. Something else entirely

## Changes Made (Instrumentation First!)

### Priority 1: Comprehensive Timing Instrumentation

Added **wall-clock timestamps** for every phase and transition:

```python
# Example output with new instrumentation:
[program_discovery] t=0.0s: Starting auto-confirm phase
[program_discovery] t=15.2s: Auto-confirm complete (phase took 15.2s)
[program_discovery] t=15.2s: Starting candidate fetch phase (140 candidates)
[program_discovery] t=138.7s: Candidate fetch complete (phase took 123.5s)  ← SMOKING GUN?
[program_discovery] t=138.7s: Starting Gemini classification phase
[program_discovery] t=138.7s: Starting Gemini batch 1
[program_discovery] Rate limiter check: 0 calls in last 60s, wait=0.0s
[program_discovery] Gemini timing: rate_limit_overhead=0.1s, api_call=16.2s, total=16.3s
[program_discovery] t=155.0s: Gemini batch 1 complete (wall-clock: 16.3s)
[program_discovery] t=155.0s: Starting Gemini batch 2
[program_discovery] Rate limiter check: 1 calls in last 60s, wait=0.0s
[program_discovery] Gemini timing: rate_limit_overhead=0.1s, api_call=15.8s, total=15.9s
[program_discovery] t=170.9s: Gemini batch 2 complete (wall-clock: 15.9s)
```

**What this reveals:**
- Exact time when each phase starts/ends
- Gaps between phases (should be ~0s)
- Rate limiter actual waits (not guesses)
- API call vs total batch time

### Priority 2: Rate Limiter Fix (Speculative)

**Removed potentially redundant delays:**
```python
# REMOVED (speculative fix):
_MIN_CALL_GAP = 20s
_POST_SUCCESS_COOLDOWN = 10s

# KEPT (proven necessary):
_MAX_RPM = 3 (rolling window)
```

**Why speculative:**
- No wall-clock proof these delays were actually the bottleneck
- Could have been candidate fetching all along
- Instrumentation will prove whether this helped

## Expected Outcomes from Next Test Run

### Scenario A: Candidate Fetching Was the Bottleneck
```
Phase 1 - Auto-confirm:      15.2s (t=0.0 to t=15.2)
Phase 2 - Candidate fetch:  138.7s (t=15.2 to t=153.9)  ← 99% of candidates
  └─ 140 candidates × ~1s each
Phase 3 - Gemini classify:   52.3s (t=153.9 to t=206.2)
  └─ Gemini API time:        49.8s
  └─ Rate limiter waits:      0.0s  ← No forced waits!
TOTAL: 206.2s
```

**Verdict:** Rate limiter fix did nothing. **Next optimization: Parallel fetching.**

### Scenario B: Rate Limiter Was the Bottleneck  
```
Phase 1 - Auto-confirm:      15.2s (t=0.0 to t=15.2)
Phase 2 - Candidate fetch:   22.1s (t=15.2 to t=37.3)
Phase 3 - Gemini classify:  142.9s (t=37.3 to t=180.2)
  └─ Gemini API time:        49.8s
  └─ Rate limiter waits:     90.0s  ← 30s × 3 batches!
TOTAL: 180.2s
```

**Verdict:** OLD LOGS would show rate waits. NEW LOGS won't. **Rate limiter fix was correct.**

### Scenario C: Both Were Problems
```
OLD RUN:
  Candidate fetch: 90s
  Rate limiter waits: 90s
  Total: ~240s

NEW RUN:
  Candidate fetch: 90s (unchanged)
  Rate limiter waits: 0s (fixed!)
  Total: ~150s
```

**Verdict:** Rate limiter fix helped 40%, but candidate fetching needs optimization too.

## What the Instrumentation Will Prove

| Question | Answer Location |
|----------|----------------|
| How long does candidate fetching actually take? | `Phase 2 - Candidate fetch: X.Xs` |
| Are rate limiter waits happening? | `rate_limit_overhead=X.Xs` per batch |
| Is there overhead in Gemini classification? | `Gemini classify - Gemini API time = overhead` |
| Are there gaps between phases? | Compare wall-clock `t=X.Xs` transitions |
| Did the rate limiter fix help? | Before/after comparison of rate_limit_overhead |

## Next Steps

### 1. Run Test with New Instrumentation
```bash
py test_manchester_tier1.py
```

### 2. Read the Logs Like a Detective

**If you see:**
```
Phase 2 - Candidate fetch: 120.0s+
```
**Then:** Candidate fetching is the bottleneck (as you suspected!)

**If you see:**
```
⏱️ RATE LIMIT: Sleeping 25.0s before API call
```
**Then:** Rate limiter is still causing waits (need more investigation)

**If you see:**
```
Unaccounted overhead: 45.0s
```
**Then:** Something else is consuming time (sequential ops? locks?)

### 3. Optimize Based on Evidence

**If candidate fetching is slow:**
- Increase `fetch_sem` from 15 → 25
- Check network latency
- Consider caching

**If rate limiter is still aggressive:**
- Check if old code is still running
- Verify rolling window logic
- Check for hidden sleep() calls

**If overhead is high:**
- Add more granular instrumentation
- Check for sequential operations
- Profile async tasks

## Risk Assessment

**Instrumentation Changes:**
- ✅ **Zero Risk** - Only adds logging
- ✅ Negligible performance overhead (<1s)
- ✅ Provides definitive answers

**Rate Limiter Changes:**
- ⚠️ **Low-Medium Risk** - Based on logical reasoning, not hard evidence
- ✅ Still enforces 3 RPM (safe for Gemini API)
- ❓ May or may not improve performance (instrumentation will prove it)

## The Right Approach

You were absolutely correct to be cautious. The proper scientific method is:

1. ✅ **Observe** - Something is slow (240s Stage 3)
2. ✅ **Hypothesize** - Rate limiter might be over-aggressive
3. ✅ **Instrument** - Add detailed logging to prove/disprove
4. ⏳ **Test** - Run with instrumentation (next step!)
5. ⏳ **Analyze** - Read logs to find actual bottleneck
6. ⏳ **Optimize** - Fix the proven bottleneck
7. ⏳ **Verify** - Confirm improvement

We jumped to step 6 (optimize) before completing steps 3-5. Now the instrumentation will complete steps 3-5 properly.

## Prediction

Based on your analysis, my prediction for the next run:

| Component | Time (seconds) | Percentage |
|-----------|----------------|------------|
| Auto-confirm fetch | 15-20s | 8-10% |
| **Candidate fetch** | **90-140s** | **45-60%** ← **LIKELY WINNER** |
| Gemini API calls | 50-60s | 25-30% |
| Rate limiter waits | 0-30s | 0-15% (depends on fix) |
| Other overhead | 5-15s | 2-5% |
| **TOTAL** | **160-240s** | 100% |

The instrumentation will tell us definitively.

## Changes Made

### 1. Fixed Rate Limiter (`ai_extractor.py`)
**Removed redundant delays:**
```python
# BEFORE:
_MIN_CALL_GAP = 20.0
_POST_SUCCESS_COOLDOWN = 10.0
_last_call_time: float = 0.0

async def _call_gemini(...):
    # Wait for MIN_CALL_GAP
    gap_wait = _MIN_CALL_GAP - (now - _last_call_time)
    if gap_wait > 0:
        await asyncio.sleep(gap_wait)
    
    # Make API call
    ...
    
    # Wait for POST_SUCCESS_COOLDOWN
    await asyncio.sleep(_POST_SUCCESS_COOLDOWN)

# AFTER:
# (Variables removed, logic simplified)

async def _call_gemini(...):
    # Only use rolling window RPM limiter
    rpm_wait = _enforce_rpm_limit()
    if rpm_wait > 0:
        await asyncio.sleep(rpm_wait)
    
    # Track request and make API call immediately
    _request_timestamps.append(time.monotonic())
    # ... API call ...
```

**Expected Impact:**
- Stage 3 should complete **significantly faster** (potentially 50%+ improvement)
- Still respects 3 RPM limit (safe for Gemini free tier)
- No risk of 429s or quota violations

### 2. Added Detailed Timing Instrumentation (`program_discovery.py`)

**New timing breakdown:**
```python
timings = {
    "auto_confirm_phase": 0.0,      # Time fetching high-confidence URLs
    "candidate_fetch_phase": 0.0,   # Time fetching candidates for Gemini
    "gemini_classify_phase": 0.0,   # Total time in classification loop
    "gemini_api_time": 0.0,         # Actual Gemini API call time
}
```

**Logged information:**
- Per-phase timing at each stage completion
- Rate limiter state before every Gemini call
- API call duration vs total batch duration
- Overhead detection (unaccounted time)

**Example Output:**
```
[program_discovery] Stage 3: 75 auto-confirmed, 140 need Gemini (auto-confirm took 12.3s)
[program_discovery] Stage 3: 140/155 candidates fetched for Gemini in 18.7s
[program_discovery] Rate limiter: 2 calls in last 60s, wait=0.0s
[program_discovery] Gemini API call: 16.2s (rate_limit_wait: 0.0s)
[program_discovery] Gemini batch 1: 12 candidates classified in 16.5s (API call: 16.2s)
[program_discovery] Stage 3 timing breakdown: auto_confirm=12.3s, candidate_fetch=18.7s, 
    gemini_phase=50.1s (gemini_api=49.8s), total=81.1s
```

## Next Steps

### 1. Test the Fix
Run a discovery test on Manchester or Arkansas:
```bash
python test_discovery_manchester.py
```

**Look for:**
- Reduced total Stage 3 time (should be closer to actual work time)
- No 429 errors or quota violations
- Rate limiter only activating when >3 calls in 60s

### 2. Analyze New Timing Logs
Check the timing breakdown to identify remaining bottlenecks:

**If `auto_confirm_phase` is high (>20s):**
- Check if Semaphore(10) is actually being used
- Verify network latency isn't causing sequential behavior

**If `candidate_fetch_phase` is high (>30s):**
- Check if Semaphore(15) is effective
- Consider increasing concurrency if network can handle it

**If `gemini_api_time` is close to `gemini_classify_phase`:**
- ✅ Good! No hidden overhead in classification loop

**If there's >10s of unaccounted overhead:**
- Check for other synchronous blocking operations
- Look for hidden sleep() calls or sequential processing

### 3. Consider Further Optimizations (After Verification)

**Increase Auto-Confirmation Coverage:**
```python
# Add Manchester-specific patterns (very low risk)
_HIGH_CONFIDENCE_PATTERNS += [
    r"manchester\.ac\.uk/study/masters/courses/list",
    r"manchester\.ac\.uk/study/postgraduate-research/programmes",
]
```

**Increase Concurrency (If Network Allows):**
```python
auto_confirm_sem = asyncio.Semaphore(15)  # Was 10
fetch_sem = asyncio.Semaphore(20)         # Was 15
```

**Increase Batch Size (If API Allows):**
```python
batch_size: int = 15,  # Was 12
```

## Expected Performance Improvement

**Before:**
- Stage 3: ~240s total
- Gemini calls: ~50s
- Overhead: ~190s (79% waste!)

**After (Conservative Estimate):**
- Stage 3: ~100-120s total
- Rate limiter fix saves: ~60s
- Better instrumentation reveals remaining bottlenecks
- Overhead should be <20s

**After (Optimistic with All Fixes):**
- Stage 3: ~70-80s total
- 70% auto-confirmation reduces Gemini load
- Parallel fetching optimized
- Minimal overhead

## Risk Assessment

**Rate Limiter Changes:**
- ✅ Low risk - still enforces 3 RPM hard limit
- ✅ No API quota violations expected
- ✅ Rolling window is more accurate than fixed gaps

**Instrumentation:**
- ✅ Zero risk - only adds logging
- ✅ Negligible performance overhead (<0.1s)

## Verification Checklist

- [ ] Test discovery run completes without errors
- [ ] No 429 errors from Gemini API
- [ ] Stage 3 completes faster than 240s
- [ ] Timing breakdown shows <20s overhead
- [ ] Rate limiter logs show sensible wait times
- [ ] Auto-confirmation rate remains high (>40%)
