# Instrumentation Complete - Ready for Evidence-Based Optimization

## Status: ✅ Ready to Test

You were absolutely right to be cautious about celebrating the rate limiter fix prematurely. The logs didn't prove where the 190 seconds went.

## What Changed

### 1. Comprehensive Wall-Clock Instrumentation (High Confidence)

Every phase now reports:
- **Absolute wall-clock time** (`t=X.Xs` from Stage 3 start)
- **Phase duration** (how long each phase took)
- **Gaps between phases** (should be ~0s if no hidden overhead)
- **Rate limiter actual waits** (not estimates)

### Example New Log Output

```
[program_discovery] t=0.0s: Starting auto-confirm phase
[program_discovery] t=15.2s: Auto-confirm complete (phase took 15.2s)
[program_discovery] t=15.2s: Starting candidate fetch phase (140 candidates)
[program_discovery] t=138.9s: Candidate fetch complete (phase took 123.7s)  ← PROOF!
[program_discovery] t=138.9s: Starting Gemini classification phase
[program_discovery] t=138.9s: Starting Gemini batch 1
[program_discovery] Rate limiter check: 0 calls in last 60s, wait=0.0s
[program_discovery] ⏱️ RATE LIMIT: Sleeping 0.0s before API call
[program_discovery] Gemini timing: rate_limit_overhead=0.1s, api_call=16.2s, total=16.3s
[program_discovery] t=155.2s: Gemini batch 1 complete (wall-clock: 16.3s)

[program_discovery] Stage 3 TIMING BREAKDOWN:
  Phase 1 - Auto-confirm:      15.2s (t=0.0 to t=15.2s)
  Phase 2 - Candidate fetch:  123.7s (t=15.2s to t=138.9s)  ← 63% of total!
  Phase 3 - Gemini classify:   52.1s (t=138.9s to t=191.0s)
    └─ Gemini API time:        49.8s (actual API calls)
    └─ Overhead:                2.3s (4% of phase)
  TOTAL WALL-CLOCK TIME:      191.0s
  Accounted time:             191.0s
  Unaccounted overhead:         0.0s (0% of total)
```

### 2. Rate Limiter Fix (Speculative, Needs Verification)

Removed these delays from `ai_extractor.py`:
```python
_MIN_CALL_GAP = 20.0           # Forced 20s between calls
_POST_SUCCESS_COOLDOWN = 10.0  # Forced 10s after success
```

**Important:** This fix is **unproven** until the instrumentation shows whether these delays were actually causing waits.

## What the Next Test Will Prove

Run this:
```bash
py test_manchester_tier1.py
```

### The instrumentation will definitively answer:

#### Question 1: Was candidate fetching the bottleneck?
**Look for:**
```
Phase 2 - Candidate fetch: 120.0s+
```

**If YES:**
- Candidate fetching is consuming 50-60% of total time
- Rate limiter fix may have helped, but fetching is the bigger issue
- **Next optimization:** Increase fetch concurrency or optimize network

#### Question 2: Was the rate limiter over-waiting?
**Look for:**
```
⏱️ RATE LIMIT: Sleeping 25.0s before API call
```

**If YES (appears on batch 1-3):**
- Rate limiter fix didn't work or wasn't applied
- Still have unnecessary waits
- **Next step:** Debug why old behavior persists

**If NO (only appears on batch 4+):**
- Rate limiter fix worked!
- No forced delays on first 3 calls
- **Success:** Rate limiter is now optimal

#### Question 3: Is there hidden overhead?
**Look for:**
```
Unaccounted overhead: 45.0s (23% of total)
```

**If YES:**
- Something else is consuming time between phases
- Could be: locks, sequential operations, hidden sleeps
- **Next step:** Add more granular instrumentation

#### Question 4: Did the rate limiter fix help?
**Compare:**
- Old run: Gemini phase ~140s (3 batches)
- New run: Gemini phase ~50s (3 batches)

**If phase time dropped significantly:**
- Rate limiter fix was correct!
- Removed ~90s of forced waits

**If phase time similar:**
- Rate limiter wasn't the bottleneck
- Focus on other optimizations

## Predicted Results (Based on Your Analysis)

You suspected candidate fetching was the main issue. I agree. Here's my prediction:

### Most Likely Scenario: Fetching is the Bottleneck
```
Phase 1 - Auto-confirm:      15s (8%)   ← Semaphore(10), reasonable
Phase 2 - Candidate fetch:  120s (60%)  ← BOTTLENECK! 140 URLs × ~0.85s each
Phase 3 - Gemini classify:   60s (30%)
  └─ API calls:              50s
  └─ Rate limiter waits:      5s        ← Only on batch 4+
  └─ Overhead:                5s
TOTAL: 195s (19% improvement from 240s)
```

**Analysis:**
- Rate limiter fix helped a bit (removed some overhead)
- But candidate fetching is the real bottleneck
- **Next optimization:** Increase `fetch_sem` from 15 → 25

### Alternative: Rate Limiter Was the Problem (Less Likely)
```
Phase 1 - Auto-confirm:      15s (10%)
Phase 2 - Candidate fetch:   25s (15%)  ← Fast with concurrency
Phase 3 - Gemini classify:  120s (73%)
  └─ API calls:              50s
  └─ Rate limiter waits:     65s        ← OLD: Was causing long waits
  └─ Overhead:                5s
TOTAL: 160s (33% improvement)
```

**Analysis:**
- Rate limiter fix was the big win
- But OLD logs should have shown the waits explicitly
- NEW logs will show `wait=0.0s` on first 3 batches

## How to Interpret the Results

### ✅ Good Signs
- Phase times add up to total (no unaccounted overhead)
- Rate limiter wait=0.0s on batches 1-3
- Candidate fetch < 40s (means concurrency is working)
- Gemini API time ≈ Gemini phase time (minimal overhead)

### ⚠️ Red Flags
- Candidate fetch > 80s (fetching is sequential or slow)
- Rate limiter wait > 0s on batch 1-3 (fix didn't work)
- Large unaccounted overhead (>20s)
- Gemini phase >> Gemini API time (hidden delays)

## Next Optimizations (After Analysis)

Based on what the logs reveal:

### If Candidate Fetching is Slow:
```python
# Increase concurrency
fetch_sem = asyncio.Semaphore(25)  # Was 15
```

### If Rate Limiter Still Waiting:
- Check if code changes were applied
- Verify rolling window logic
- Check for hidden sleep() calls in call chain

### If Both Are Issues:
- Fix rate limiter first (higher impact)
- Then optimize fetching (bigger absolute time)

## The Scientific Method Applied

1. ✅ **Observe** - Stage 3 takes 240s, only 50s is API time
2. ✅ **Hypothesize** - Rate limiter or fetching might be slow
3. ✅ **Instrument** - Add wall-clock timing to every phase
4. ⏳ **Test** - Run Manchester discovery with instrumentation
5. ⏳ **Analyze** - Read logs to identify actual bottleneck
6. ⏳ **Optimize** - Fix the proven bottleneck (not guesses!)
7. ⏳ **Verify** - Confirm improvement with metrics

We're now at step 4. One test run will complete steps 4-5 and guide step 6.

## Summary

**You were right to be skeptical.** The evidence wasn't there yet. Now it will be.

The instrumentation will definitively show:
- ✅ Where every second is spent (no more "missing" time)
- ✅ Whether rate limiter waits are happening
- ✅ Whether fetching is sequential or parallel
- ✅ Whether the rate limiter fix helped

Run the test, read the logs, and the bottleneck will be obvious. Then we optimize based on **evidence**, not **assumptions**.

---

**Ready to test:** `py test_manchester_tier1.py`

The logs will tell the story.
