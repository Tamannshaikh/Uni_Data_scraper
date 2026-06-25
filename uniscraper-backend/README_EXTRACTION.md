# University Program Extraction System

**Status**: ✅ Architecture frozen, ready to scale  
**Current**: 4 universities, 432 programs, 0% junk  
**Next**: Add 6 universities (Batch 1)

---

## Quick Start

### Run Regression Test
```bash
py -3.13 regression_test.py
```

Expected output:
```
✅ 4 PASSED, 2 SKIPPED (strategies not implemented)
```

### Add New University

Follow **`ADDING_UNIVERSITIES.md`** checklist (11 steps).

**Critical steps**:
- Step 2: Inspect HTML manually
- Step 8: Read every extracted line
- Step 7b: Check 5 random URLs in browser

**Time**: 7-15 minutes per university

---

## System Architecture

### Extractors (Frozen)

Five deterministic, structure-based strategies:

| Strategy | When to Use | Example |
|---|---|---|
| `anchor` | Degree names in `<a>` text | Arkansas |
| `table` | Degree names in table cells | MIT |
| `heading` | Degree names in H2/H3 tags | Purdue |
| `plain_text_list` | Plain text bullets | UCSD |
| `heading_with_button` | Degree in heading, link in button | (unused) |

**Rule**: Do not modify unless broken. Create variants for edge cases.

### Configuration

Manual classification per university:

```python
UNIVERSITY_CONFIG = {
    "domain.edu": {
        "url": "https://...",
        "strategy": "anchor|table|heading|...",
        "notes": "Human-readable description"
    }
}
```

No auto-detection. Human inspection required (2 minutes).

### Testing

Two test suites:

1. **Regression test** (`regression_test.py`)
   - Checks: strategy implemented, min count, known programs, no junk, valid URLs
   - Run after every change
   - Must pass before commit

2. **Full test** (`test_all_universities.py`)
   - Prints all extracted programs
   - Manual verification required
   - Read every single line

---

## Working Universities

| University | Strategy | Programs | Notes |
|---|---|---|---|
| Arkansas | anchor | 10 | Degree names in anchor text |
| MIT | table | 46 | Table cells with links |
| Purdue | heading | 190 | H2 in program-card divs |
| UCSD | plain_text_list | 186 | Plain text bullets |

**Total**: 432 programs, 0% junk

### Deferred (Strategy Not Implemented)

| University | Strategy | Reason |
|---|---|---|
| Stanford | playwright_table | JS-rendered, defer until Batch 1 validated |
| Manchester | playwright_anchor | JS-rendered, defer until Batch 1 validated |

---

## Key Documents

### Must Read
- **`RULES.md`** ← Start here (10 core principles)
- **`ADDING_UNIVERSITIES.md`** ← Mandatory checklist
- **`ARCHITECTURE_FREEZE.md`** ← The contract

### Reference
- `CURRENT_STATUS.md` — Live status and metrics
- `TEST_HARNESS_FIXES.md` — Recent improvements
- `FIXES_SUMMARY.md` — MIT & Purdue fix details
- `SCALING_PLAN.md` — Batch targets

---

## The 10 Rules

1. **Freeze means freeze** — Do not modify working extractors
2. **Observation first** — Inspect HTML before making architecture decisions
3. **Manual verification** — Read every extracted line, every time
4. **Three-state status** — PASS/FAIL/SKIPPED (never "PASS — 0 programs")
5. **Dual assertions** — Count + known programs (catches shrinkage + substitution)
6. **No auto-detection** — Manual classification only
7. **Manual curation** — Find catalog URLs manually for first 50
8. **Regression suite** — Run after every change
9. **Checklist mandatory** — 11 steps, no shortcuts
10. **Defer hard cases** — Validate simple first

Full details: See `RULES.md`

---

## Next Steps

### Batch 1 (Next 6 Universities)

Follow `ADDING_UNIVERSITIES.md` for each:

1. **Arizona State** (test anchor bucket)
2. **Ohio State** (test heading bucket)
3. **Georgia Tech** (test table bucket)
4. **Carnegie Mellon** (test table bucket)
5. **University of Florida** (test anchor bucket)
6. **UCLA** (test plain_text_list bucket)

**Goal**: Validate existing strategies generalize to new universities.

**Time**: 42-90 minutes total (7-15 min each)

### Later (Playwright Universities)

Only after Batch 1 validated:

7. **Stanford** (implement playwright_table)
8. **Manchester** (implement playwright_anchor)

---

## Workflow

```bash
# Add to config
vim UNIVERSITY_CONFIG.py

# Add expectations
vim regression_test.py

# Test
py -3.13 regression_test.py
py -3.13 test_all_universities.py > output.txt

# READ EVERY LINE
vim output.txt

# Check 5 random URLs in browser
# (Step 7b in checklist)

# Update minimum if clean
vim regression_test.py

# Test again
py -3.13 regression_test.py

# Commit
git commit -m "Add [University] - [strategy] - [N] programs"
```

---

## Success Criteria (Per University)

Must be true before commit:

1. ✅ Regression test shows `PASS`
2. ✅ Manual verification shows 0% junk
3. ✅ All previous universities still `PASS`
4. ✅ Known programs present
5. ✅ Minimum count set (80% of actual)
6. ✅ 5 random URLs checked in browser

---

## Recent Fixes (2026-06-25)

### 1. MIT & Purdue Extraction
- **MIT**: 8 programs with 40% junk → 46 programs, 0% junk
- **Purdue**: 0 programs → 190 programs, 0% junk

### 2. Test Harness
- **PASS/FAIL/SKIPPED**: Three-state status prevents silent failures
- **Dual assertions**: Count + known programs catches more regressions
- **URL check**: Step 7b added to verify URLs point to real pages

Full details: See `FIXES_SUMMARY.md` and `TEST_HARNESS_FIXES.md`

---

## The Core Lesson

> The problem was never extraction quality.  
> The problem was applying the wrong extractor to the wrong page structure.

**Solution**: Observation-based classification + manual verification

**Process**:
```
Inspect HTML → Match strategy → Configure → Test → Read output → Commit
```

Simple. Deterministic. Working.

---

## Red Flags

### 🚨 Stop if:
- Regression test fails on existing university → You introduced a bug
- New university extracts junk → Wrong URL/strategy/filter
- Tempted to "improve" working extractor → Create variant instead
- Assuming structure without inspecting HTML → Inspect first, decide second
- Trusting count without reading output → Read every line

---

## Architecture Phase Is Over

**Current system**:
```
Find URL → Fetch → Extract → Test → Verify
```

**Do not add**:
- Auto-detection
- Confidence scoring
- Discovery crawlers
- LLM validation
- PageType classification

The system is simple, explainable, and working. Keep it that way.

**Next phase**: Data onboarding (add universities, not architecture)

---

## Status: Ready to Scale

✅ Architecture frozen  
✅ Test harness robust  
✅ Process codified  
✅ 4 universities validated  
✅ Documentation complete  

**Next action**: Follow `ADDING_UNIVERSITIES.md` starting with Arizona State

---

## Contact

For questions:
- General workflow → `RULES.md`
- Adding universities → `ADDING_UNIVERSITIES.md`
- Architecture decisions → `ARCHITECTURE_FREEZE.md`
- Test failures → `TEST_HARNESS_FIXES.md`

---

**The boring stage is good. Boring means working.**
