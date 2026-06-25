# Current Project Status

**Last Updated**: 2026-06-25  
**Phase**: Data Onboarding (architecture frozen)

---

## Summary

✅ **Architecture validated and frozen**  
✅ **Test harness fixed (no silent failures)**  
✅ **4 universities working at 100% precision**  
✅ **Ready to scale**

---

## Working Universities

| University | Strategy | Programs | Status |
|---|---|---|---|
| Arkansas | anchor | 10 | ✅ PASS |
| MIT | table | 46 | ✅ PASS |
| Purdue | heading | 190 | ✅ PASS |
| UCSD | plain_text_list | 186 | ✅ PASS |
| Stanford | playwright_table | — | ⏭️ SKIPPED |
| Manchester | playwright_anchor | — | ⏭️ SKIPPED |

**Total programs extracted**: 432  
**Junk rate**: 0%

---

## Test Harness Status

### Regression Suite: `regression_test.py`

**Checks**:
1. ✅ Strategy is implemented (SKIPPED if not)
2. ✅ Minimum program count met
3. ✅ Known programs present (catches substitution)
4. ✅ No forbidden phrases (catches junk)
5. ✅ Valid URLs

**Run**:
```bash
py -3.13 regression_test.py
```

**Current output**:
```
✅ 4 PASSED, 2 SKIPPED (strategies not implemented)
```

### Full Test Suite: `test_all_universities.py`

Prints every extracted program for manual verification.

**Run**:
```bash
py -3.13 test_all_universities.py
```

---

## Frozen Components (Do Not Modify)

### Extractors (`pipeline/extractors.py`)

Five strategies, all deterministic and structure-based:

1. **`extract_anchor`** — degree names in `<a>` tag text
2. **`extract_table`** — degree names in table cells (first column)
3. **`extract_heading`** — degree names in H2/H3 tags (with container scoping)
4. **`extract_plain_text_list`** — plain text list items with degree keywords
5. **`extract_heading_with_button`** — degree in heading, link in button (unused)

**Rule**: Do not modify unless a specific university breaks. Create variants (`extract_table_v2`) instead.

### Configuration (`UNIVERSITY_CONFIG.py`)

Manual classification per university:

```python
{
    "domain.edu": {
        "url": "https://...",
        "strategy": "anchor|table|heading|plain_text_list|...",
        "notes": "Human-readable description"
    }
}
```

**Rule**: No auto-detection. Manual inspection required.

---

## Recent Fixes (2026-06-25)

### 1. MIT Table Strategy
- **Before**: 8 programs with ~40% junk (deadline text, nav menus)
- **After**: 46 programs, 0% junk
- **Fix**: Proper table extraction filtering linked rows vs. bold headers

### 2. Purdue Heading Strategy
- **Before**: 0 programs (wrong DOM selector)
- **After**: 190 programs, 0% junk
- **Fix**: Scoped to `program-card` divs instead of generic H2 tags

### 3. Test Harness Silent Failures
- **Before**: Stanford/Manchester showed "✅ PASS — 0 programs"
- **After**: "⏭️ SKIPPED — Strategy not implemented"
- **Fix**: Three-state status (PASS/FAIL/SKIPPED) + supported strategy allowlist

### 4. Dual Assertion Policy
- **Before**: Only checked count (missed substitution regressions)
- **After**: Count + known programs (catches shrinkage + substitution)
- **Fix**: `KNOWN_PROGRAMS` dict with must-be-present program names

---

## Documentation

### Architecture
- `ARCHITECTURE_FREEZE.md` — The contract (do not violate)
- `FIXES_SUMMARY.md` — MIT & Purdue fix details
- `EXTRACTION_STATUS.md` — Live extraction status

### Testing
- `TEST_HARNESS_FIXES.md` — Recent test improvements
- `ADDING_UNIVERSITIES.md` — Mandatory 11-step checklist

### Planning
- `SCALING_PLAN.md` — Batch 1-5 targets (50 universities)
- `CURRENT_STATUS.md` — This document

---

## Next Steps

### Immediate: Add 6 Universities (Batch 1)

Follow `ADDING_UNIVERSITIES.md` checklist for each:

1. **Arizona State** (anchor bucket test)
2. **Ohio State** (heading bucket test)
3. **Georgia Tech** (table bucket test)
4. **Carnegie Mellon** (table bucket test)
5. **University of Florida** (anchor bucket test)
6. **UCLA** (plain_text_list bucket test)

**Goal**: Validate that existing 4 strategies generalize to new universities.

**Time estimate**: 7-15 minutes per university = 42-90 minutes total

### Later: Playwright Universities

Only after Batch 1 is 100% validated:

7. **Stanford** (implement `playwright_table`)
8. **Manchester** (implement `playwright_anchor`)

**Why defer**: These require new infrastructure (Playwright extractors). Should not block progress on static-HTML universities.

---

## Workflow

### Daily Workflow (Per University)

```bash
# 1. Add to UNIVERSITY_CONFIG.py
vim UNIVERSITY_CONFIG.py

# 2. Add expectations to regression_test.py
vim regression_test.py

# 3. Run regression (will fail on new one, pass on existing)
py -3.13 regression_test.py

# 4. Print full output
py -3.13 test_all_universities.py > output.txt

# 5. READ EVERY LINE MANUALLY
vim output.txt

# 6. If clean: update minimum count
vim regression_test.py

# 7. Run regression again (should all pass)
py -3.13 regression_test.py

# 8. Commit
git commit -m "Add [University] - [strategy] - [N] programs"
```

### After Every 3-5 Universities

Run full regression and spot-check random programs to ensure no regressions crept in.

---

## Success Criteria (Per University)

A university is successfully added when:

1. ✅ Regression test shows `PASS`
2. ✅ Manual verification shows 0% junk
3. ✅ All previous universities still show `PASS`
4. ✅ Known programs confirmed present
5. ✅ Minimum count set reasonably (80% of actual)

Only commit when all 5 met.

---

## Key Lessons (From Debugging Journey)

### 1. Structure-Specific Beats Universal
4 different page structures, 4 different strategies, all at 100% precision. No universal extractor attempted.

### 2. Diagnosis → Implementation Gap Is Real
- MIT: Correctly diagnosed as table, but wrong extractor applied → 40% junk
- Purdue: Content confirmed in static HTML, but concluded "needs Playwright" → 0 programs

**Fix**: Build the extractor that matches the diagnosis, not the nearest existing tool.

### 3. Manual Verification Is Non-Negotiable

> "Found N programs" is not evidence.  
> Manual read-through is the highest-value validation step.

Every bug was caught by reading actual output, not by trusting counts.

### 4. Freeze Means Freeze
Resist improving extractors "just because". Stable code stays stable. Create variants for edge cases.

---

## Metrics

### Current
- **Universities**: 4 working, 2 deferred
- **Programs**: 432 extracted
- **Precision**: 100% (0% junk)
- **Extractors**: 5 strategies
- **Test coverage**: 100% (all universities in regression suite)

### Target (End of Week)
- **Universities**: 30+ working
- **Programs**: 5000+ extracted
- **Precision**: 100% (maintained)
- **Extractors**: 5-7 strategies (minor variants if needed)

### Target (Next Week)
- **Universities**: 50+ working (top tier complete)
- **Programs**: 10,000+ extracted
- **Precision**: 100% (maintained)

---

## Architecture Simplicity

Current system:
```
1. Find catalog URL (manual for first 50)
2. Fetch page (httpx or Playwright)
3. Choose extractor (manual classification)
4. Extract programs (deterministic, structure-based)
5. Regression test (automated assertions)
6. Manual verification (read all programs)
```

This is **dramatically simpler** than earlier versions:
```
cache → guess URLs → classify page → score confidence → 
regex extraction → link following → SerpAPI → SearXNG → 
fallback heuristics → validation → rescoring
```

The current system is maintainable, debuggable, and working.

---

## Red Flags (When to STOP)

### 🚨 Regression test fails on existing university
**Action**: You've introduced a bug. Revert and investigate.

### 🚨 New university extracts junk
**Action**: Do not proceed. Wrong URL? Wrong strategy? Missing filter?

### 🚨 New structure doesn't fit existing strategies
**Action**: Do not force-fit. Create new extractor variant or document for later.

### 🚨 Temptation to "improve" working extractor
**Action**: Don't. Stable code stays stable. Create variant instead.

---

## Contact / Questions

For questions about:
- Adding universities → See `ADDING_UNIVERSITIES.md`
- Test failures → See `TEST_HARNESS_FIXES.md`
- Architecture decisions → See `ARCHITECTURE_FREEZE.md`
- Scaling plan → See `SCALING_PLAN.md`

---

## Status: Ready to Scale

✅ Architecture frozen  
✅ Test harness robust  
✅ Documentation complete  
✅ Process codified  
✅ 4 universities validated  

**Next action**: Begin Batch 1 (Arizona State, Ohio State, Georgia Tech, Carnegie Mellon, Florida, UCLA)
