# Checklist for Adding Universities

**Follow this checklist for EVERY new university. No exceptions.**

This process takes ~7 minutes per university if smooth, ~15 minutes if debugging needed.

---

## Prerequisites

✅ Regression test passes for all existing universities:
```bash
py -3.13 regression_test.py
```

---

## Step-by-Step Checklist

### ☐ 1. Manual Page Inspection (2 minutes)

1. Open the university's graduate catalog page in browser
2. Find 2-3 known real program names (e.g., "Computer Science MS", "MBA", "Mechanical Engineering PhD")
3. Right-click one program → Inspect → examine HTML structure around it
4. Take note of the structure

**Example findings**:
- Degree name in `<a>` tag text → `anchor` strategy
- Degree name in `<li>` plain text → `plain_text_list` strategy  
- Degree name in table `<td>` → `table` strategy
- Degree name in `<h2>` with specific container class → `heading` strategy
- Page is blank until JavaScript runs → `playwright_*` strategy (DEFER — add to end of batch)

### ☐ 2. Choose Strategy (30 seconds)

Based on Step 1, select from:
- `anchor` — degree names in anchor text
- `table` — degree names in table cells
- `heading` — degree names in H2/H3 tags
- `plain_text_list` — degree names in plain text list items
- `heading_with_button` — degree name in heading, link in separate button

**If structure doesn't match any existing strategy**:

STOP. Before creating a new extractor, verify:
1. ☐ HTML has been inspected manually
2. ☐ All 5 existing extractors have been ruled out
3. ☐ The structure is proven fundamentally different

Common mistakes (do NOT create new extractor for these):
- ❌ Wrong DOM selector → fix selector in config
- ❌ Wrong container → inspect which container has programs
- ❌ Wrong URL → find correct catalog page

Only create new extractor variant if structure is genuinely novel (e.g., accordion, tabs, grid).

**If page requires JavaScript rendering**: DEFER to end of batch. Do not add yet.

### ☐ 3. Add to Configuration (1 minute)

Edit `UNIVERSITY_CONFIG.py`:

```python
"newuniversity.edu": {
    "url": "https://newuniversity.edu/graduate/programs",
    "strategy": "anchor",  # From Step 2
    "notes": "Clean anchor list, standard catalog layout"
}
```

### ☐ 4. Add Test Expectations (1 minute)

Edit `regression_test.py`:

Add minimum count (set to ~80% of what you expect):
```python
EXPECTED_MIN_PROGRAMS = {
    # ... existing entries
    "newuniversity.edu": 50,  # Estimate conservatively
}
```

Add 2-3 known program names you confirmed exist in Step 1:
```python
KNOWN_PROGRAMS = {
    # ... existing entries
    "newuniversity.edu": [
        "Computer Science",
        "Mechanical Engineering",
        "MBA",
    ],
}
```

### ☐ 5. Run Regression Suite (1 minute)

```bash
py -3.13 regression_test.py
```

**Expected outcome**:
- ✅ All previous universities still PASS
- ❌ New university FAILS (count will be wrong on first run, but known programs should be found)

If any previous university changed from PASS to FAIL, you've introduced a regression. STOP and investigate.

### ☐ 6. Print Full Extracted List (1 minute)

Run full test to see actual extracted programs:

```bash
py -3.13 test_all_universities.py > output.txt
```

Open `output.txt` and find the new university's section.

### ☐ 7. Manual Verification — READ EVERY LINE (2 minutes)

**This is the most important step.**

Read every single extracted program name. Check for:

❌ **Junk to reject**:
- Deadline text ("Master's: July 1", "PhD: October 1")
- Navigation text ("Follow Us", "Contact Us", "More Info")
- UI elements ("plus_icon", "menu", "search")
- Table headers ("Program", "Department", "Degree")
- Admin text ("Financial Aid", "Apply Now", "Tuition")

✅ **Good programs**:
- Real degree/program names only
- Proper formatting
- No nav/admin/UI concatenation
- URLs look valid (start with `http`)

### ☐ 7b. Spot-Check URLs (1 minute)

Pick 5 random program URLs from the extracted list and open them in browser.

**Check**:
- ✅ URL points to actual program page (not nav page, not anchor)
- ✅ Page loads successfully (not 404)
- ✅ Content matches program name

**Why**: Sometimes names look perfect but URLs point to navigation pages, section anchors, or dead links.

**If ANY junk appears**:
1. Identify why (wrong container? wrong tag? missing filter?)
2. Options:
   - Try different URL (maybe wrong catalog page)
   - Adjust extractor filtering (if same structure, edge case)
   - Create new extractor variant (if fundamentally different structure)
3. Re-test from Step 5

**If output is 100% clean**: Proceed to Step 8

### ☐ 8. Update Minimum Count (30 seconds)

Based on actual count from Step 6, update `regression_test.py`:

```python
EXPECTED_MIN_PROGRAMS = {
    # ...
    "newuniversity.edu": 80,  # Set to ~80% of actual (e.g., if got 100, set to 80)
}
```

### ☐ 9. Run Regression Suite Again (30 seconds)

```bash
py -3.13 regression_test.py
```

**Expected outcome**:
- ✅ ALL universities PASS (including new one)

If new university still FAILS, check error message and adjust minimum count or known programs list.

### ☐ 10. Commit (30 seconds)

```bash
git add UNIVERSITY_CONFIG.py regression_test.py
git commit -m "Add [University Name] - [strategy] - [N] programs"
```

Example:
```bash
git commit -m "Add Arizona State - anchor - 95 programs"
```

---

## Full Checklist Summary

```
☐ 1. Open page manually, find 2-3 real programs
☐ 2. Inspect HTML, identify structure
☐ 3. Choose matching strategy from existing 5
☐ 4. Add to UNIVERSITY_CONFIG.py
☐ 5. Add EXPECTED_MIN and KNOWN_PROGRAMS to regression_test.py
☐ 6. Run regression suite (expect new university to fail, others to pass)
☐ 7. Run full test, print all extracted programs
☐ 8. READ EVERY SINGLE LINE manually
☐ 9. If 100% clean: update minimum count
☐ 10. Run regression suite again (should all pass)
☐ 11. Commit
```

**Time**: 7-15 minutes per university

---

## Red Flags — When to STOP

### 🚨 Previous university changed from PASS to FAIL
**Action**: You've introduced a regression. Revert your changes and investigate before proceeding.

### 🚨 Extracted list contains obvious junk
**Action**: Do not proceed. Fix the extraction first (wrong URL? wrong strategy? new filter needed?).

### 🚨 Count way lower than expected
**Action**: Extraction is incomplete. Check:
- Wrong catalog URL?
- Wrong container scoping?
- Overly aggressive filtering?

### 🚨 New structure doesn't match any existing strategy
**Action**: Do not force-fit. Either:
- Create new extractor variant
- Defer this university until new extractor is designed
- Document the structure and discuss with team

### 🚨 Page requires JavaScript rendering
**Action**: Do not add yet. Mark as `playwright_*` and defer to end of batch after all static-HTML universities are validated.

---

## DO NOT Skip Manual Verification

The entire project's debugging history proves this:

❌ **Not sufficient**: "Found 46 programs"  
✅ **Sufficient**: Reading all 46 lines and confirming each is a real degree name

**Why**:
- MIT once showed "13 programs" but 5 were junk (deadline text, nav menus)
- Purdue once showed "0 programs" but content existed (wrong DOM selector)
- Counts can look healthy while hiding garbage

Manual read-through is the highest-value validation step.

---

## Examples

### Good Commit
```
Add Arizona State - anchor - 95 programs

- Strategy: anchor (degree names in <a> tag text)
- URL: https://degrees.apps.asu.edu/masters-phd
- Manual verification: 0% junk, all real program names
- Known programs: Computer Science, MBA, Mechanical Engineering
```

### Bad Commit
```
Add Stanford - playwright_table - 0 programs

ERROR: This should not be committed yet.
Strategy is not implemented. Mark as SKIPPED.
```

---

## After Every 3-5 Universities

Run the full suite and manually spot-check a few random programs from each university to ensure:
1. No regressions crept in
2. All universities still extracting cleanly
3. No URL changes broke anything

**Frequency**: After every 3-5 additions, or daily if adding in batches.

---

## University Addition Order (Recommended)

### Batch 1 (next 6 universities)
Test if existing 4 strategies generalize:

1. Arizona State (likely `anchor`)
2. Ohio State (likely `heading`)  
3. Georgia Tech (likely `table`)
4. Carnegie Mellon (likely `table`)
5. University of Florida (likely `anchor`)
6. UCLA (likely `plain_text_list`)

### Batch 2 (Playwright universities)
Only after Batch 1 is 100% validated:

7. Stanford (`playwright_table`)
8. Manchester (`playwright_anchor`)

**Rationale**: Validate simpler cases first. Playwright universities require new infrastructure (Playwright extractor implementation) and should not block progress on static-HTML universities.

---

## Success Criteria

A university addition is successful when:

1. ✅ Regression test shows `PASS`
2. ✅ Manual verification shows 0% junk
3. ✅ All previous universities still show `PASS`
4. ✅ Known programs confirmed present
5. ✅ Minimum count set reasonably (80% of actual)

Only commit when all 5 criteria met.
