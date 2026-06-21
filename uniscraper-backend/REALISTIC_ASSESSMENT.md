# Realistic Multi-University Assessment

**Date**: June 21, 2026  
**Status**: ⚠️ Manchester production-ready, cross-university generalization needs work

---

## Corrected Classification

| University | Technical | Product | Verdict |
|-----------|-----------|---------|---------|
| Manchester | ✅ Success | ✅ Success | **READY** |
| Arkansas | 🔧 Bug fixed | ❌ Fail | **NOT READY** |
| Edinburgh | ⚠️ Graceful | ❌ Fail (0 programs) | **NOT READY** |
| MIT | ⚠️ Graceful | ❌ Fail (0 programs) | **NOT READY** |

**Reality check**: 1/4 universities returned usable results  
**Product success rate**: 25% (not 75%)

---

## What "Graceful Failure" Actually Means

### Edinburgh (0 programs)
```
403 Forbidden on all sitemaps
Fell back to SerpAPI → 20 URLs
After filtering → 8 candidates
Skipped Gemini (< 15 threshold)
Result: 0 programs
```

**This is graceful error handling, but NOT success.**  
User asks "Find Edinburgh programs" → Gets nothing → Product failure.

### MIT (0 programs)
```
404 on all sitemaps
Fell back to SerpAPI → 20 URLs
After filtering → 13 candidates
Skipped Gemini (< 15 threshold)
Result: 0 programs
```

**Same story.** Didn't crash, but returned nothing useful.

---

## The Arkansas Pattern Problem

### Manchester (the outlier)
```
584 candidates checked
574 pattern matched (98.3%)
568 auto-confirmed
16 Gemini candidates
```

**Architecture**: Slug → Pattern → Fetch → Gemini  
**Gemini usage**: 2.7% of candidates  
**This is the ideal case.**

### Arkansas (the norm?)
```
411 candidates checked
54 pattern matched (13.1%)
43 auto-confirmed
368 Gemini candidates (89.5%)
```

**Architecture**: Gemini-heavy (opposite of Manchester)  
**Gemini usage**: 89.5% of candidates  
**This suggests pattern matching is Manchester-specific.**

---

## Why Arkansas Is So Slow

### Breakdown
```
Phase 1 - Auto-confirm:     17.6s
Phase 2 - Candidate fetch: 131.2s  ← 68% of runtime
Phase 3 - Gemini classify:  44.9s
Total:                     193.8s
```

### The 131-second bottleneck
```
368 requests
329 failed (89% failure rate)
avg=8.12s/URL
```

**Problem**: Content extraction is failing massively.  
**Evidence**: `HTTP 200 OK` followed by `no_content (status=0)`

This is NOT a network issue. It's either:
1. Crawl4AI can't parse Arkansas HTML structure
2. Content validation is too strict
3. Markdown extraction is failing

---

## The Sibling Expansion Waste

Arkansas discovered:
```
52 programs confirmed (Stage 3)
391 sibling candidates launched (Stage 4)
```

**But the cap is 500 programs.**

With 52 already found, launching 391 more candidates is excessive.

### Recommended guard
```python
# Before Stage 4
if len(confirmed) >= max_programs * 0.2:  # 20% threshold
    logger.info(f"Skipping sibling expansion: {len(confirmed)} programs already exceed 20% of cap")
    skip_sibling_expansion = True
```

For `max_programs=500`:
- If confirmed ≥ 100 → skip sibling expansion
- Sibling expansion is for recall boost, not primary discovery

---

## Pattern Generalization Gaps

### Manchester patterns work for:
```
/postgraduate/taught/courses/msc-program-name/
/postgraduate-research/programmes/phd-program-name/
```

### Arkansas patterns DON'T work for:
```
/programs/ma-in-history.html
/programs/ms-in-engineering-management.html
/programs/phd-in-molecular-biosciences.html
```

**Evidence**: Only 9 slug confirmations (vs Manchester's 538)

### Missing patterns
The slug detector should recognize:
- `ma-in-`, `ms-in-`, `msc-in-`
- `mba-`, `mfa-`, `mph-`
- `dnp-`, `edd-`, `dba-`
- `phd-in-`, `doctorate-`
- `graduate-certificate-`, `post-masters-`

**Current**: Optimized for Manchester-style slugs  
**Needed**: Broader pattern vocabulary

---

## The "95% Faster" Claim Needs Context

### What we actually know:
```
Manchester: 64.9s (baseline was 600s+)
Arkansas:   318.5s (no baseline given)
```

**If Arkansas is typical**, many universities might take 300s+, not 65s.

### What we need to verify:
1. Is Manchester the exception or the norm?
2. What % of universities have rich sitemaps like Manchester?
3. What % block bots like Edinburgh?
4. What % have distributed structures like MIT?

**Without this data, "95% faster" is premature.**

---

## What "Production-Ready" Actually Means

### Current state:
✅ **Production-ready for Manchester-like universities**:
- Rich sitemap
- Consistent URL patterns
- Predictable structure

❌ **NOT production-ready for**:
- Bot-protected sites (Edinburgh)
- Distributed structures (MIT)
- Different URL conventions (Arkansas patterns work poorly)

---

## Immediate Actions (Priority Order)

### 1. Re-run Arkansas with bug fix (5 minutes)
**Expected**: Should complete successfully now  
**Measure**: How many programs actually discovered?  
**Goal**: Verify tuple fix works

### 2. Expand slug patterns (30 minutes)
Add to `_has_obvious_degree_slug()`:
```python
BROAD_DEGREE_PATTERNS = [
    r'/ma-in-',
    r'/ms-in-',
    r'/msc-in-',
    r'/mba-',
    r'/mfa-',
    r'/mph-',
    r'/mres-',
    r'/llm-',
    r'/dnp-',
    r'/edd-',
    r'/dba-',
    r'/phd-in-',
    r'/doctorate-',
    r'/grad-cert-',
    r'/graduate-certificate-',
    r'/post-masters-',
    r'/post-baccalaureate-',
]
```

**Expected impact**: Arkansas slug confirmations: 9 → 200+

### 3. Add early-stop for sibling expansion (15 minutes)
```python
# After Stage 3
if len(confirmed) >= max_programs * 0.2:
    logger.info(f"[program_discovery] Skipping sibling expansion: {len(confirmed)} programs already found")
else:
    siblings_result = await sibling_expansion(...)
```

**Expected impact**: Save 100+ seconds on Arkansas-like universities

### 4. Investigate Arkansas extraction failures (60 minutes)
**Problem**: 329/368 URLs returning `no_content` despite `200 OK`  
**File**: `pipeline/fetcher.py` or `utils/crawl4ai_client.py`  
**Debug**:
- Pick 5 failed Arkansas URLs
- Test Crawl4AI extraction manually
- Check if content validation is too strict
- Test with different extraction methods

---

## Longer-Term Actions

### 1. Test 10-20 more universities (2-3 hours)
Sample universities with different characteristics:
- **Sitemap-rich**: Oxford, Cambridge, Stanford, Berkeley
- **Bot-protected**: Imperial, UCL, Edinburgh, LSE
- **Distributed**: Harvard, Yale, Princeton, MIT
- **State schools**: Various US state universities

**Measure for each**:
- Discovery time
- Programs found
- Gemini candidate %
- Extraction failure rate

### 2. Add fallback strategies for non-sitemap universities
**For bot-protected (Edinburgh)**:
- Playwright-based crawling
- Degree finder page extraction
- Navigation menu parsing

**For distributed structures (MIT)**:
- Multi-subdomain crawling (programs.mit.edu, admissions.mit.edu, etc.)
- School-specific entry points
- Department directory mining

### 3. Benchmark and set realistic expectations
Don't claim "95% faster" until you have:
- 20+ university test results
- Median time (not just best case)
- Success rate (% returning >100 programs)

---

## What We Can Claim Right Now

### Accurate claims:
✅ Manchester discovery is production-ready (64.9s, 500 programs, 98% auto-confirm)  
✅ Slug-based auto-confirmation works brilliantly when patterns match  
✅ 96% reduction in Gemini calls (200+ → 16) for Manchester  
✅ Architecture is sound (Slug → Pattern → Fetch → Gemini)  
✅ Graceful error handling (no crashes on 403s, 404s, extraction failures)  
✅ Configurable parameters (max_programs, skip_gemini, etc.)

### Premature claims:
❌ "Discovery pipeline is production-ready" (only true for Manchester-like universities)  
❌ "95% faster" (only measured on Manchester)  
❌ "Generalizes across universities" (3/4 failed to return programs)  
❌ "Cross-university validation successful" (25% success rate, not 75%)

---

## Revised Recommendation

### Current status:
**Manchester discovery**: ✅ Freeze and deploy  
**Cross-university discovery**: ⚠️ Needs more work

### Next milestone:
**Goal**: 10/10 universities return >100 programs in <120s  
**Deadline**: After slug pattern expansion + extraction fixes

### Actions:
1. ✅ Fix Arkansas bug (done)
2. 🔄 Re-run Arkansas test
3. 🔄 Expand slug patterns
4. 🔄 Add sibling expansion guard
5. 🔄 Fix extraction failures
6. 🔄 Test 10 more universities
7. ⏳ THEN claim production-ready

---

## Bottom Line

**Manchester is a huge win.** The optimizations work beautifully.

**But Manchester might be the best-case scenario**, not the typical case.

Before calling discovery "done":
1. Fix Arkansas extraction (89% failure rate)
2. Expand pattern vocabulary (9 slug confirmations → 200+)
3. Add early-stop guards (waste less time)
4. Test 10-20 more universities
5. Measure median performance, not best case

**Once we have 10/10 universities succeeding**, then we can confidently claim:
> "Discovery pipeline is production-ready and generalizes across university structures."

Right now, the honest claim is:
> "Discovery pipeline is production-ready for sitemap-rich universities with Manchester-style URL patterns. Cross-university robustness is in progress."

**That's still a massive achievement.** Just being realistic about scope.
