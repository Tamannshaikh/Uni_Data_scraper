# Next Test Run - Deeper Instrumentation + Optimizations

## Changes Made

### 1. Deeper Instrumentation Added ✅

**Auto-Confirm Phase:**
- ✅ Per-URL timing tracking
- ✅ Average/min/max request time logging
- ✅ Concurrency level logging
- ✅ Success/failure count

**Candidate Fetch Phase:**
- ✅ Per-URL timing tracking
- ✅ Average/min/max request time logging  
- ✅ Concurrency level logging
- ✅ Failed fetch count

**Example new logs:**
```
[program_discovery] Auto-confirm: 300 URLs to check, concurrency=25
[program_discovery] Auto-confirm stats: 300 URLs checked, avg=0.33s/URL, min=0.12s, max=2.14s

[program_discovery] Candidate fetch: concurrency=30
[program_discovery] Candidate fetch stats: 150 requests, 12 failed, avg=0.75s/URL, min=0.21s, max=4.52s
```

### 2. Optimizations Applied ✅

| Setting | Old Value | New Value | Expected Impact |
|---------|-----------|-----------|-----------------|
| Auto-confirm concurrency | 10 | **25** | 2.5x faster (99s → ~40s) |
| Candidate fetch concurrency | 15 | **30** | 2x faster (151s → ~75s) |
| Time limit | 240s | **600s** | Allow Gemini to run |

**Combined expected improvement:**
- Old: 250s (hit limit before Gemini)
- New: ~115s total + Gemini time
- **Goal:** Complete discovery in <180s

### 3. What the Next Run Will Tell Us

#### Question 1: Is concurrency actually being used?
**Look for:**
```
Auto-confirm: 300 URLs to check, concurrency=25
```
If avg time is still ~0.88s/URL, concurrency isn't working.
If avg time drops to ~0.15-0.30s/URL, concurrency is working.

#### Question 2: Are there slow outliers?
**Look for:**
```
avg=0.25s/URL, min=0.10s, max=5.40s
```
If max >> avg, some URLs are taking disproportionately long.
Could be:
- Slow servers
- Large pages
- Timeouts not being enforced
- Retries happening

#### Question 3: How many requests actually complete?
**Look for:**
```
300 URLs checked (was 300 candidates)
150 requests, 12 failed (was 187 candidates, 72 failed)
```
High failure rate suggests network issues or aggressive timeouts.

#### Question 4: How long does Gemini actually take?
**With 600s limit, Gemini should finally run:**
```
Phase 3 - Gemini classify: X.Xs
  └─ Gemini API time: Y.Ys
  └─ Rate limiter waits: Z.Zs
```

This will tell us if the rate limiter fix mattered at all.

## Predicted Results

### Scenario A: Concurrency Works (Best Case)
```
Phase 1 - Auto-confirm:       40s (2.5x improvement)
Phase 2 - Candidate fetch:    75s (2x improvement)
Phase 3 - Gemini classify:    50s (finally runs!)
TOTAL:                       165s
```
**Conclusion:** Optimization successful, Gemini adds 50s

### Scenario B: Concurrency Partially Works
```
Phase 1 - Auto-confirm:       60s (1.6x improvement)
Phase 2 - Candidate fetch:   100s (1.5x improvement)  
Phase 3 - Gemini classify:    50s
TOTAL:                       210s
```
**Conclusion:** Still an improvement, but need to investigate why concurrency isn't fully effective

### Scenario C: Concurrency Doesn't Work (Worst Case)
```
Phase 1 - Auto-confirm:       95s (no improvement)
Phase 2 - Candidate fetch:   150s (no improvement)
Phase 3 - Gemini classify:    50s
TOTAL:                       295s
```
**Conclusion:** Semaphores aren't the bottleneck, something else is serializing requests

## What to Check in Logs

### ✅ Good Signs
- `avg=0.20s/URL` (fast requests)
- `max=1.5s` (no major outliers)
- `concurrency=25` (high parallelism)
- `Phase 3` actually runs and completes
- Total time < 180s

### ⚠️ Warning Signs
- `avg=0.85s/URL` (still slow, concurrency not helping)
- `max=10.0s` (major outliers dragging down average)
- `150 requests, 75 failed` (high failure rate)
- `Phase 3` still hits time limit

### ❌ Red Flags
- `avg ≈ old avg` (no improvement from concurrency increase)
- Logs show sequential timing (requests completing one-by-one)
- Max time approaching timeout (6.0s)
- High retry counts

## How to Run the Test

### 1. Clear cache
```bash
.\venv\Scripts\python.exe clean_stuck_discovery.py
```

### 2. Backend should already be running
Check that terminal 11 is still active.

### 3. Run discovery test
```bash
.\venv\Scripts\python.exe test_discovery_manchester.py
```

### 4. Watch backend logs
```bash
# In another terminal or check terminal 11 output
# Look for the new timing stats
```

### 5. Let it run for up to 10 minutes
Don't interrupt! We need to see if Gemini runs.

## After the Test

### Extract Key Metrics

From logs, find:
```
[program_discovery] Auto-confirm stats: XXX URLs checked, avg=X.XXs/URL, min=X.XXs, max=X.XXs
[program_discovery] Candidate fetch stats: XXX requests, XXX failed, avg=X.XXs/URL, min=X.XXs, max=X.XXs
[program_discovery] Phase 3 - Gemini classify: XXX.Xs
```

### Calculate Improvement
```
Old auto-confirm:    99.1s
New auto-confirm:    ???s
Improvement:         ???%

Old candidate fetch: 151.4s  
New candidate fetch: ???s
Improvement:         ???%

Old Gemini:          0.0s (never ran)
New Gemini:          ???s
```

### Determine Next Steps

**If concurrency helped:**
- ✅ Mark optimization as successful
- Consider increasing further if still slow
- Move to Gemini optimization if needed

**If concurrency didn't help:**
- ❌ Semaphore not the bottleneck
- Investigate: Are requests actually parallel?
- Check: Is there a hidden sequential operation?
- Profile: Where is the actual time being spent?

## Success Criteria

**Minimum viable:**
- Total time < 300s (completes within extended limit)
- Gemini phase runs to completion
- Get timing data for all 3 phases

**Good:**
- Total time < 180s
- Auto-confirm < 50s
- Candidate fetch < 80s
- Gemini < 50s

**Excellent:**
- Total time < 120s
- All phases show improvement from concurrency
- No major outliers (max < 2x avg)
- Low failure rate (<10%)

---

**Status:** Ready to test
**Expected runtime:** 3-10 minutes
**Backend:** Running on terminal 11
**Next action:** Run `test_discovery_manchester.py`
