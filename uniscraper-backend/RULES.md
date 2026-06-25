# Rules of Engagement

**Last Updated**: 2026-06-25

These are the non-negotiable principles that keep this project stable.

---

## Rule 1: Freeze Means Freeze

**Do not modify working extractors.**

If a new university has a slightly different structure, create a **variant** instead:

❌ **Wrong**:
```python
# Modify extract_table() to handle both MIT and new university
def extract_table(base_url, container):
    if "mit.edu" in base_url:
        # MIT logic
    else:
        # New logic
```

✅ **Right**:
```python
# Keep extract_table() for MIT, create new variant
def extract_table_v2(base_url, container):
    # New logic for different table structure
```

**Why**: Stable code stays stable. Generalization breaks things.

---

## Rule 2: Observation Before Implementation

**Never create a new extractor until:**

1. ☐ HTML has been inspected manually
2. ☐ Existing extractors have been ruled out
3. ☐ The structure is proven fundamentally different

**Common false alarms** (do NOT create new extractor):
- Wrong DOM selector → fix selector, not extractor
- Wrong container → inspect different container
- Wrong URL → find correct catalog page

**Example from this project**:

❌ **Assumption**: "Purdue needs Playwright because 0 programs extracted"  
✅ **Reality**: Content existed in static HTML, just needed correct container (`program-card` divs)

**Lesson**: Inspect HTML first, make architecture decisions second.

---

## Rule 3: Manual Verification Is Non-Negotiable

**After every extraction, read every single line.**

❌ **Not sufficient**: "Found 46 programs ✅"  
✅ **Sufficient**: Reading all 46 lines and confirming each is a real degree name

**Why**: This project's entire debugging history proves:

> Every fix that worked was preceded by someone opening the real HTML and reading it.  
> Every "success" that turned out to be hollow was a case where a count got trusted instead.

**Examples**:
- MIT once showed "13 programs" but 5 were junk (deadline text, nav menus)
- Purdue once showed "0 programs" but content existed (wrong selector)
- Stanford showed "0 programs PASS" but strategy wasn't implemented (false positive)

**Process**:
```bash
py -3.13 test_all_universities.py > output.txt
vim output.txt  # READ EVERY LINE
```

No shortcuts. No trusting counts. Read the actual output.

---

## Rule 4: Three-State Status (PASS/FAIL/SKIPPED)

**Never merge code with "PASS — 0 programs".**

Three states:
- `PASS` = extractor exists and output is clean
- `FAIL` = extractor exists but output is bad
- `SKIPPED` = extractor not implemented yet

❌ **Wrong**:
```
stanford.edu    ✅ PASS — 0 programs
```

✅ **Right**:
```
stanford.edu    ⏭️  SKIPPED — Strategy 'playwright_table' not implemented yet
```

**Why**: Silent failures hide problems. Explicit SKIPPED status forces acknowledgment.

---

## Rule 5: Dual Assertions (Count + Known Programs)

**Both must pass, not just count.**

```python
# Check 1: Minimum count (catches shrinkage)
assert len(programs) >= EXPECTED_MIN[domain]

# Check 2: Known programs present (catches substitution)
for expected in KNOWN_PROGRAMS[domain]:
    assert any(expected.lower() in p.lower() for p in extracted)
```

**Why**: Count alone can look healthy while hiding quality degradation.

**Example**:
```
MIT before: 46 real programs
MIT after:  44 real programs + 2 junk items = 46 total
Count check: PASS ✅ (still 46)
Known program check: FAIL ❌ ("Architecture" missing)
```

Known programs catch substitution that count checks miss.

---

## Rule 6: No Auto-Detection

**Manual classification only.**

❌ **Do not build**:
- `classify_page()` — auto-detect strategy
- `detect_structure()` — guess extractor
- `confidence_scorer()` — rate extraction quality

✅ **Instead**:
- Human inspects page (2 minutes)
- Human chooses strategy from 5 options
- Human verifies output manually

**Why**: Auto-detection adds complexity and failure modes. Manual classification is 100% reliable and takes 2 minutes.

---

## Rule 7: Manual Catalog Curation (First 50)

**For top 50 universities, manually find catalog URLs.**

**Time**: 50 universities × 2 minutes = 100 minutes = **under 2 hours**

**Compare to**:
- Building discovery heuristics: weeks
- Debugging false positives: weeks
- Maintaining complex crawlers: ongoing

**Decision**: Manual wins decisively at this scale.

Re-evaluate only if scaling to 500+ universities.

---

## Rule 8: Regression Suite After Every Change

**Run this after every university addition**:

```bash
py -3.13 regression_test.py
```

If any **existing** university changes from PASS to FAIL, you've introduced a regression. STOP and investigate.

**Do not commit** if regression test fails.

---

## Rule 9: Checklist Is Mandatory

**Follow `ADDING_UNIVERSITIES.md` for every new university.**

11 steps, no exceptions:

```
☐ 1. Open page manually
☐ 2. Inspect HTML, identify structure
☐ 3. Choose strategy
☐ 4. Add to UNIVERSITY_CONFIG.py
☐ 5. Add EXPECTED_MIN and KNOWN_PROGRAMS
☐ 6. Run regression suite
☐ 7. Print full output
☐ 7b. Spot-check 5 random URLs in browser
☐ 8. READ EVERY SINGLE LINE manually
☐ 9. Update minimum count
☐ 10. Run regression suite again
☐ 11. Commit
```

Step 8 is the most important.

---

## Rule 10: Defer Hard Cases

**Do not let difficult universities block progress.**

**Defer to end of batch**:
- JavaScript-rendered pages (Stanford, Manchester)
- Unusual structures that need new extractors
- Universities with CAPTCHAs or bot detection
- Universities that 403/block requests

**Why**: Validate simple cases first. Prove existing extractors generalize. Then tackle hard cases with proven foundation.

**Current deferred**:
- Stanford (playwright_table)
- Manchester (playwright_anchor)

These should only be attempted after 6-10 static-HTML universities are validated.

---

## Red Flags (When to STOP)

### 🚨 Regression test fails on existing university
**You've introduced a bug.** Revert changes and investigate.

### 🚨 New university extracts junk
**Do not proceed.** Wrong URL? Wrong strategy? Missing filter?

### 🚨 Temptation to "improve" working extractor
**Don't.** Stable code stays stable. Create variant instead.

### 🚨 Assuming structure without inspecting HTML
**Don't assume**:
- "Needs Playwright"
- "Needs AI"
- "Needs new strategy"

**Instead**: Open HTML, read structure, match to existing extractors.

### 🚨 Trusting counts without reading output
**"Found 46 programs"** tells you nothing about quality.

**Reading all 46 lines** tells you everything.

---

## The Core Lesson

From weeks of debugging:

> The problem was never extraction quality.  
> The problem was applying the wrong extractor to the wrong page structure.

**Solution**: Observation-based classification, not guessing.

**Process**:
1. Inspect HTML manually
2. Match to existing strategy
3. Configure
4. Test
5. **Read every line**
6. Commit

Simple. Deterministic. Working.

---

## Current System (Keep This Simple)

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

---

## Architecture Status

**Frozen**:
- 5 extractors (anchor, table, heading, plain_text_list, heading_with_button)
- 4 working universities (Arkansas, MIT, Purdue, UCSD)
- Manual classification workflow

**Next phase**: Data onboarding (add universities, not architecture)

**Rule**: No new extractors unless genuinely novel structure proven.

---

## Success Definition

A university is successfully added when:

1. ✅ Regression test shows `PASS`
2. ✅ Manual verification shows 0% junk
3. ✅ All previous universities still show `PASS`
4. ✅ Known programs confirmed present
5. ✅ Minimum count set reasonably
6. ✅ 5 random URLs checked in browser

All 6 must be true before commit.

---

## The "Boring Stage" Is Good

> The project has finally reached the boring stage—and in scraping projects, boring is usually a sign that things are working.

**Current workflow**:
- Inspect HTML (2 min)
- Choose strategy (30 sec)
- Configure (1 min)
- Test (2 min)
- Read output (2 min)
- Commit (30 sec)

**Total**: 7-8 minutes per university

This is boring, repetitive, manual work. That's exactly right.

**The architecture phase is over.**

---

## What NOT to Do Next

❌ Build auto-classifier  
❌ Add confidence scores  
❌ Create discovery system  
❌ Implement crawlers  
❌ "Improve" working extractors  
❌ Add LLM validation  

✅ **What TO do next**:

Follow the checklist. Add universities. Read output. Commit. Repeat.

That's it.

---

## Summary

These 10 rules keep the system stable:

1. Freeze means freeze (do not modify working extractors)
2. Observation before implementation (inspect HTML first)
3. Manual verification is non-negotiable (read every line)
4. Three-state status (PASS/FAIL/SKIPPED, never "PASS 0")
5. Dual assertions (count + known programs)
6. No auto-detection (manual classification only)
7. Manual catalog curation for first 50
8. Regression suite after every change
9. Checklist is mandatory (11 steps, no shortcuts)
10. Defer hard cases (validate simple first)

Follow these rules. The architecture will stay stable. The data will scale.
