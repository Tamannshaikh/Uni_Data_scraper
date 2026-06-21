# Strategic Optimization: Sitemap-Based Fast Path

## The Real Bottleneck (Not Network Failures)

### Current State (200s)
```
Stage 1: Collect 1300 candidates (896 postgrad + 404 undergrad)
Stage 2: Sample 300 randomly
Stage 3: Auto-confirm 54s (104/300)
Stage 4: Candidate fetch 86s (132/196)
Stage 5: Gemini classify ~60s+ (ongoing)
TOTAL: 200s+
```

### What's Wrong

**The pipeline treats all URLs equally:**
- `/study/masters/courses/list/11520/pgce-secondary-chemistry/` ← NEEDS NO CLASSIFICATION
- `/study/undergraduate/courses/2026/00675/bsocsc-politics/` ← IRRELEVANT FOR POSTGRAD

**Manchester already classified these URLs:**
- Sitemap path `/masters/courses/list/` = Masters program
- Sitemap path `/postgraduate-research/programmes/list/` = PhD program
- Sitemap path `/undergraduate/courses/` = NOT POSTGRAD

**Yet we're:**
1. Fetching undergraduate pages (waste)
2. Running Gemini on obvious masters/PhD URLs (waste)
3. Random sampling means missing high-confidence postgrad URLs (data loss)

---

## The Fix: Tiered Classification

### Tier 1: Sitemap Path Auto-Accept (0s, no fetch, no AI)

**Rule:** If sitemap path contains known program directories, auto-accept.

```python
POSTGRAD_SITEMAP_PATHS = [
    "/study/masters/courses/list/",
    "/study/masters/courses/",
    "/study/postgraduate-research/programmes/list/",
    "/study/postgraduate-research/programme",
    "/study/online-blended-learning/courses/",  # Often postgrad
]

def classify_by_sitemap_path(url: str, sitemap_parent: str) -> Optional[ProgramData]:
    """Instantly classify URLs from known program directories."""
    if any(path in sitemap_parent for path in POSTGRAD_SITEMAP_PATHS):
        # Extract program name from URL
        degree_level = infer_degree_level(url, sitemap_parent)
        program_name = extract_name_from_url(url)
        
        return {
            "program_name": program_name,
            "degree_level": degree_level,
            "url": url,
            "confidence": 0.99,  # Very high - university classified it
            "method": "sitemap_path"
        }
    return None
```

**Expected impact for Manchester:**
- 896 postgrad URLs instantly accepted
- 0 seconds
- 0 API calls
- 0 fetches

### Tier 2: URL Slug Auto-Accept (0s, no fetch, no AI)

**Rule:** If URL slug contains degree indicators, auto-accept.

```python
POSTGRAD_SLUG_PATTERNS = [
    "msc-", "ma-", "mba-", "llm-", "mphil-", "phd-",
    "pgce-", "pgdip-", "mres-", "med-", "meng-",
    "doctorate-", "dclinpsych-", "dedchpsy-"
]

def classify_by_url_slug(url: str) -> Optional[ProgramData]:
    """Classify based on degree abbreviation in URL."""
    url_lower = url.lower()
    
    for pattern in POSTGRAD_SLUG_PATTERNS:
        if pattern in url_lower:
            degree_level = map_slug_to_degree(pattern)
            program_name = extract_name_from_slug(url, pattern)
            
            return {
                "program_name": program_name,
                "degree_level": degree_level,
                "url": url,
                "confidence": 0.95,
                "method": "url_slug"
            }
    return None
```

**Example URLs that benefit:**
```
https://www.manchester.ac.uk/study/masters/courses/list/20967/msc-robotics/
→ Auto-accept: MSc Robotics

https://www.manchester.ac.uk/study/postgraduate-research/programmes/list/05305/phd-applied-mathematics/
→ Auto-accept: PhD Applied Mathematics

https://www.manchester.ac.uk/study/masters/courses/list/09644/llm-public-international-law/
→ Auto-accept: LLM Public International Law
```

### Tier 3: Pattern-Based Auto-Confirm (4s, lightweight fetch)

**Current implementation** - keep this for edge cases.

URLs that pass pattern matching but aren't Tier 1 or 2.

### Tier 4: Gemini Classification (1.5s per candidate)

**Only for ambiguous pages:**
```
/study/international/study-abroad-exchange/
/research-areas/
/funding/opportunities/
/faculty/profiles/
```

### Tier 5: Reject Immediately (0s)

**Rule:** If URL is obviously not a program, reject without processing.

```python
REJECT_PATTERNS = [
    "/study/undergraduate/courses/",  # Not postgrad
    "/news/", "/events/", "/about/",
    "/contact/", "/apply/", "/fees/",
    "/accommodation/", "/location/",
]

def should_reject_immediately(url: str) -> bool:
    """Reject URLs that are definitely not programs."""
    return any(pattern in url.lower() for pattern in REJECT_PATTERNS)
```

---

## Implementation Priority

### Priority 1: Add Sitemap Path Classification (HIGH IMPACT)

**Change `pipeline/program_discovery.py`:**

```python
def _classify_candidates_tiered(candidates: List[dict]) -> Tuple[List[ProgramData], List[str]]:
    """
    Tiered classification:
    - Tier 1: Sitemap path (instant)
    - Tier 2: URL slug (instant)
    - Tier 3: Pattern + fetch (current auto-confirm)
    - Tier 4: Gemini (expensive)
    """
    tier1_accepted = []
    tier2_accepted = []
    needs_further_classification = []
    rejected = []
    
    for candidate in candidates:
        url = candidate["url"]
        sitemap_parent = candidate.get("sitemap_parent", "")
        
        # Tier 1: Sitemap path
        result = classify_by_sitemap_path(url, sitemap_parent)
        if result:
            tier1_accepted.append(result)
            continue
        
        # Tier 2: URL slug
        result = classify_by_url_slug(url)
        if result:
            tier2_accepted.append(result)
            continue
        
        # Tier 5: Reject immediately
        if should_reject_immediately(url):
            rejected.append(url)
            continue
        
        # Tier 3 + 4: Need further classification
        needs_further_classification.append(url)
    
    logger.info(f"Tier 1 (sitemap path): {len(tier1_accepted)} auto-accepted")
    logger.info(f"Tier 2 (URL slug): {len(tier2_accepted)} auto-accepted")
    logger.info(f"Tier 5 (rejected): {len(rejected)} rejected")
    logger.info(f"Tiers 3+4 (need classification): {len(needs_further_classification)}")
    
    all_accepted = tier1_accepted + tier2_accepted
    return all_accepted, needs_further_classification
```

**Expected Manchester results:**
```
Tier 1 (sitemap path): 896 auto-accepted   ← 0s
Tier 2 (URL slug): 0 auto-accepted         ← Already caught by Tier 1
Tier 5 (rejected): 404 rejected            ← Undergrads
Tiers 3+4 (need classification): 0         ← Nothing left!
```

**Time:** <5s total (just URL parsing)

### Priority 2: Store Sitemap Parent During Collection

**Modify sitemap parsing to track parent path:**

```python
for loc in sitemap_locs:
    url = loc["url"]
    parent_dir = extract_parent_directory(url)
    
    candidates.append({
        "url": url,
        "sitemap_parent": parent_dir,  # ← Add this
        "source": "sitemap"
    })
```

### Priority 3: Update High-Confidence Patterns

**For Manchester-specific optimization:**

```python
_HIGH_CONFIDENCE_PATTERNS = [
    # Existing patterns...
    r"/study/masters/courses/",
    r"/study/postgraduate-research/",
    r"/study/online-blended-learning/",
]
```

---

## Expected Performance

### Current (200s+)
```
Sitemap collection:  ~5s
Auto-confirm:        54s (300 URLs)
Candidate fetch:     86s (196 URLs)
Gemini classify:    ~60s (132 URLs, 9 batches)
TOTAL:             205s
Programs found:    104 + Gemini results
```

### After Tier 1+2 (30s)
```
Sitemap collection:  ~5s
Tier 1 sitemap:      ~3s (896 URLs instant accept)
Tier 2 URL slug:     ~1s (0 URLs, already caught)
Tier 5 reject:       ~1s (404 undergrads rejected)
Tier 3 auto-confirm: ~10s (~20 ambiguous URLs)
Tier 4 Gemini:       ~10s (~10 ambiguous URLs, 1 batch)
TOTAL:              ~30s
Programs found:     896 + ~10 = 906
```

**Improvement: 85% faster (205s → 30s), 9× more programs found**

---

## Why This Works

### Manchester Has Structured Sitemaps

The university already did the classification work:

**Directory structure = program type:**
```
/masters/courses/list/         ← Masters programs
/postgraduate-research/        ← PhD/MPhil programs
/undergraduate/courses/        ← Bachelor's programs
/online-blended-learning/      ← Often postgrad
```

**We're re-classifying what's already classified.**

### URL Slugs Are Descriptive

Manchester includes degree abbreviations in URLs:
```
/msc-robotics/              ← MSc
/phd-applied-mathematics/   ← PhD
/llm-international-law/     ← LLM
/ma-politics/               ← MA
```

**The URL itself is the classification.**

### Current Approach is Blind

Random sampling means:
- Missing 596 of the 896 postgrad URLs (only using 300/1300)
- Processing 100+ undergrad URLs in that 300
- Running expensive Gemini on obvious masters/PhD pages

**We're working harder, not smarter.**

---

## Benefits Beyond Speed

### 1. More Complete Results
- Current: 104 programs (incomplete, hit time limit)
- After: 896+ programs (complete, structured)

### 2. Lower API Costs
- Current: ~15-20 Gemini API calls per discovery
- After: ~1-2 Gemini API calls (only ambiguous cases)

### 3. More Reliable
- Sitemap-based classification doesn't depend on:
  - Network conditions
  - Page load times
  - Gemini API availability

### 4. Easier to Debug
- Clear tier separation
- Each tier logged separately
- Can measure tier effectiveness

### 5. Scales to Other Universities

Many universities use similar structures:
- `/graduate/programs/`
- `/academics/graduate/`
- `/programs/masters/`

Tier 1 patterns are reusable.

---

## Implementation Steps

### Step 1: Add Sitemap Parent Tracking (15 min)
Modify sitemap collection to store parent directory.

### Step 2: Implement Tiered Classification (30 min)
Add `classify_by_sitemap_path()` and `classify_by_url_slug()`.

### Step 3: Update Main Flow (15 min)
Call tiered classification before current auto-confirm logic.

### Step 4: Test on Manchester (5 min)
Should complete in ~30s with 896+ programs.

### Step 5: Measure and Document (15 min)
Compare before/after metrics.

**Total implementation time: ~75 minutes**
**Expected speedup: 85% (205s → 30s)**
**Expected completeness: 9× more programs (104 → 906)**

---

## Risk Mitigation

### What Could Go Wrong?

1. **Sitemap paths might not always indicate program type**
   - Mitigation: Log rejected URLs for manual review
   - Mitigation: Add validation check (spot-check 10 URLs)

2. **URL slugs might be ambiguous**
   - Example: `med-psychology` could be MEd or Medical
   - Mitigation: Context from sitemap parent
   - Mitigation: Fall back to Tier 3/4 if uncertain

3. **Missing legitimate programs**
   - Mitigation: Log all rejected URLs
   - Mitigation: Keep Tier 3+4 as fallback

### Validation Strategy

**Before deploying:**
1. Run on Manchester with logging
2. Spot-check 20 Tier 1 accepted programs
3. Spot-check 20 Tier 5 rejected URLs
4. Compare program count to current method

**Success criteria:**
- ✅ Tier 1 precision > 95% (spot-check)
- ✅ Tier 5 recall > 95% (no postgrads rejected)
- ✅ Total runtime < 60s
- ✅ Programs found > 800

---

## Next Action

**Implement Tier 1 (sitemap path classification) first.**

This alone should catch 896/1300 (69%) of Manchester's URLs instantly and reduce runtime to ~60s.

Then measure impact before implementing other tiers.

**Quick prototype (5 minutes):**

```python
# Add to beginning of Stage 3 in program_discovery.py
logger.info("[program_discovery] Testing Tier 1 classification...")

tier1_count = sum(
    1 for c in candidates 
    if "/study/masters/courses/" in c.get("url", "")
    or "/study/postgraduate-research/" in c.get("url", "")
)

logger.info(f"[program_discovery] Tier 1 would instantly accept {tier1_count}/{len(candidates)} candidates")
```

Run this on Manchester to confirm the 896 number, then implement full tier logic.

