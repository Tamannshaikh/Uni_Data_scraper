# Scaling Plan — Batch 1 (10 Universities)

**Status**: Ready to onboard  
**Goal**: Validate extractor buckets generalize beyond the initial 4

---

## Current State

✅ **4 universities working** (Arkansas, MIT, Purdue, UCSD)  
✅ **Regression suite in place** (`regression_test.py`)  
✅ **Architecture frozen** (no extractor modifications unless university breaks)

**Next bottleneck**: Finding the right catalog URL (not extraction quality)

---

## Batch 1 Target Universities

### Anchor Bucket (3 universities)
Test if Arkansas pattern holds across other state schools.

1. ✅ **Arkansas** (done) — 10 programs
2. **Arizona State** — https://degrees.apps.asu.edu/masters-phd
3. **University of Florida** — https://catalog.ufl.edu/graduate/
4. **Texas A&M** — https://catalog.tamu.edu/graduate/

### Table Bucket (3 universities)
Test if MIT pattern holds across other table-based catalogs.

1. ✅ **MIT** (done) — 46 programs
2. **Carnegie Mellon** — https://www.cmu.edu/graduate/programs/index.html
3. **Georgia Tech** — https://grad.gatech.edu/degree-programs

### Heading Bucket (3 universities)
Test if Purdue pattern holds across other program-card style pages.

1. ✅ **Purdue** (done) — 190 programs
2. **Ohio State** — https://gradsch.osu.edu/graduate-programs
3. **Michigan State** — https://grad.msu.edu/programs

### Playwright Bucket (1 university)
Test if Stanford needs Playwright, and if so, whether existing extractors work post-fetch.

1. **Stanford** — https://applygrad.stanford.edu/portal/programs (currently configured, not tested)

**Total Batch 1**: 10 universities (4 done + 6 new)

---

## Process Per University

### Step 1: Manual Inspection (2 minutes)

1. Open catalog page in browser
2. Find 2-3 known programs (e.g., "Computer Science MS", "MBA")
3. Right-click → Inspect → examine HTML around program names
4. Answer:
   - Is degree name in `<a>` text? → `anchor`
   - In `<li>` plain text? → `plain_text_list`
   - In table cell? → `table`
   - In `<h2>` with container class? → `heading`
   - Page blank until JS runs? → `playwright_*`

### Step 2: Add to Config (30 seconds)

```python
# In UNIVERSITY_CONFIG.py
"newdomain.edu": {
    "url": "https://newdomain.edu/programs",
    "strategy": "anchor",  # Based on Step 1
    "notes": "Clean anchor list, typical state school catalog"
}
```

### Step 3: Run Regression Test (1 minute)

```bash
py -3.13 regression_test.py
```

Expected:
- ✅ All previous universities still pass
- ❌ New university fails (no minimum set yet)

### Step 4: Run Full Test with Output (1 minute)

```bash
py -3.13 test_all_four_universities.py
```

(Rename to `test_all_universities.py` — it tests all configured, not just 4)

### Step 5: Manual Verification (2 minutes)

Read every extracted program. Check for:
- Real degree/program names only
- No junk ("Follow Us", deadline text, nav menus)
- No duplicates
- URLs look valid

If junk appears:
- Identify why (wrong container? wrong tag? missing filter?)
- Either:
  - Adjust config (e.g., different URL)
  - Add filter to extractor (if same structure, edge case)
  - Create new extractor variant (if fundamentally different)

### Step 6: Set Minimum & Commit (30 seconds)

```python
# In regression_test.py
EXPECTED_MIN_PROGRAMS = {
    "newdomain.edu": 80,  # Set to ~80% of actual count
    # ...
}
```

Run regression test again — should pass.

**Total time per university**: ~7 minutes if smooth, ~15 minutes if debugging needed

---

## Expected Outcomes

### Scenario A: Buckets Generalize (Best Case)

All 6 new universities fit into existing extractors:
- Arizona State, Florida, Texas A&M → `anchor`
- Carnegie Mellon, Georgia Tech → `table`
- Ohio State, Michigan State → `heading`
- Stanford → `playwright_table` (Playwright fetch → `table` extract)

**Result**: Batch 1 complete, ready for Batch 2 (next 10)

### Scenario B: 1-2 Edge Cases (Likely)

Most universities fit existing buckets, but 1-2 need minor variants:
- Example: `table_variant` for slightly different table structure
- Example: `heading_variant` for different container class

**Action**: Create new extractor function (e.g., `extract_table_v2`), test, freeze

**Result**: 5-6 extractors total, still manageable

### Scenario C: New Structure Discovered (Possible)

One university has genuinely novel structure not covered by buckets.

**Action**: 
1. Inspect HTML carefully
2. Identify structural pattern
3. Create new extractor (e.g., `extract_accordion`)
4. Test, document, freeze
5. New bucket created

**Result**: 6-7 extractors, architecture still simple

### Scenario D: Wrong URL (Common)

University configured with wrong catalog page (e.g., undergraduate programs, course catalog instead of degree catalog, 404 page).

**Action**:
1. Google: `"[university name]" graduate programs catalog`
2. Find correct URL
3. Update config
4. Re-test

**Result**: No code changes, just config fix

---

## What NOT to Do

### ❌ Do Not Modify Existing Extractors for Edge Cases

If Carnegie Mellon's table has an extra column, do **not** change `extract_table()`. Create `extract_table_v2()`.

**Why**: Keep stable extractors stable. Generalization breaks things.

### ❌ Do Not Skip Manual Verification

Even if regression test passes, **read the actual programs**. Counts can lie (MIT showed this).

### ❌ Do Not Auto-Detect Strategy

No `classify_page()`. Human inspection is 2 minutes and 100% reliable.

### ❌ Do Not Add Generic Scoring

No "confidence: 0.85" or "quality_score: 7/10". Either 100% clean or broken.

---

## Regression Test as Safety Net

After each new university, run:

```bash
py -3.13 regression_test.py
```

This catches:
1. **Extraction breakage**: Program count drops below minimum
2. **Junk leakage**: Forbidden phrases appear
3. **URL issues**: Malformed links

If regression test fails on an **existing** university after adding a new one, you've introduced a bug. Roll back and investigate.

---

## Manual Catalog Curation

For top 50 universities, **manually finding catalog URLs is cheaper than automation**.

**Time estimate**:
- 50 universities × 2 minutes each = **100 minutes = 1.7 hours**

Compare to:
- Building discovery heuristics: weeks
- Debugging false positives: weeks
- Maintaining complex crawlers: ongoing

**Decision**: Manual curation for Batch 1-5 (first 50 universities). Re-evaluate if scaling to 500+.

---

## Batch 1 Success Criteria

1. ✅ All 10 universities pass regression test
2. ✅ Manual verification shows 0% junk for all
3. ✅ Extractors remain at 5-6 functions (max 7 if edge cases found)
4. ✅ Documentation updated with new patterns
5. ✅ Total time < 2 hours (including debugging)

If criteria met → proceed to Batch 2 (next 10 universities)

---

## Next Batches (Preview)

### Batch 2 (10 universities)
- More US state schools (anchor bucket)
- More research universities (table/heading buckets)
- More Playwright universities (Stanford pattern)

### Batch 3 (10 universities)
- UK universities (likely new buckets)
- Canadian universities (likely existing buckets)
- Australian universities (likely new buckets)

### Batch 4-5 (20 universities)
- Fill out top 50
- Mix of all buckets
- Focus on stability, not novelty

**Target**: 50 universities by end of week, all at 100% precision.

---

## Current System Simplicity

```
1. Find catalog URL (manual for first 50)
2. Fetch page (httpx or Playwright)
3. Choose extractor (manual classification)
4. Extract programs (deterministic, structure-based)
5. Regression test (automated assertions)
6. Manual verification (read all programs)
```

This is dramatically simpler than earlier:
```
cache → guess URLs → classify page → score confidence → 
regex extraction → link following → SerpAPI → SearXNG → 
fallback heuristics → validation → rescoring
```

The current system is maintainable, debuggable, and working.

---

## Files to Use

### Daily workflow
```bash
# Add university to config
vim UNIVERSITY_CONFIG.py

# Run regression (fails until minimum set)
py -3.13 regression_test.py

# Run full test with output
py -3.13 test_all_universities.py

# Read output manually, verify quality

# Set minimum in regression_test.py
vim regression_test.py

# Run regression again (should pass)
py -3.13 regression_test.py
```

### Documentation
- `ARCHITECTURE_FREEZE.md` — the contract (do not violate)
- `SCALING_PLAN.md` — this document (current batch plan)
- `EXTRACTION_STATUS.md` — live status (update after each batch)

---

## Start Now

Begin with **Arizona State**:

1. Open https://degrees.apps.asu.edu/masters-phd
2. Inspect one program's HTML
3. Classify structure (anchor? table? heading?)
4. Add to config
5. Test
6. Verify
7. Set minimum
8. Commit

Then **University of Florida**, then **Texas A&M**.

Once anchor bucket is validated (3 universities all working), move to table bucket (Carnegie Mellon, Georgia Tech).

**Goal for today**: Batch 1 complete (10 universities)  
**Goal for week**: Batch 1-3 complete (30 universities)  
**Goal for next week**: Batch 4-5 complete (50 universities)

The architecture is frozen. Time to scale.
