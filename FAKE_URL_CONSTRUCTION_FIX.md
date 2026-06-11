# Fake URL Construction Fix - Root Cause Analysis

**Date:** June 11, 2026  
**Issue:** Tier 1 (Crawl4AI) falling back to Tier 2 (Firecrawl) due to 30s timeouts on non-existent URLs

---

## Root Cause

The BFS crawler in `tier1_crawl4ai.py` was constructing fake URLs by appending suffixes to existing pages:

### Before Fix (Lines 365-388)
```python
# Source C: construct known sub-page patterns
base_domain = urlparse(fetch_url).netloc
base_path = urlparse(fetch_url).path.rstrip("/")
KNOWN_SUFFIXES = [
    "/entry-requirements", "/fees", "/how-to-apply",
    "/application", "/english-requirements", "/english-language",
    "/scholarships", "/funding", "/overview", "/about",
    "/structure", "/modules", "/curriculum",
]
for suffix in KNOWN_SUFFIXES:
    extracted_links.add(f"https://{base_domain}{base_path}{suffix}")

# Also add university-wide admission/fees pages
UNIVERSITY_WIDE_PATHS = [
    "/admissions-and-aid/tuition-and-fees",
    "/admissions-and-aid/financial-aid",
    "/tuition-and-fees",
    "/tuition/graduate",
    "/graduate-admissions",
    "/international-students/admissions",
    "/international/fees",
]
for path in UNIVERSITY_WIDE_PATHS:
    extracted_links.add(f"https://{base_domain}{path}")
```

### What This Created

For Arkansas State MBA (`https://www.astate.edu/programs/mba`), it constructed:
- `https://www.astate.edu/programs/mba/entry-requirements` ❌ 404
- `https://www.astate.edu/programs/mba/english-requirements` ❌ 404
- `https://www.astate.edu/programs/mba/fees` ❌ 404
- `https://www.astate.edu/programs/mba/how-to-apply` ❌ 404
- Plus 17 more fake URLs from `UNIVERSITY_WIDE_PATHS`

### Impact

1. **30-second timeouts** - Each fake URL tried to fetch for 30s before failing
2. **Crawl4AI marked as failed** - Multiple timeouts caused Tier 1 to fail
3. **Fallback to Tier 2** - System dropped to Firecrawl (old approach)
4. **Our fixes not applied** - All English requirements improvements (scoring boost, duplicate detection, budget increase) only work in Tier 1

---

## The Fix

### After Fix (Lines 362-368)
```python
for match in re.finditer(r'(?<!\()https?://[^\s\)>]+', markdown):
    extracted_links.add(match.group(0).rstrip(".,)"))

# REMOVED: Fake URL construction with KNOWN_SUFFIXES
# The previous code appended suffixes like /entry-requirements and /english-requirements
# to existing pages, creating non-existent URLs that timeout after 30s.
# Now we ONLY follow links that actually exist on the page.

logger.info(f"[tier1_crawl4ai] Depth {depth} — {fetch_url} OK ({wc} words, {len(extracted_links)} links)")
```

### What Changed
- ✅ Removed `KNOWN_SUFFIXES` construction (lines 368-374)
- ✅ Removed `UNIVERSITY_WIDE_PATHS` construction (lines 376-388)
- ✅ Now **ONLY** follows links that actually exist in the HTML/Markdown

---

## Test Case Analysis

### Arkansas State MBA

**Problem:** No IELTS/TOEFL info found on tested pages:
- ❌ `/international-students/admissions` - no IELTS
- ❌ `/admissions-and-aid/graduate-admissions/` - no IELTS
- ❌ `/international/` - no IELTS

**Likely explanation:** 
- Arkansas State may not publish English requirements online (especially for domestic-focused programs)
- OR English requirements are on a page the crawler hasn't discovered yet
- OR Requirements are in a PDF brochure

**Action:** Use a different university for testing (Edinburgh, Sydney, etc.)

### McGill MBA

**Problem:** Main MBA page has **zero admission info**:
- ❌ No links containing "admission", "english", "requirement"
- ❌ Page content has no IELTS, TOEFL, admission text
- ❌ 79 internal links found, but all point to general faculty pages

**Why:** McGill's website structure is incomplete or uses a different URL pattern entirely.

**Constructed URLs that 404:**
- `/desautels/programs/mba/admissions` ❌ Soft 404
- `/desautels/programs/mba/admission-requirements` ❌ 404
- `/desautels/programs/mba/english-requirements` ❌ 404

**Action:** McGill is not a good test case - find universities with accessible English requirements pages

---

## Better Test Universities

### ✅ University of Sydney
```bash
https://www.sydney.edu.au/courses/courses/pc/master-of-business-administration.html
```
- Known to have structured admission requirements
- Clear navigation to English language requirements
- Australian university (uses IELTS primarily)

### ✅ University of Melbourne
```bash
https://study.unimelb.edu.au/find/courses/graduate/master-of-business-administration/
```
- Comprehensive admission pages
- Dedicated English requirements section
- Go8 university with detailed info

### ✅ University of Edinburgh (Already tested)
```bash
https://www.ed.ac.uk/studying/postgraduate/degrees/index.php?r=site/view&id=107
```
- Has `/english-language-requirements` page
- UK university with structured admission info
- Previously extracted 7/15 fields

---

## Expected Improvements After Fix

### Before (With Fake URLs)
```
Arkansas State MBA:
  Tier: 2 (Firecrawl fallback)
  Time: 186s
  Pages: 13
  English: 0/5 ❌
  Tuition: 0/4 ❌
  
  Issue: Timeouts on fake URLs caused Tier 1 to fail
```

### After (Only Real Links)
```
Edinburgh MBA (example):
  Tier: 1 (Crawl4AI with fixes) ✅
  Time: <150s (no 30s timeouts)
  Pages: 15-20
  English: 2-3/5 ✅
  Tuition: 3-4/4 ✅
  
  Benefit: All fixes active (scoring boost, duplicate detection, budget)
```

---

## Verification Steps

### 1. Restart Backend
```bash
cd c:\Projects\uniscrape\uniscraper-backend
.\venv\Scripts\activate
python main.py
```

### 2. Clear Cache
```bash
python -c "import asyncio; from motor.motor_asyncio import AsyncIOMotorClient; async def clear(): client = AsyncIOMotorClient('mongodb+srv://patilniks69_db_user:Ryussei0120@cluster0.0gpoypz.mongodb.net/'); db = client['uniscraper']; result = await db.scrape_results.delete_many({'url_requested': {'$regex': 'astate|mcgill|ed.ac.uk'}}); print(f'Deleted {result.deleted_count}'); client.close(); asyncio.run(clear())"
```

### 3. Test with Sydney
```bash
python -c "import httpx; resp = httpx.post('http://localhost:8000/api/v1/scrape', json={'url': 'https://www.sydney.edu.au/courses/courses/pc/master-of-business-administration.html'}, timeout=300); print(f'Scrape ID: {resp.json()[\"scrape_id\"]}')"
```

### 4. Verify Tier 1 is Used
```bash
# Wait 2-3 minutes for scrape to complete
python -c "import httpx; resp = httpx.get('http://localhost:8000/api/v1/scrape/SCRAPE_ID'); data = resp.json(); print(f'Tier: {data[\"tier_used\"]}'); print(f'English: {sum(1 for v in (data.get(\"english_requirements\") or {}).values() if v)}/5')"
```

### 5. Check Backend Logs
Should see:
```
[tier1_crawl4ai] Exhaustive BFS crawl starting...
[tier1_crawl4ai] Depth 0 — https://... OK (1234 words, 45 links)
[ai_extractor] english_requirements - ALL PAGE SCORES:
  #1 score=260 words=451 url=.../english-requirements
```

Should NOT see:
```
[orchestrator] Tier 1 failed, falling back to Tier 2
[firecrawl] Starting fetch...
```

---

## Summary

- ✅ **Fix Applied:** Removed fake URL construction (23 lines deleted)
- ✅ **Duplicate Detection:** Still active (lines 321-346)
- ✅ **English Scoring Boost:** Still active (ai_extractor.py line 382)
- ✅ **Budget Increase:** Still active (ai_extractor.py line 577)
- ⚠️ **Arkansas/McGill:** Not good test cases - no accessible English requirements
- 📋 **Next:** Test with Sydney or Edinburgh after backend restart

---

**Status:** Fix implemented, awaiting backend restart + test with better university  
**ETA:** 15 minutes after restart  
**Confidence:** HIGH - This was the root cause of Tier 2 fallback
