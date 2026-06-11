# Bucket-Based Relevance Architecture

## The Problem with Top-N Selection

### Old Approach (Broken)
```python
pages = [page1, page2, ..., page20]
scores = [410, 390, 270, 250, 190, 150, ...]

# Pick TOP 3 for tuition_fees
selected = [page1, page2, page3]  # scores: 410, 390, 270
# Page4 (score=250) EXCLUDED despite being highly relevant

send_to_llm(selected)  # Missing information from page4!
```

### Why This Fails

**Scenario: Arkansas State MBA Tuition**

Pages discovered:
1. `/admissions-and-aid/tuition-and-fees/` (score=410) - "Graduate tuition: $590/credit hour"
2. `/tuition-and-fees/` (score=390) - "Resident: $530, Non-resident: $590"
3. `/study/fees-scholarships/` (score=270) - "Merit scholarships up to $5,000"
4. `/programs/mba/funding/` (score=250) - "Payment plans available"
5. `/programs/mba/fees/` (score=190) - "See university tuition page for rates"

**With TOP-3 limit:**
- Includes: 410, 390, 270
- Excludes: 250 (funding info), 190 (reference to main page)
- Result: LLM might miss funding options

**Why it's arbitrary:**
- Score difference 390→270 = 120 points (both included)
- Score difference 270→250 = 20 points (one excluded)
- The 20-point gap is SMALLER but triggers exclusion!

## The Bucket-Based Solution

### New Approach
```python
pages = [page1, page2, ..., page20]
scores = [410, 390, 270, 250, 190, 150, 80, 75, 50, ...]

# Define THRESHOLD (semantic meaning)
RELEVANCE_THRESHOLD = 80

# Include ALL pages above threshold
selected = [page1, page2, page3, page4, page7]  # scores >= 80
# Pages 5,6,7 excluded because score < 80 (actually irrelevant)

send_to_llm(selected)  # Complete information!
```

### Why This Works

**Same scenario with threshold approach:**

Pages:
1. score=410 → INCLUDED (>80) ✅
2. score=390 → INCLUDED (>80) ✅
3. score=270 → INCLUDED (>80) ✅
4. score=250 → INCLUDED (>80) ✅
5. score=190 → INCLUDED (>80) ✅
6. score=150 → INCLUDED (>80) ✅
7. score=75 → EXCLUDED (<80) ❌ (actually irrelevant)

**Result:** LLM sees complete picture from 6 relevant sources

## Architectural Principles

### 1. Scoring Determines Ordering, Not Exclusion

**Bad:**
```
if rank <= 3:  # Arbitrary limit
    include_page()
```

**Good:**
```
if score >= THRESHOLD:  # Semantic meaning
    include_page()
```

### 2. Let the LLM Synthesize

**Universities scatter information:**
- Main page: Base tuition
- International page: Additional fees
- Scholarship page: Funding options
- Deadlines page: Payment schedules

**Old approach:** Pick ONE page (incomplete)
**New approach:** Send ALL relevant pages (complete)

**LLMs are GOOD at:**
- Reading multiple sources
- Synthesizing information
- Handling redundancy
- Resolving contradictions

**LLMs are BAD at:**
- Knowing which single page is the "source of truth"

### 3. Threshold Has Semantic Meaning

```python
RELEVANCE_THRESHOLD = 80
```

**What this means:**
- score < 0: Actively harmful (visa, accommodation pages for tuition)
- score 0-50: Generic/neutral (homepage, about page)
- score 50-80: Somewhat relevant (might mention tuition in passing)
- score >= 80: Actually relevant (dedicated to the topic)
- score >= 200: Critical page (e.g., university-wide tuition page)

**Benefit:** Explicit semantic boundary, not arbitrary count

## Implementation

### Before (ai_extractor.py)
```python
def build_field_specific_context(...):
    scored = sorted(pages_by_score, reverse=True)
    
    max_pages = 5 if field_group == "tuition_fees" else 3  # ARBITRARY
    
    for score, page in scored:
        parts.append(page)
        if len(parts) >= max_pages:  # STOPS HERE
            break
```

**Problems:**
1. Why 3? Why 5? Why not 4 or 7?
2. What if 6 pages are all highly relevant?
3. What if only 2 pages are relevant but we force-include 3?

### After (ai_extractor.py)
```python
def build_field_specific_context(...):
    scored = sorted(pages_by_score, reverse=True)
    
    RELEVANCE_THRESHOLD = 80  # SEMANTIC
    
    for score, page in scored:
        if score < RELEVANCE_THRESHOLD:  # STOP AT THRESHOLD
            break
        if char_limit_reached:  # Only other stop condition
            break
        parts.append(page)
```

**Benefits:**
1. Threshold has semantic meaning (>=80 = relevant)
2. No artificial page limit
3. Stops only when content becomes irrelevant OR space runs out

## Logging Improvements

### Before
```
[RELEVANCE] tuition_fees: 3 pages, 8000 chars, top_score=410
```

**Questions this doesn't answer:**
- How many relevant pages were there?
- Did we exclude relevant pages due to limit?
- Were all 3 pages actually relevant?

### After
```
[ai_extractor] tuition_fees: included 5/7 relevant pages, 9850 chars, top_score=410
```

**What this tells us:**
- 7 pages scored >= 80 (all relevant)
- 5 fit in the char budget
- 2 relevant pages excluded (only due to space, not arbitrary limit)
- This is a REAL tradeoff (space constraint) vs artificial one

## Expected Outcomes

### 1. Better Extraction Quality

**Before:** Single page might have incomplete info
```json
{
  "tuition_domestic": "$530 per credit hour",
  "tuition_international": null,  // Was on page #4
  "scholarships": null             // Was on page #5
}
```

**After:** Multiple pages = complete picture
```json
{
  "tuition_domestic": "$530 per credit hour",
  "tuition_international": "$590 per credit hour",  // Found!
  "scholarships": "Merit scholarships up to $5,000"   // Found!
}
```

### 2. More Robust to Scoring Errors

**Scenario:** Scoring slightly mis-ranks pages

**Before (top-3):**
```
Page A: score=410 (has info) → included
Page B: score=390 (has info) → included  
Page C: score=270 (has info) → included
Page D: score=265 (CRITICAL INFO) → excluded  // 5 points difference!
```

**After (threshold):**
```
Page A: score=410 → included
Page B: score=390 → included
Page C: score=270 → included
Page D: score=265 → included  // Still above threshold!
```

### 3. Natural Adaptation to Content Structure

**University A:** Puts everything on one page
- Result: 1 page with score=400, rest below 80
- System includes only the 1 relevant page ✅

**University B:** Splits across 6 pages
- Result: 6 pages with scores 410, 390, 350, 300, 250, 200
- System includes all 6 relevant pages ✅

**The old max_pages=3 approach would fail for University B!**

## Testing the Change

### Before Fix
```
[RELEVANCE] tuition_fees: 1 pages, 5985 chars  (top: .../fees)
```

Only sent the program-specific `/fees` sub-page.

### After Fix (with scoring fix)
```
[ai_extractor] tuition_fees top pages:
  score=410 url=.../admissions-and-aid/tuition-and-fees words=708
  score=390 url=.../tuition-and-fees words=708
  score=270 url=.../study/fees-scholarships words=14590
  score=250 url=.../funding words=685
  score=190 url=.../fees words=685

[ai_extractor] tuition_fees: included 5/7 relevant pages, 9850 chars, top_score=410
```

Now sending 5 relevant pages totaling 9850 chars.

## Comparison with Original Request

### What User Wanted
> "The website will first access the root page, then look for sublinks or pages, 
> then inside them too access all the accessible links and subpages and go on 
> till we extract the relevant information"

**This is exactly the bucket approach:**
- Crawl discovers ALL relevant pages (not just one)
- Extraction uses ALL relevant pages (not just top 1)
- LLM synthesizes from complete information

### What Was Being Done (Before)
- Crawl: Found 50 pages ✅
- Scoring: Ranked them ✅
- Routing: Picked TOP 3 ❌ (arbitrary limit)
- Extraction: LLM never saw pages 4-7 ❌

### What Happens Now
- Crawl: Finds 20 pages (early exit) ✅
- Scoring: Ranks them ✅
- Routing: Picks ALL with score >= 80 ✅ (semantic threshold)
- Extraction: LLM sees complete picture ✅

## Why This Matters

### The Original Problem
Arkansas State: `tuition_domestic=null, tuition_international=null, tuition_notes="$30"`

**Root cause:** Tuition page was discovered but excluded from extraction context

### Why It Was Excluded
1. Scoring ranked it #2 or #3
2. Arbitrary page limit (3 or 5) cut it off
3. Despite being highly relevant (score ~250)

### How Bucket Approach Fixes This
1. Threshold = 80
2. Tuition page score = 250 (>>80)
3. Automatically included
4. LLM sees actual tuition information

## Conclusion

The bucket-based threshold approach is **architecturally superior** because:

1. ✅ **Semantic boundaries** (not arbitrary limits)
2. ✅ **Complete information** (all relevant pages included)
3. ✅ **Resilient to scoring errors** (small ranking mistakes don't exclude content)
4. ✅ **Adapts to content structure** (works for 1-page or 10-page universities)
5. ✅ **Matches LLM strengths** (synthesizing multiple sources)
6. ✅ **Better logging** (shows real tradeoffs)

**The principle:**
> "Scoring should determine ordering, not exclusion"

This change transforms the system from:
- **Fragile:** One wrong ranking = extraction fails
- **Robust:** Multiple sources = extraction succeeds

---

**Status:** ✅ Implemented  
**Commit:** `ec30aad` - Refactor: Bucket-based relevance architecture  
**Impact:** Higher extraction quality through information completeness
