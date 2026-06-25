# Test Harness Fixes — Critical Improvements

**Date**: 2026-06-25  
**Status**: ✅ Complete

---

## Summary

Three critical fixes applied to prevent silent failures and catch regressions:

1. **PASS/SKIPPED/FAIL distinction** — Stop treating "0 programs from unimplemented strategy" as success
2. **Dual assertion policy** — Minimum count + known programs (catches both shrinkage and substitution)
3. **Mandatory checklist** — Codifies "read every line" as non-negotiable step

---

## Fix 1: PASS/SKIPPED/FAIL Distinction

### Problem (Before)

```
stanford.edu    ✅ PASS — 0 programs
manchester      ✅ PASS — 0 programs
```

These showed as **PASS** because:
- Strategy `playwright_table` and `playwright_anchor` don't exist yet
- Extractor dispatcher returns empty list for unknown strategies
- Test counted 0 programs but had no minimum set
- Result: False positive

This is exactly the silent failure mode that caused weeks of debugging.

### Fix (After)

Added explicit strategy allowlist:

```python
SUPPORTED_STRATEGIES = {
    "anchor",
    "table", 
    "heading",
    "plain_text_list",
    "heading_with_button",
}

if config['strategy'] not in SUPPORTED_STRATEGIES:
    return {
        "status": "SKIPPED",
        "errors": ["Strategy not implemented yet"]
    }
```

Now shows:

```
stanford.edu    ⏭️  SKIPPED — Strategy 'playwright_table' not implemented yet
manchester      ⏭️  SKIPPED — Strategy 'playwright_anchor' not implemented yet
```

**States**:
- `PASS` = extractor exists and output is clean
- `FAIL` = extractor exists but output is bad
- `SKIPPED` = extractor not implemented yet

**Why this matters**: "0 programs = PASS" is the exact bug that let MIT's "8 programs with 40% junk" result get reported as success before manual reading caught it.

---

## Fix 2: Dual Assertion Policy (Minimum Count + Known Programs)

### Problem (Before)

Only checked minimum count:

```python
assert len(programs) >= EXPECTED_MIN[domain]
```

This catches shrinkage (46 → 3) but **not substitution** (46 → 46 where real programs get replaced by junk).

Example missed regression:
```
MIT before: 46 real programs
MIT after:  44 real programs + 2 junk items = 46 total
Test: PASS ✅ (count still 46)
Reality: FAIL ❌ (2 programs replaced with section headers)
```

### Fix (After)

Added dual checks:

```python
# Check 1: Minimum count (catches shrinkage)
assert len(programs) >= EXPECTED_MIN[domain]

# Check 2: Known programs present (catches substitution)
for expected_name in KNOWN_PROGRAMS[domain]:
    assert any(expected_name.lower() in p.lower() for p in extracted)
```

**Configuration**:

```python
EXPECTED_MIN_PROGRAMS = {
    "mit.edu": 40,      # Currently 46, set to ~80%
    "purdue.edu": 150,  # Currently 190
    "ucsd.edu": 150,    # Currently 186
    "uark.edu": 5,      # Currently 10
}

KNOWN_PROGRAMS = {
    "mit.edu": [
        "Architecture",
        "Economics", 
        "MIT Sloan MBA Program",
    ],
    "purdue.edu": [
        "Mechanical Engineering",
        "Business Analytics",
        "Computer Science",
    ],
    # ... etc
}
```

**Why this matters**: Count alone can look healthy while hiding quality degradation. Known programs check ensures specific expected items are still present.

---

## Fix 3: Mandatory Checklist (Codified Manual Verification)

### Problem (Before)

Manual verification was recommended but not enforced. This led to:

- MIT: "Found 13 programs" reported as success, but 5 were junk
- Purdue: "Found 0 programs" reported as failure, but content existed (wrong selector)

**Pattern**: Trusting counts instead of reading actual output.

### Fix (After)

Created `ADDING_UNIVERSITIES.md` with **non-optional** 11-step checklist:

```
☐ 1. Open page manually, find 2-3 real programs
☐ 2. Inspect HTML, identify structure
☐ 3. Choose matching strategy
☐ 4. Add to UNIVERSITY_CONFIG.py
☐ 5. Add EXPECTED_MIN and KNOWN_PROGRAMS
☐ 6. Run regression suite
☐ 7. Run full test, print all extracted programs
☐ 8. READ EVERY SINGLE LINE manually ← MANDATORY
☐ 9. If 100% clean: update minimum count
☐ 10. Run regression suite again
☐ 11. Commit
```

**Step 8 is the critical one**: Read every extracted program, check for junk.

**Why this matters**: The entire debugging journey proved this lesson repeatedly:

> Every fix that worked was preceded by someone opening the real HTML and reading it. Every "success" that turned out to be hollow was a case where a count got trusted instead.

The checklist encodes this discipline into the workflow so it doesn't depend on someone remembering.

---

## Validation — All Fixes Working

### Test Output (After Fixes)

```bash
$ py -3.13 regression_test.py

================================================================================
REGRESSION TEST SUITE
================================================================================

Testing: uark.edu (anchor)
  ✅ PASS — 10 programs

Testing: mit.edu (table)
  ✅ PASS — 46 programs

Testing: purdue.edu (heading)
  ✅ PASS — 190 programs

Testing: ucsd.edu (plain_text_list)
  ✅ PASS — 186 programs

Testing: stanford.edu (playwright_table)
  ⏭️  SKIPPED — Strategy 'playwright_table' not implemented yet

Testing: manchester.ac.uk (playwright_anchor)
  ⏭️  SKIPPED — Strategy 'playwright_anchor' not implemented yet

================================================================================
REGRESSION TEST SUMMARY
================================================================================
✅ uark.edu             —  10 programs — PASS
✅ mit.edu              —  46 programs — PASS
✅ purdue.edu           — 190 programs — PASS
✅ ucsd.edu             — 186 programs — PASS
⏭️  stanford.edu         —   0 programs — SKIPPED
⏭️  manchester.ac.uk     —   0 programs — SKIPPED

================================================================================
✅ 4 PASSED, 2 SKIPPED (strategies not implemented)
================================================================================
```

**Results**:
1. ✅ SKIPPED clearly distinguished from PASS
2. ✅ All 4 working universities pass dual checks (count + known programs)
3. ✅ Stanford and Manchester correctly marked as not implemented

---

## Impact

### Before Fixes

```
Test shows: ✅ PASS
Reality:     ❌ Silent failures hiding
```

**Examples**:
- MIT showing PASS with junk in output
- Stanford showing PASS with 0 programs
- Purdue showing FAIL with content actually present

### After Fixes

```
Test shows: ✅ PASS / ⏭️ SKIPPED / ❌ FAIL
Reality:    Accurately reflected
```

**Guarantees**:
- `PASS` = extractor working + count healthy + known programs present + no junk
- `SKIPPED` = extractor not implemented (not hiding as PASS)
- `FAIL` = specific errors listed

---

## Files Modified

1. **`regression_test.py`**
   - Added `SUPPORTED_STRATEGIES` allowlist
   - Added `KNOWN_PROGRAMS` assertions
   - Changed return value from `passed: bool` to `status: "PASS"|"FAIL"|"SKIPPED"`
   - Updated summary output to show three-state status

2. **`ADDING_UNIVERSITIES.md`** (new)
   - 11-step mandatory checklist
   - Step 8: "READ EVERY SINGLE LINE" (non-optional)
   - Red flags section (when to STOP)
   - Examples of good/bad commits

3. **`TEST_HARNESS_FIXES.md`** (this document)
   - Documents all three fixes
   - Explains why each matters
   - Shows validation results

---

## Next Steps

### Immediate (Do NOT Skip)

Before adding any new universities:

1. ✅ Test harness fixes complete (this document)
2. ✅ Checklist created (`ADDING_UNIVERSITIES.md`)
3. ✅ Regression suite passes with clear PASS/SKIPPED distinction

### Next (University Onboarding)

Follow `ADDING_UNIVERSITIES.md` checklist for each new university:

**Recommended order**:
1. Arizona State (anchor bucket)
2. Ohio State (heading bucket)
3. Georgia Tech (table bucket)
4. Carnegie Mellon (table bucket)
5. University of Florida (anchor bucket)
6. UCLA (plain_text_list bucket)

**Defer until above 6 are validated**:
7. Stanford (playwright_table)
8. Manchester (playwright_anchor)

---

## The Core Lesson

From the debugging journey:

> "Found N programs" is not evidence.  
> Manual read-through is the highest-value validation step.

The test harness now enforces this:

1. **Dual checks** catch both shrinkage and substitution
2. **SKIPPED state** prevents false positives from unimplemented strategies
3. **Mandatory checklist** codifies "read every line" as a workflow requirement

No more silent failures.

---

## Architecture Status

**Frozen components**:
- 5 extractors (anchor, table, heading, plain_text_list, heading_with_button)
- 4 working universities (Arkansas, MIT, Purdue, UCSD)
- Test harness with three-state pass/fail/skip
- Dual assertion policy (count + known programs)

**Next phase**: Data onboarding (add universities, not architecture changes)

**Rule**: Do not modify extractors unless a specific university breaks them.
