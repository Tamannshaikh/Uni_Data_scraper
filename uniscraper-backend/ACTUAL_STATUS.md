# Actual Status: No Timing Data Yet

## What Actually Happened

### The Discovery Task Never Completed

**Discovery ID:** `305fe450-004b-4652-b395-25b58ff837a3`  
**Started:** 2026-06-20 18:30:42  
**Status:** `running` (stuck)  
**Programs Found:** 0  
**Completed:** Never  

### Root Cause: Auto-Reload Killed the Task

The backend was running with **uvicorn auto-reload enabled** (watchfiles). Every time I created a test file:
1. `test_discovery_manchester.py` created → backend reloaded
2. `clear_manchester_cache.py` created → backend reloaded  
3. `check_manchester_discovery.py` created → backend reloaded

Each reload **cancelled the running discovery task** mid-execution.

**Evidence from logs:**
```
INFO:     Application startup complete.
INFO:watchfiles.main:1 change detected
WARNING:  WatchFiles detected changes in 'test_discovery_manchester.py'. Reloading...
INFO:     Shutting down
...
asyncio.exceptions.CancelledError
```

### The httpx.ReadError Explained

The test client got `httpx.ReadError` because:
1. Discovery task was running
2. Backend detected file change
3. Uvicorn shut down mid-request
4. Socket closed unexpectedly
5. Client polling failed

This is **exactly what you predicted:** "httpx.ReadError often means backend process died / socket closed unexpectedly"

## Current Situation

### ✅ What's Ready
- Comprehensive timing instrumentation is in place
- Rate limiter fix is applied
- Test scripts are created
- Code compiles without errors

### ❌ What's Missing
- **Zero actual timing data from instrumentation**
- No evidence rate limiter fix helped
- No evidence candidate fetching is the bottleneck
- No completed discovery run with new code

### The Cached Run is Unreliable

The cached run that returned:
```
Time: 992.6s
Programs found: 15
Degree breakdown:
  Bachelor's: 8
  Master's: 6  
  PhD: 1
```

This is **highly suspicious** because:
- Previous Manchester runs found **144 programs**
- Now only 15, with many undergraduates
- 992.6s is ~16 minutes (extremely long)
- Suggests incomplete/failed run or different pipeline

**Conclusion:** Don't use this for performance analysis.

## Your Analysis Was Correct

You identified every issue:

1. ✅ **"Fresh Manchester run never completed"**
   - Status: `running` with 0 programs
   - Confirmed

2. ✅ **"Backend process crashed / hung / deadlocked"**  
   - Actually: Auto-reload cancelled task
   - Same effect: Discovery never finished

3. ✅ **"httpx.ReadError means socket closed unexpectedly"**
   - Caused by uvicorn reload
   - Confirmed

4. ✅ **"Until resolved, you have zero timing data"**
   - Absolutely correct
   - Instrumentation ran 0 times successfully

5. ✅ **"Cached run is suspicious"**
   - 15 programs vs 144 expected
   - Don't use for benchmarking
   - Confirmed

## What Needs to Happen Next

### Priority 1: Run Discovery Without Auto-Reload

**Option A: Disable auto-reload**
```bash
# In main.py, change:
uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
# To:
uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
```

**Option B: Run in production mode**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --no-reload
```

**Option C: Run discovery directly (bypass API)**
```python
# Direct function call in a standalone script
from pipeline.program_discovery import discover_programs
result = await discover_programs("University of Manchester", "manchester.ac.uk")
```

### Priority 2: Add Stage-Level Crash Protection

Add try/except around each stage:
```python
try:
    logger.info("START Stage 1: Sitemap fetch")
    locs = await stage1()
    logger.info(f"END Stage 1: {len(locs)} URLs")
except Exception as e:
    logger.exception("STAGE 1 CRASHED")
    raise

try:
    logger.info("START Stage 2: Cheap prefilter")
    filtered = stage2(locs)
    logger.info(f"END Stage 2: {len(filtered)} URLs")
except Exception as e:
    logger.exception("STAGE 2 CRASHED")
    raise

# ... etc for all stages
```

This way if it crashes again, you'll know exactly where.

### Priority 3: Check for Stuck Discovery Task

The database still shows `status=running`. Either:
1. Task is actually still running (check CPU usage)
2. Task crashed without updating status
3. Task deadlocked

**Check:**
```python
# Mark stuck discovery as failed
await db.discovery_results.update_one(
    {"discovery_id": "305fe450-004b-4652-b395-25b58ff837a3"},
    {"$set": {"status": "failed", "error": "Cancelled by auto-reload"}}
)
```

## The Bigger Picture

### What We Know
- ✅ Instrumentation code is correct
- ✅ Rate limiter fix is applied  
- ❌ Zero evidence either helped
- ❌ Zero actual timing measurements

### What We Don't Know
- ❓ Where the 190 seconds actually went
- ❓ Whether rate limiter was the bottleneck
- ❓ Whether candidate fetching is the bottleneck
- ❓ Whether the instrumentation works as designed

### The Hypothesis Remains Unproven

**Your hypothesis:** Candidate fetching is 50-70% of the time  
**My hypothesis:** Rate limiter was forcing 30s delays  
**Current evidence:** Neither hypothesis has been tested

## Lesson Learned

You were right to be cautious. The proper sequence is:

1. ✅ Observe problem (240s Stage 3)
2. ✅ Form hypotheses (fetching vs rate limiter)
3. ✅ Add instrumentation
4. ❌ **Run test successfully** ← WE ARE HERE
5. ⏳ Analyze results
6. ⏳ Optimize based on evidence

We skipped step 4 due to auto-reload interference.

## Next Action

**Immediate:**
1. Stop the current backend process
2. Clear the stuck discovery from database
3. Restart backend with `--no-reload`
4. Run fresh Manchester discovery
5. Let it complete fully
6. Read the timing logs
7. Then (and only then) analyze performance

**The instrumentation is ready. The test just needs to actually complete.**

---

**Status:** ❌ No usable data yet  
**Blocker:** Auto-reload cancelled the discovery task  
**Fix:** Run with `--no-reload` or direct function call  
**ETA:** One successful run away from having real evidence
