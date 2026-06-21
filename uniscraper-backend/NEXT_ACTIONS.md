# Immediate Next Actions

**Date**: June 21, 2026  
**Context**: Manchester is production-ready, broader generalization needs work

---

## Priority 1: Re-run Arkansas (5 minutes)

**Goal**: Verify the tuple unpacking fix works

```bash
cd c:\Projects\uniscrape\uniscraper-backend
.\venv\Scripts\python.exe -c "
import asyncio
from pipeline.program_discovery import discover_programs

async def test():
    programs = await discover_programs(
        domain='astate.edu',
        university_name='Arkansas State University',
        max_programs=500
    )
    print(f'Programs found: {len(programs)}')
    
asyncio.run(test())
"
```

**Expected**: 50-100 programs in ~5 minutes  
**Success criteria**: No crash, >50 programs returned

---

## Priority 2: Expand Slug Patterns (30 minutes)

**Problem**: Arkansas only got 9 slug confirmations (vs Manchester's 538)

**File**: `pipeline/program_discovery.py`  
**Function**: `_has_obvious_degree_slug()`

### Current patterns (Manchester-optimized):
```python
degree_slugs = [
    "msc-", "ma-", "mba-", "mres-", "mph-", "mphil-",
    "phd-", "llm-", "pgce-", "engd-",
]
```

### Expanded patterns (broader coverage):
```python
DEGREE_SLUG_PATTERNS = [
    # Master's programs
    r'/msc-', r'/ma-', r'/mba-', r'/mfa-', r'/mph-', 
    r'/mres-', r'/mphil-', r'/llm-', r'/mpa-', r'/mlis-',
    r'/msw-', r'/march-', r'/med-', r'/mat-',
    
    # With "in" variants
    r'/ma-in-', r'/ms-in-', r'/msc-in-', r'/mba-in-',
    
    # Doctoral programs
    r'/phd-', r'/phd-in-', r'/doctorate-', r'/dba-',
    r'/edd-', r'/dnp-', r'/dmin-', r'/dpt-',
    
    # Certificates
    r'/pgce-', r'/pgcert-', r'/pgdip-',
    r'/graduate-certificate-', r'/grad-cert-',
    r'/post-masters-', r'/post-baccalaureate-',
    
    # Graduate programs
    r'/graduate-program', r'/grad-program',
    r'/master-of-', r'/doctor-of-',
]
```

### Implementation:
```python
def _has_obvious_degree_slug(url: str) -> tuple[bool, str]:
    """
    Check if URL slug contains obvious degree program identifiers.
    Returns (has_slug, matched_pattern).
    """
    import re
    
    url_lower = url.lower()
    
    for pattern in DEGREE_SLUG_PATTERNS:
        if re.search(pattern, url_lower):
            return (True, pattern)
    
    return (False, "")
```

**Expected impact**:
- Arkansas: 9 → 200+ slug confirmations
- Arkansas runtime: 318s → ~100s
- Gemini candidates: 368 → ~50

---

## Priority 3: Add Sibling Expansion Guard (15 minutes)

**Problem**: Arkansas launched 391 sibling candidates after already finding 52 programs

**File**: `pipeline/program_discovery.py`  
**Location**: Around line 1547 (before Stage 4)

### Add early-stop threshold:
```python
logger.info(f"[program_discovery] Stage 3: {len(confirmed)} programs confirmed")

# ── Stage 4: Sibling expansion (with early-stop guard) ────────────────────
SIBLING_THRESHOLD = max_programs * 0.2  # 20% of cap

if len(confirmed) >= SIBLING_THRESHOLD:
    logger.info(
        f"[program_discovery] Skipping sibling expansion: "
        f"{len(confirmed)} programs already found (threshold={SIBLING_THRESHOLD})"
    )
else:
    logger.info(
        f"[program_discovery] Starting sibling expansion: "
        f"{len(confirmed)} programs found (threshold={SIBLING_THRESHOLD})"
    )
    siblings_result = await sibling_expansion(confirmed, domain, university_name)
    siblings = siblings_result[0] if isinstance(siblings_result, tuple) else siblings_result
    if siblings:
        logger.info(f"[program_discovery] Stage 4: {len(siblings)} additional siblings")
        confirmed = confirmed + siblings
```

**Expected impact**:
- Save 100+ seconds on universities that already have many programs
- Prevent wasted processing after hitting 20% of cap

---

## Priority 4: Debug Arkansas Extraction Failures (60 minutes)

**Problem**: 329/368 URLs (89%) returning `no_content` despite `HTTP 200 OK`

### Investigation steps:

1. **Pick sample URLs** (from logs):
```python
test_urls = [
    "https://www.astate.edu/programs/minor-in-english.html",
    "https://www.astate.edu/programs/bs-in-public-health.html",
    "https://www.astate.edu/programs/mm-in-music-composition.html",
    "https://www.astate.edu/programs/msa-in-agriculture.html",
    "https://www.astate.edu/programs/certificate-in-computed-tomography.html",
]
```

2. **Test extraction manually**:
```python
# File: test_arkansas_extraction.py
import asyncio
from pipeline.fetcher import _fetch_html
from pipeline.program_discovery import _get_title, _get_snippet, _word_count

async def test_extraction(url: str):
    print(f"\n{'='*80}")
    print(f"Testing: {url}")
    print(f"{'='*80}")
    
    html, status = await _fetch_html(url, timeout=10.0)
    
    print(f"Status: {status}")
    print(f"HTML length: {len(html) if html else 0}")
    print(f"Word count: {_word_count(html) if html else 0}")
    
    if html:
        title = _get_title(html)
        snippet = _get_snippet(html, max_words=100)
        
        print(f"Title: {title}")
        print(f"Snippet: {snippet[:200]}...")
    else:
        print("ERROR: No HTML content extracted")

async def main():
    test_urls = [
        "https://www.astate.edu/programs/minor-in-english.html",
        "https://www.astate.edu/programs/mm-in-music-composition.html",
    ]
    
    for url in test_urls:
        await test_extraction(url)

asyncio.run(main())
```

3. **Check for issues**:
- Is Crawl4AI returning content?
- Is content validation too strict (< 50 words)?
- Is JavaScript rendering needed?
- Are redirects being followed?

4. **Possible fixes**:

**Option A**: Lower word count threshold for Arkansas
```python
# In _fetch_html or fetch_candidate_info
if _word_count(html) < 30:  # Changed from 50
    return None
```

**Option B**: Use different extraction method
```python
# Try raw HTML parsing instead of Crawl4AI
from bs4 import BeautifulSoup

def _extract_text_backup(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text(separator=' ', strip=True)
```

**Option C**: Add JavaScript rendering for Arkansas
```python
# If Arkansas needs browser rendering
if "astate.edu" in url:
    use_playwright = True
```

---

## Priority 5: Test Additional Universities (2-3 hours)

**Goal**: Verify patterns work across diverse structures

### Test suite (10 universities):

```python
# File: test_10_universities.py
UNIVERSITIES = [
    # Sitemap-rich
    ("ox.ac.uk", "University of Oxford"),
    ("cam.ac.uk", "University of Cambridge"),
    ("stanford.edu", "Stanford University"),
    
    # Bot-protected
    ("imperial.ac.uk", "Imperial College London"),
    ("ucl.ac.uk", "University College London"),
    
    # Distributed
    ("harvard.edu", "Harvard University"),
    ("yale.edu", "Yale University"),
    
    # State schools
    ("umich.edu", "University of Michigan"),
    ("berkeley.edu", "UC Berkeley"),
    ("arizona.edu", "University of Arizona"),
]
```

### Success criteria:
- 7/10 universities return >100 programs
- Median time < 120s
- Average extraction failure rate < 30%

---

## Timeline

### Today (2-3 hours):
- ✅ Fix Arkansas bug (done)
- 🔄 Re-run Arkansas (5 min)
- 🔄 Expand slug patterns (30 min)
- 🔄 Add sibling guard (15 min)
- 🔄 Debug extraction (60 min)

### Tomorrow (3-4 hours):
- Test 10 universities
- Analyze failure patterns
- Document findings

### After 10-university test:
- **If 7+/10 succeed** → Call discovery production-ready
- **If <7/10 succeed** → Identify remaining gaps, fix, re-test

---

## Success Metrics (Revised)

### Manchester-like universities:
- ✅ <60s discovery time
- ✅ 500+ programs
- ✅ >90% auto-confirm
- ✅ <20 Gemini candidates

### Other universities (new targets):
- ⏳ <120s discovery time
- ⏳ >100 programs
- ⏳ >50% auto-confirm
- ⏳ <100 Gemini candidates

### Cross-university (aggregate):
- ⏳ 70% success rate (7/10 universities)
- ⏳ Median time <90s
- ⏳ Average extraction failure rate <30%

---

## When to Call Discovery "Done"

### Minimum criteria:
1. ✅ Manchester validated (done)
2. ⏳ Arkansas working (bug fixed, needs re-test)
3. ⏳ 10-university test: 7/10 success
4. ⏳ Slug patterns generalize (tested on diverse URLs)
5. ⏳ Extraction failure rate <30%
6. ⏳ Documented failure modes (bot protection, distributed, etc.)

### Then and only then:
> "Discovery pipeline is production-ready and validated across diverse university structures."

**We're close, but not quite there yet.**

---

## Final Notes

**What we've achieved so far is huge**:
- Manchester: 95% faster, 5x more programs
- Slug-based auto-confirmation works brilliantly
- Architecture is sound and extensible

**What remains**:
- Pattern vocabulary needs broadening
- Extraction reliability needs improvement
- Cross-university validation needs completion

**This is normal.** Going from "works perfectly on one university" to "works well on many" is always the hardest part.

Manchester proves the approach works. Now we need to generalize it.
