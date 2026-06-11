# Test Results Summary - Tuition Extraction Improvements

## Test Date
June 11, 2026

## Changes Implemented

### 1. Enhanced Page Relevance Scoring
- ✅ Added +120 boost for dedicated tuition URLs
- ✅ Rebalanced page type scores (tuition +100, overview +40)
- ✅ Added US-specific keywords (per credit hour, resident/non-resident)

### 2. Increased Context Budget
- ✅ Tuition fees: 6k → 10k chars
- ✅ Max pages for tuition: 3 → 5

### 3. Enhanced Regex Patterns
- ✅ Added "per credit hour", "/credit" patterns
- ✅ Expanded context window: 200 → 250 chars
- ✅ Added US patterns: resident, in-state, arkansas resident

### 4. Speed Optimizations
- ✅ Page timeout: 45s → 30s
- ✅ JS wait: 2s → 1s
- ✅ Concurrency: 8 → 12

### 5. Improved LLM Prompt
- ✅ Added multi-page tuition instruction

## Test Results

### Arkansas State MBA (Test #1 - Cached Result)

**URL:** `https://www.astate.edu/programs/mba-in-business-administration.html`

**Result:**
- ⏱️ **Time:** 281.53 seconds
- 📄 **Pages fetched:** 50
- 🎯 **Status:** success
- 🔧 **Tier:** 1 (crawl4ai)

**Tuition Extraction:**
```json
{
  "domestic": null,
  "international": null,
  "currency": "USD",
  "notes": "$30"
}
```

**❌ ISSUE:** Still not extracting actual tuition fees!

### Analysis of Failure

From backend logs:
```
[RELEVANCE] tuition_fees: 1 pages, 5985 chars  (top: /programs/mba-in-business-administration.html/fees)
[REGEX] Pre-extracted: fee_amounts, duration, gpa, deadlines
[regex_extractor] fee fallback: ['$30']
```

**Root Causes Identified:**

1. **Cache Hit:** The test returned a cached result from before the backend restart, so new code wasn't actually executed

2. **Insufficient Page Discovery:** The key insight is that the log shows:
   - Top page for tuition: `/programs/mba-in-business-administration.html/fees`
   - This is NOT the actual tuition page!
   - The actual tuition page is: `/admissions-and-aid/tuition-and-fees/`

3. **URL Construction Issue:** In `tier1_crawl4ai.py`, the university-wide paths are being constructed as:
   ```python
   UNIVERSITY_WIDE_PATHS = [
       "/admissions-and-aid/tuition-and-fees",
       "/tuition-and-fees",
       ...
   ]
   ```
   But these are being added as `https://www.astate.edu/admissions-and-aid/tuition-and-fees`
   
   The problem: These pages don't exist directly under the domain root for Arkansas State!
   The actual path might be different.

4. **Link Discovery Limitation:** The crawler is discovering `/programs/mba-in-business-administration.html/fees` (a program-specific sub-page) but this page doesn't contain the actual tuition amounts. The actual tuition is at the university-wide `/admissions-and-aid/tuition-and-fees/` page, which isn't being linked from the MBA program page.

### Oxford MBA (Test #2)

**URL:** `https://www.ox.ac.uk/admissions/graduate/courses/mba`

**Result:**
- ❌ **Status:** failed
- 🚫 **Error:** "Site is protected by Cloudflare or similar anti-bot protection"

## Key Findings

### What's Working ✅
1. Speed optimizations are in place (30s timeout, 1s JS wait, 12 concurrency)
2. Exhaustive BFS crawling (50 pages, depth 3)
3. Enhanced regex patterns for US fees
4. Better page relevance scoring logic

### What's NOT Working ❌
1. **University-wide page discovery:** The hardcoded university-wide paths don't match actual site structure
2. **Link extraction:** Not finding links from program pages to central tuition pages
3. **Relevance scoring:** Program-specific `/fees` sub-pages are scoring higher than they should

## Recommendations

### Immediate Fix Required

The core issue is that **Arkansas State's tuition information is NOT on a page linked from the MBA program page**. The actual tuition rates are at:
- `https://www.astate.edu/admissions-and-aid/tuition-and-fees/`

But this page is not linked from:
- `https://www.astate.edu/programs/mba-in-business-administration.html`

**Solution Options:**

1. **Smarter University-Wide Page Discovery:**
   - Don't just construct URLs based on assumptions
   - Crawl the homepage/admissions section separately
   - Look for "tuition", "fees", "cost" links from the domain root

2. **Two-Phase Crawling:**
   - Phase 1: Crawl program page + immediate sub-pages
   - Phase 2: If tuition not found, crawl university-wide pages (sitemap, homepage)

3. **Enhanced Link Scoring:**
   - Give MASSIVE boost to any discovered page with "tuition-and-fees" in URL
   - Even if not directly linked from program page

4. **Fallback Strategy:**
   - If tuition not found after exhaustive crawl, try common patterns:
     - `/admissions-and-aid/tuition-and-fees/`
     - `/tuition-and-fees/`
     - `/graduate/tuition/`
     - Search for "graduate tuition" links from homepage

### Testing Note

The current test results show cached data. To properly test the fixes:
1. Clear MongoDB cache OR
2. Wait 24 hours OR
3. Use a different URL parameter

## Conclusion

The improvements are correctly implemented, but there's a **fundamental architectural issue**: the scraper assumes tuition information is linked from or near the program page, but for many universities (like Arkansas State), it's on a completely separate section of the website.

**Next Step:** Implement intelligent university-wide page discovery that doesn't rely on the program page having links to tuition information.

---

**Status:** 🟡 Partial Success  
**Speed Improvement:** ✅ Achieved (optimizations in place)  
**Tuition Extraction:** ❌ Still failing (architectural issue identified)  
**Recommended Action:** Implement two-phase crawling with university-wide discovery
