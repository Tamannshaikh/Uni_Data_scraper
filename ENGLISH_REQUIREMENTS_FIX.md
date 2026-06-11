# English Requirements Extraction Fix

**Date:** June 11, 2026  
**Status:** ✅ Fixes Implemented (Testing in Progress)  
**Issue:** English requirements returning 0/5 sub-fields across all universities

---

## Problem Analysis

### Symptoms
- IELTS: null ❌
- TOEFL: null ❌  
- PTE: null ❌
- Duolingo: null ❌
- Notes: "page not found" or generic message

**Affected universities:** All tested (Arkansas State, McGill, Edinburgh, Monash)

### Root Causes Identified

#### 1. Main Page Crowding Out Specialist Pages
**Edinburgh logs showed:**
```
english_requirements: included 1/5 relevant pages
  #1 score=210: main program page (10,522 words)
  #2 score=110: /english-requirements (281 words)
  #3 score=110: /english-language-requirements (281 words)
```

**Problem:** Main page consumed full 5985 char budget, leaving no room for actual english requirements pages where IELTS scores live.

#### 2. Duplicate Content from JavaScript Sites
**Arkansas State returned exactly 1848 words for EVERY sub-page:**
```
/mba-program → 1848 words
/mba-program/english-language → 1848 words  (SAME CONTENT!)
/mba-program/fees → 1848 words  (SAME CONTENT!)
/mba-program/modules → 1848 words  (SAME CONTENT!)
```

**Why:** JavaScript routing serves the same shell HTML for all URLs. Sub-pages don't have unique content — wasting tokens and diluting signal.

#### 3. Weak LLM Model
Using `gemini-2.5-flash-lite` instead of `gemini-2.5-flash`. Flash-lite is cheaper but worse at complex multi-field extraction with nested JSON.

---

## Fixes Implemented

### FIX 1: Increase English Budget + Scoring Boost

**File:** `pipeline/ai_extractor.py`

**Change 1 - Budget:**
```python
# OLD:
english_context = build_field_specific_context(pages_data, "english_requirements", 6000)

# NEW:
english_context = build_field_specific_context(pages_data, "english_requirements", 10000)  # INCREASED
```

**Change 2 - Scoring:**
```python
# ENGLISH REQUIREMENTS: Boost specialist pages significantly
if field_group == "english_requirements":
    # +150 boost for actual english requirements pages
    ENGLISH_EXACT_PATTERNS = [
        "english-requirements",
        "english-language-requirements",
        "language-requirements",
        "english-proficiency",
        "ielts",
        "toefl",
    ]
    if any(pattern in url for pattern in ENGLISH_EXACT_PATTERNS):
        score += 150  # These pages have the actual IELTS/TOEFL scores
```

**Expected result:**
- `/english-requirements` should now score **260** (110 base + 150 boost)
- Main page scores ~100-130 (no boost)
- Specialist page wins and gets included first

### FIX 2: Duplicate Content Detection

**File:** `pipeline/tier1_crawl4ai.py`

**Added after word count check:**
```python
# FIX: Detect duplicate content from JavaScript-rendered sites
# Arkansas State returns EXACTLY 1848 words for every sub-page
if len(pages) > 0:  # Have a main page to compare against
    main_page = pages[0]
    main_wc = main_page.get("word_count", 0)
    
    # If word count is EXACTLY the same as main page and > 500 words
    # this is likely the same content being served for different URLs
    if wc == main_wc and wc > 500:
        # Double-check: compare first 200 chars
        main_content = main_page.get("markdown", "")[:200]
        if markdown[:200] == main_content:
            logger.warning(
                f"[tier1_crawl4ai] DUPLICATE CONTENT: {fetch_url} "
                f"has identical content to main page ({wc} words) — skipping"
            )
            return None  # Skip this page entirely
```

**Expected result:**
- Arkansas State: 14 identical pages skipped
- Only unique pages (real `/admissions-and-aid/tuition-and-fees/` page) get processed
- LLM gets better signal, less noise

### FIX 3: Upgrade to Gemini Flash

**File:** `config.py`

```python
# OLD:
llm_model: str = "gemini-2.5-flash-lite"

# NEW:
llm_model: str = "gemini-2.5-flash"  # upgraded from flash-lite for better extraction quality
```

**Why:**
- Flash-lite: Cheapest, fastest, weakest at complex extraction
- Flash: Better at following complex multi-field instructions
- Cost impact: Minimal (paying per token anyway, just slightly higher rate)

---

## Test Results - McGill MBA (Fresh Scrape)

### Verification Checklist

✅ **English budget increased:** 5985 → 10000 chars  
✅ **Scoring boost working:** `/english-requirements` scored **260** (was 110)  
✅ **Pages included:** 2/9 pages (was 1/5)  
✅ **Model upgraded:** Restarted server to load new config  
⚠️ **Extraction still partial:** 1/5 sub-fields (notes only)

### Logs Analysis

```
INFO: english_requirements - ALL PAGE SCORES:
  # 1 score=260 words=451 url=.../english-requirements ✅ BOOSTED!
  # 2 score=170 words=451 url=.../english-language
  # 3 score=100 words=1808 url=.../mba-programs/mba
  # 4-9 score= 80 (various pages)

INFO: english_requirements: included 2/9 relevant pages, 9986 chars, top_score=260
INFO: score distribution: >=200:1 | >=150:2 | >=100:3 | >=80:9
```

**Analysis:**
- ✅ Scoring boost working perfectly
- ✅ Budget increased working (9986 chars vs 5985)
- ✅ Specialist page ranked #1
- ⚠️ But LLM still returning nulls for IELTS/TOEFL

### Extraction Result

```json
{
  "ielts": null,
  "toefl": null,
  "pte": null,
  "duolingo": null,
  "notes": "The page for English requirements was not found."
}
```

**Issue:** Despite sending the right pages with the right scores, LLM extraction still failing.

---

## Remaining Issues

### Why Extraction Still Fails

**Possible reasons:**

1. **Page Content Quality**
   - McGill's `/english-requirements` page might be mostly navigation/template
   - Actual IELTS scores might be in a table or accordion that Crawl4AI doesn't capture well
   - Need to inspect actual markdown content sent to LLM

2. **LLM Prompt Issues**
   - Current prompt might not handle McGill's specific format
   - Might need more examples of diverse formats (US vs UK vs AU vs CA)

3. **Page Classification Issues**
   - Page might be classified incorrectly
   - Content might be in wrong section

4. **Flash-lite Still Running**
   - Server restart might not have loaded new config
   - Need to verify flash (not flash-lite) is being used

---

## Next Steps

### IMMEDIATE (User to run after server restart)

1. **Verify model upgrade:**
   ```bash
   # Check logs for:
   sending: X chars to Gemini (gemini-2.5-flash)  # Should be 'flash' not 'flash-lite'
   ```

2. **Test McGill again:**
   ```bash
   cd uniscraper-backend
   .\venv\Scripts\activate
   python test_english_fix.py
   ```

3. **Check for duplicate content warnings:**
   ```
   [tier1_crawl4ai] DUPLICATE CONTENT: .../mba-program/modules 
     has identical content to main page (451 words) — skipping
   ```

### INVESTIGATION NEEDED

4. **Inspect actual page content:**
   - What markdown is Crawl4AI extracting from `/english-requirements`?
   - Are IELTS scores actually in the 451 words?
   - Or are they in an accordion/table that's not being captured?

5. **Test with different university:**
   - Try a simpler site (e.g., Arkansas State `/english-language` page)
   - See if extraction works when content is cleaner

6. **Enhance LLM prompt:**
   - Add more diverse format examples
   - Explicit instructions for table extraction
   - Fallback strategies

### IF STILL FAILING

7. **Add debug logging:**
   ```python
   # In ai_extractor.py, before sending to LLM:
   if "english" in field_group:
       print(f"[DEBUG] Sending to LLM for english:")
       print(extraction_text[:500])  # First 500 chars
   ```

8. **Try direct API test:**
   - Extract McGill's english requirements page manually
   - Send to Gemini with current prompt
   - See what it returns

---

## Expected Improvements

### Before Fixes
```
University         English Sub-fields
─────────────────────────────────────
Arkansas State     0/5
McGill             1/5 (notes only)
Edinburgh          0/5
Monash             0/5
```

### After Fixes (Target)
```
University         English Sub-fields
─────────────────────────────────────
Arkansas State     2-3/5  (IELTS + TOEFL at minimum)
McGill             2-3/5
Edinburgh          2-3/5
Monash             1-2/5  (harder format)
```

### Overall Field Count Improvement
```
Current:  7-8/15 fields (50%)
Target:   10-12/15 fields (70-80%)
```

---

## Code Changes Summary

### Files Modified

1. **`pipeline/ai_extractor.py`**
   - Line ~340: Added +150 scoring boost for english requirements pages
   - Line ~650: Increased english budget 6000 → 10000

2. **`pipeline/tier1_crawl4ai.py`**
   - Line ~325: Added duplicate content detection (word count + first 200 chars comparison)

3. **`config.py`**
   - Line 24: Changed llm_model from "gemini-2.5-flash-lite" to "gemini-2.5-flash"

### Test Scripts Created

4. **`test_english_fix.py`**
   - Comprehensive test for McGill MBA
   - Checks english requirements extraction
   - Shows scoring and duplicate detection in logs

---

## Validation Commands

```bash
# Start backend (if not running)
cd uniscraper-backend
.\venv\Scripts\activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Run test
python test_english_fix.py

# Check logs for:
# 1. score=260 for /english-requirements (boost working)
# 2. included 2/9 pages, 9986 chars (budget working)
# 3. DUPLICATE CONTENT warnings (deduplication working)
# 4. gemini-2.5-flash (model upgrade working)
```

---

## Success Criteria

- [ ] English requirements score **>= 250** for specialist pages
- [ ] Budget allows **2-3 pages** (not just 1)
- [ ] Duplicate content warnings appear for JavaScript sites
- [ ] **gemini-2.5-flash** used (not flash-lite)
- [ ] At least **2/5 english sub-fields** extracted (IELTS + TOEFL minimum)
- [ ] Overall field count improves to **10-12/15** (from 7-8/15)

---

## User Instructions

After reviewing this document:

1. Restart backend if not already done
2. Run `python test_english_fix.py`
3. Check logs for the 4 validation points above
4. Report back:
   - Model being used (flash vs flash-lite)
   - English sub-fields extracted (X/5)
   - Any DUPLICATE CONTENT warnings
   - Scoring for `/english-requirements` page

**Do NOT push to GitHub yet** - waiting for test results first.

---

**Status:** Fixes implemented, awaiting test validation  
**Confidence:** HIGH for scoring/budget fixes, MEDIUM for extraction improvement  
**Next:** Validate with fresh test after server restart

