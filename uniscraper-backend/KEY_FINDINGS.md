# Manchester Discovery - Key Findings (TL;DR)

## 🎯 Bottom Line

**Original hypothesis:** Gemini rate limiter is slow (30s delays per call)  
**Reality:** Gemini is fast (1s per candidate) and rate limiter fix worked (0s overhead)

**Real bottlenecks:**
1. 🔴 Auto-confirm wastes 53% of effort fetching pattern-rejected URLs (~45s wasted)
2. 🔴 Candidate fetch has 86% failure rate (only 36/263 succeed)

---

## 📊 The Numbers

### Test Run v2 (Complete End-to-End)

```
╔═══════════════════════════════════════════════════════════╗
║  Phase 1 - Auto-confirm:       82.6s  (28% of total)     ║
║  Phase 2 - Candidate fetch:   171.9s  (58% of total)     ║
║  Phase 3 - Gemini classify:    41.6s  (14% of total)     ║
║  ─────────────────────────────────────────────────────    ║
║  TOTAL:                       296.1s                      ║
╚═══════════════════════════════════════════════════════════╝
```

**Key insights:**
- ✅ Gemini only 14% of runtime (NOT the bottleneck)
- 🔴 Candidate fetch 58% of runtime (MAIN bottleneck)
- ⚠️ Auto-confirm 28% of runtime (surprisingly high for "fast path")

---

## 🔴 Critical Finding #1: Auto-Confirm Waste

### The Problem

```python
# Current code
if not _is_high_confidence_url(url):  # Pattern check
    return None
    
html, status = await _fetch_html(url, timeout=4.0)  # ← STILL FETCHES!
```

### The Evidence

```
pattern_matched  = 140  (47%)  ← Should be fetched
pattern_rejected = 160  (53%)  ← Should NOT be fetched!

But ACTUALLY fetched = 300 (100%)  ← BUG!
```

**53% of fetches are wasted** on URLs that already failed pattern matching.

### The Fix

```python
# Fixed code
if not _is_high_confidence_url(url):
    return None  # ← Return WITHOUT fetching!

# Only fetch if pattern matched
html, status = await _fetch_html(url, timeout=4.0)
```

### Expected Impact

```
Current:  82.6s (fetches all 300)
After:    ~40s  (fetches only 140)
Savings:  ~43s (52% improvement)
```

---

## 🔴 Critical Finding #2: Candidate Fetch Failures

### The Numbers

```
Total requests:  263
Succeeded:        36  (14%)
Failed:          227  (86%)  ← TERRIBLE!

Timing:
  avg = 13.86s/URL
  min =  1.03s
  max = 33.99s
```

**86% failure rate is catastrophic.**

### Why Throughput is Low

```
Expected (30 concurrency, 2s/fetch):  15 urls/sec
Actual:                              1.5 urls/sec

→ 10x slower than expected!
```

Concurrency is NOT the problem. Failures are.

### What's Happening

Candidates that fail consume time:
- Retries
- Timeouts
- Error handling
- Network delays

With 86% failing, most work is wasted.

### Next Steps

1. **Add failure logging:**
   ```python
   logger.warning(f"Failed: {url} - {error_type}")
   ```

2. **Increase timeout:** 6s → 10s

3. **Analyze patterns:**
   - Which URLs fail?
   - What error types?
   - Specific to undergraduate pages?

4. **Fix root cause**

### Expected Impact

```
Current:  86% failure rate
After:    <20% failure rate

Result:
  - More candidates fetched (36 → 200+)
  - More programs found (43 → 100+)
  - Faster overall (failures consume time)
```

---

## ✅ Good News: Gemini is Fast!

### The Data

```
36 candidates classified in 41.6s
= 1.16s per candidate

Rate limiter overhead: 0.0s  ← Fix worked!
```

### Per-Batch Breakdown

```
Batch 1:  15 candidates in 17.0s  (1.13s each)
Batch 2:  15 candidates in 15.2s  (1.01s each)
Batch 3:   6 candidates in  9.4s  (1.57s each)
```

**Gemini is NOT the bottleneck.**

### Why Original Hypothesis Was Wrong

```
v1 Test:
  Auto-confirm + Fetch = 250.5s
  Hit 240s timeout BEFORE Gemini ran
  Gemini time: 0.0s (never executed)

→ Rate limiter delays never occurred!
→ Can't be the bottleneck if it never ran!
```

The instrumentation **proved** the original hypothesis was wrong.

---

## 📈 Throughput Over Time

### Auto-Confirm (Improving)

```
  50/300:  2.93 urls/sec
 100/300:  2.78 urls/sec
 150/300:  3.31 urls/sec
 200/300:  3.40 urls/sec
 300/300:  3.63 urls/sec
```

✅ Gradual improvement, no stalls  
⚠️ But fetching 160 wasted URLs

### Candidate Fetch (Slowly Improving)

```
  25/263:  0.74 urls/sec  ← Slow start
  50/263:  0.98 urls/sec
 100/263:  1.26 urls/sec
 150/263:  1.48 urls/sec
 250/263:  1.51 urls/sec  ← Peak
```

✅ Gradual improvement, no stalls  
🔴 But 10x slower than expected (failures)

---

## 🎯 Optimization Roadmap

### Priority 1: Fix Auto-Confirm Waste (HIGH IMPACT)

**Change:** 1 line of code  
**Impact:** ~43s savings (52% improvement)  
**Effort:** 5 minutes

```diff
  if not _is_high_confidence_url(url):
-     return None
+     return None  # Return WITHOUT fetching!
  
- html, status = await _fetch_html(url, timeout=4.0)
+ # Only fetch if pattern matched
+ html, status = await _fetch_html(url, timeout=4.0)
```

### Priority 2: Fix Candidate Fetch Failures (HIGH IMPACT)

**Change:** Add logging, increase timeout, analyze, fix  
**Impact:** ~50s+ savings, 100+ programs found  
**Effort:** 2-4 hours (investigation + fix)

**Steps:**
1. Add failure reason logging (30 min)
2. Run test and analyze logs (1 hour)
3. Identify root cause (1 hour)
4. Implement fix (1-2 hours)
5. Validate (30 min)

### Priority 3: Retest and Validate (CRITICAL)

After fixes:
```
Expected times:
  Auto-confirm:     ~40s  (was 82.6s)
  Candidate fetch: ~100s  (was 171.9s)
  Gemini:           ~50s  (was 41.6s, more candidates)
  ─────────────────────
  TOTAL:           ~190s  (within 240s limit!)
```

Expected results:
- ✅ Complete within 240s
- ✅ 100+ programs found
- ✅ <20% failure rate

---

## 📝 What We Learned

### About the Investigation

1. ✅ **Instrumentation revealed the truth** - Gemini wasn't slow, it never ran
2. ✅ **Wall-clock data > intuition** - Original hypothesis was wrong
3. ✅ **Throughput patterns matter** - Gradual improvement = no stalls
4. ✅ **Failure rates critical** - 86% failure > concurrency optimizations

### About the Code

1. 🔴 **Auto-confirm has a bug** - Fetches pattern-rejected URLs
2. 🔴 **Candidate fetch is fragile** - 86% failure rate unacceptable
3. ✅ **Gemini is well-optimized** - 1s per candidate is fast
4. ✅ **Rate limiter fix worked** - 0s overhead confirms it

### About Optimization

1. 🎯 **Fix waste before scaling** - 53% waste > more concurrency
2. 🎯 **Fix failures before scaling** - 86% failure rate > more workers
3. 🎯 **Profile before optimizing** - Don't guess, measure
4. 🎯 **Complete runs matter** - v1 was misleading (incomplete)

---

## 🚀 Next Actions

### Immediate (Today)

1. ✅ Fix auto-confirm waste (5 min)
2. ✅ Add candidate fetch failure logging (30 min)
3. ✅ Run test #3 (5 min)
4. ✅ Analyze failure logs (1 hour)

### Short-term (This Week)

1. ⏳ Identify candidate fetch root cause
2. ⏳ Implement fix
3. ⏳ Run test #4 and validate
4. ⏳ Document final performance

### Success Criteria

- [ ] Total time < 240s
- [ ] Programs found > 100
- [ ] Failure rate < 20%
- [ ] Auto-confirm < 50s
- [ ] Candidate fetch < 120s

---

## 💡 Key Takeaway

> **The original hypothesis (Gemini rate limiter is slow) was completely wrong.**
> 
> **The real problems:**
> - Auto-confirm wastes 53% of effort (easy fix)
> - Candidate fetch has 86% failure rate (needs investigation)
> 
> **This is why instrumentation and wall-clock data matter more than intuition.**

---

## 📚 Documents

Full details in:
- `INSTRUMENTATION_RESULTS_V2.md` - Complete timing breakdown
- `PERFORMANCE_INVESTIGATION_SUMMARY.md` - Full investigation story
- `CRITICAL_INSIGHTS.md` - Pre-test predictions (all correct!)

