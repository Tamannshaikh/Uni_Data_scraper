# Guide: Interpreting the New Timing Logs

## Quick Reference

When you run a discovery test, you'll now see detailed timing breakdowns. Here's how to interpret them.

## Stage 3 Timing Logs

### 1. Auto-Confirmation Phase
```
[program_discovery] Stage 3: 75 auto-confirmed, 140 need Gemini (auto-confirm took 12.3s)
```

**What it means:**
- 75 URLs matched high-confidence patterns and were confirmed without Gemini
- 140 URLs need Gemini classification
- Took 12.3 seconds to fetch and validate the auto-confirmed URLs

**What's good:**
- ✅ Auto-confirm phase < 20s
- ✅ High auto-confirm rate (>40%)
- ✅ Time scales with number of candidates (~0.1-0.2s per URL with concurrency)

**Red flags:**
- ⚠️ Auto-confirm taking >30s for <200 candidates (network issues or sequential fetching)
- ⚠️ Auto-confirm rate <30% (patterns too conservative)

---

### 2. Candidate Fetch Phase
```
[program_discovery] Stage 3: 140/155 candidates fetched for Gemini in 18.7s
```

**What it means:**
- Fetched 140 candidate pages successfully (15 failed)
- Took 18.7 seconds to fetch all pages in parallel
- Each candidate gets: title, snippet, confidence score

**What's good:**
- ✅ Fetch phase < 30s for ~150 candidates
- ✅ High success rate (>90%)
- ✅ Time scales with candidates (~0.1-0.2s per URL)

**Red flags:**
- ⚠️ Taking >40s for ~150 candidates (network issues or sequential)
- ⚠️ Low success rate (<80% fetched)

---

### 3. Gemini Classification Phase

#### Per-Batch Logs
```
[program_discovery] Rate limiter: 2 calls in last 60s, wait=0.0s
[program_discovery] Gemini API call: 16.2s (rate_limit_wait: 0.0s)
[program_discovery] Gemini batch 1: 12 candidates classified in 16.5s (API call: 16.2s)
```

**What it means:**
- Rate limiter checked: 2 calls in last 60s → no wait needed
- Actual API call took 16.2s
- Total batch time was 16.5s (includes API + parsing)

**What's good:**
- ✅ API call time ≈ batch time (minimal overhead)
- ✅ No rate limit waits for first 3 batches
- ✅ Batch 4+ shows reasonable wait times (~20-30s)

**Red flags:**
- ⚠️ Batch time >> API time (e.g., 40s batch for 15s API call)
- ⚠️ Rate limit wait on batch 1-3 (should be 0s)
- ⚠️ Rate limit wait >60s (shouldn't happen with 3 RPM)

---

### 4. Final Breakdown
```
[program_discovery] Stage 3 timing breakdown:
  auto_confirm=12.3s,
  candidate_fetch=18.7s,
  gemini_phase=52.3s (gemini_api=49.8s),
  total=83.3s
```

**What it means:**
- Auto-confirm: 12.3s
- Candidate fetch: 18.7s
- Classification: 52.3s total (49.8s in actual API calls)
- Wall clock: 83.3s

**Accounted time:**
```
12.3s + 18.7s + 52.3s = 83.3s
```

**What's good:**
- ✅ Accounted time ≈ total time (<10s difference)
- ✅ Gemini API time ≈ gemini phase time (minimal overhead)
- ✅ Total time < 120s for ~200 candidates

**Red flags:**
- ⚠️ Large overhead (total - accounted > 20s)
- ⚠️ Gemini phase >> gemini API time (hidden delays)

---

### 5. Overhead Warnings
```
[program_discovery] Stage 3: 45.2s unaccounted overhead detected 
  (total=180.5s, accounted=135.3s)
```

**What it means:**
- 45 seconds are unaccounted for in the timing breakdown
- Something is taking time that isn't being measured

**Possible causes:**
- Sequential operations that should be parallel
- Hidden sleep() calls
- Lock contention (semaphores blocking)
- Logging overhead (unlikely but possible)
- Network connection setup time

---

## Example: Good Run

```
[program_discovery] Stage 3: 80 auto-confirmed, 135 need Gemini (auto-confirm took 14.2s)
[program_discovery] Stage 3: 135/140 candidates fetched for Gemini in 19.3s
[program_discovery] Rate limiter: 0 calls in last 60s, wait=0.0s
[program_discovery] Gemini API call: 15.8s (rate_limit_wait: 0.0s)
[program_discovery] Gemini batch 1: 12 candidates classified in 16.1s (API call: 15.8s)
[program_discovery] Rate limiter: 1 calls in last 60s, wait=0.0s
[program_discovery] Gemini API call: 14.2s (rate_limit_wait: 0.0s)
[program_discovery] Gemini batch 2: 12 candidates classified in 14.5s (API call: 14.2s)
[program_discovery] Rate limiter: 2 calls in last 60s, wait=0.0s
[program_discovery] Gemini API call: 16.5s (rate_limit_wait: 0.0s)
[program_discovery] Gemini batch 3: 12 candidates classified in 16.8s (API call: 16.5s)
[program_discovery] Rate limiter: 3 calls in last 60s, wait=23.4s
[program_discovery] Sleeping 23.4s for rate limit
[program_discovery] Gemini API call: 15.1s (rate_limit_wait: 23.4s)
[program_discovery] Gemini batch 4: 12 candidates classified in 38.7s (API call: 15.1s)

[program_discovery] Stage 3 timing breakdown:
  auto_confirm=14.2s,
  candidate_fetch=19.3s,
  gemini_phase=86.1s (gemini_api=61.6s),
  total=119.6s
```

**Analysis:**
- ✅ First 3 batches: No rate limiting (as expected)
- ✅ Batch 4: Waited ~23s (correct for rolling window)
- ✅ Total time: 119.6s for 215 candidates
- ✅ Minimal overhead: 119.6 - (14.2 + 19.3 + 86.1) = 0s
- ✅ **This is optimal performance!**

---

## Example: Problem Run (Before Fix)

```
[program_discovery] Stage 3: 75 auto-confirmed, 140 need Gemini (auto-confirm took 15.1s)
[program_discovery] Stage 3: 140/155 candidates fetched for Gemini in 21.2s
[program_discovery] Rate limiter: 0 calls in last 60s, wait=0.0s
[program_discovery] Gemini API call: 16.2s (rate_limit_wait: 20.0s)  ⚠️
[program_discovery] Gemini batch 1: 12 candidates classified in 46.2s (API call: 16.2s)  ⚠️
[program_discovery] Rate limiter: 1 calls in last 60s, wait=0.0s
[program_discovery] Gemini API call: 15.8s (rate_limit_wait: 20.0s)  ⚠️
[program_discovery] Gemini batch 2: 12 candidates classified in 45.8s (API call: 15.8s)  ⚠️
[program_discovery] Rate limiter: 2 calls in last 60s, wait=0.0s
[program_discovery] Gemini API call: 16.0s (rate_limit_wait: 20.0s)  ⚠️
[program_discovery] Gemini batch 3: 12 candidates classified in 46.0s (API call: 16.0s)  ⚠️
Hit time limit (240.0s) after 3 Gemini calls...

[program_discovery] Stage 3 timing breakdown:
  auto_confirm=15.1s,
  candidate_fetch=21.2s,
  gemini_phase=138.0s (gemini_api=48.0s),  ⚠️
  total=174.3s  ⚠️
```

**Problems identified:**
- ⚠️ Each batch taking 46s but API only 16s (30s overhead!)
- ⚠️ Rate limit wait showing 20s even when RPM < 3
- ⚠️ Gemini phase: 138s total but only 48s in API calls (90s wasted!)
- ⚠️ This is the OLD behavior with _MIN_CALL_GAP

---

## Quick Diagnostic Checklist

| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| Auto-confirm > 30s | Sequential fetching or network issues | Check semaphore, increase concurrency |
| Candidate fetch > 40s | Sequential fetching or network issues | Check semaphore, increase concurrency |
| Rate limit wait on batch 1-3 | Bug in rate limiter | Check _enforce_rpm_limit() |
| Batch time >> API time | Hidden delays | Check for sleep(), locks, sequential ops |
| Large unaccounted overhead | Mystery delays | Add more instrumentation |
| Total time > 180s | Multiple issues | Check all above + consider batch size |

---

## Optimization Targets

Based on your logs, here are good targets:

| Metric | Target | Stretch Goal |
|--------|--------|--------------|
| Auto-confirm phase | < 20s | < 15s |
| Candidate fetch phase | < 30s | < 20s |
| Gemini API per batch | 12-18s | 10-15s (API dependent) |
| Gemini phase overhead | < 10% | < 5% |
| Total Stage 3 | < 120s | < 90s |
| Unaccounted overhead | < 10s | < 5s |

---

## Rate Limiter Behavior (Expected)

| Batch | Calls in Last 60s | Wait Time | Explanation |
|-------|-------------------|-----------|-------------|
| 1 | 0 | 0s | Under limit, proceed immediately |
| 2 | 1 | 0s | Under limit, proceed immediately |
| 3 | 2 | 0s | Under limit, proceed immediately |
| 4 | 3 | 20-30s | At limit, wait for oldest to age out |
| 5 | 3 | 15-25s | At limit, wait for oldest to age out |

**Note:** Wait times decrease as older requests age out of the 60s window.
