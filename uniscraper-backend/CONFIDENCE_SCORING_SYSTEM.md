# Confidence-Based URL Scoring System

## The Right Approach

**Instead of:** Hard tiers (accept/reject)  
**Use:** Confidence scoring (0.0 to 1.0)

Then:
- **confidence > 0.95**: Skip fetch + Gemini, auto-accept
- **confidence 0.7-0.95**: Lightweight fetch + pattern validation
- **confidence < 0.7**: Full Gemini classification

## Confidence Scoring Components

### Component 1: Sitemap Path Score (0.0 to 0.7)

**High confidence paths:**
```python
POSTGRAD_SITEMAP_SIGNALS = {
    "/study/masters/courses/": 0.7,
    "/study/postgraduate-research/programmes/": 0.7,
    "/study/postgraduate/": 0.6,
    "/study/online-blended-learning/": 0.4,  # Mixed
    "/graduate/programs/": 0.7,
    "/academics/graduate/": 0.6,
}

UNDERGRAD_SITEMAP_SIGNALS = {
    "/study/undergraduate/courses/": -0.7,  # Negative signal
    "/undergraduate/": -0.5,
}

NON_PROGRAM_SIGNALS = {
    "/research-areas/": -0.3,
    "/funding/": -0.4,
    "/faculty/": -0.5,
    "/admissions/": -0.4,
}
```

**Example:**
```
/study/masters/courses/list/20967/msc-robotics/
→ sitemap_score = 0.7

/study/postgraduate-research/programmes/research-areas/
→ sitemap_score = 0.7 + (-0.3) = 0.4  ← Needs validation!

/study/undergraduate/courses/2026/00675/bsocsc-politics/
→ sitemap_score = -0.7 (if postgrad_only mode)
```

### Component 2: URL Slug Score (0.0 to 0.3)

**Degree indicators in URL:**
```python
DEGREE_SLUG_PATTERNS = {
    # Research degrees
    "phd-": 0.3,
    "mphil-": 0.3,
    "mres-": 0.25,
    "dphil-": 0.3,
    
    # Taught masters
    "msc-": 0.3,
    "ma-": 0.25,  # Could be undergrad at some unis
    "mba-": 0.3,
    "llm-": 0.3,
    "meng-": 0.25,
    "mfin-": 0.3,
    "med-": 0.25,
    "mpharm-": 0.25,
    
    # Professional
    "pgce-": 0.3,
    "pgdip-": 0.25,
    
    # Undergrad (negative)
    "bsc-": -0.3,
    "ba-": -0.25,
    "beng-": -0.3,
    "llb-": -0.25,
}
```

**Example:**
```
/study/masters/courses/list/20967/msc-robotics/
→ slug_score = 0.3

/study/undergraduate/courses/2027/03927/meng-mechatronic-engineering/
→ slug_score = 0.25 (but sitemap is negative, so net low)
```

### Component 3: Directory Depth Score (0.0 to 0.05)

**Programs are usually in deeper paths:**
```python
def directory_depth_score(url: str) -> float:
    """Programs usually have ID/slug at end of path."""
    path_segments = urlparse(url).path.strip('/').split('/')
    
    if len(path_segments) >= 5:  # e.g., /study/masters/courses/list/20967/
        return 0.05
    elif len(path_segments) >= 4:
        return 0.03
    return 0.0
```

**Example:**
```
/study/masters/courses/list/20967/msc-robotics/
→ 6 segments → 0.05

/study/masters/
→ 2 segments → 0.0
```

### Component 4: Keyword Score (0.0 to 0.05)

**Program-related keywords in URL:**
```python
PROGRAM_KEYWORDS = [
    "program", "course", "degree", 
    "study", "qualification"
]

def keyword_score(url: str) -> float:
    """Presence of program keywords."""
    url_lower = url.lower()
    matches = sum(1 for kw in PROGRAM_KEYWORDS if kw in url_lower)
    return min(matches * 0.02, 0.05)
```

### Total Confidence Calculation

```python
def calculate_url_confidence(
    url: str,
    sitemap_parent: str,
    discovery_mode: str = "postgrad_only"
) -> float:
    """
    Calculate confidence that URL is a program page.
    
    Returns:
        0.0 to 1.0 confidence score
    """
    confidence = 0.0
    
    # Component 1: Sitemap path (0.0 to 0.7)
    confidence += sitemap_path_score(sitemap_parent, discovery_mode)
    
    # Component 2: URL slug (0.0 to 0.3)
    confidence += url_slug_score(url)
    
    # Component 3: Directory depth (0.0 to 0.05)
    confidence += directory_depth_score(url)
    
    # Component 4: Keywords (0.0 to 0.05)
    confidence += keyword_score(url)
    
    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, confidence))
```

### Example Scores

```python
# High confidence - no validation needed
"/study/masters/courses/list/20967/msc-robotics/"
→ 0.7 (sitemap) + 0.3 (slug) + 0.05 (depth) + 0.02 (keywords) = 1.07 → 1.0

# Medium confidence - needs lightweight validation
"/study/postgraduate-research/programmes/research-areas/"
→ 0.7 (sitemap) + 0.0 (slug) - 0.3 (non-program) + 0.03 (depth) = 0.43

# Low confidence - needs Gemini
"/study/international/study-abroad-exchange/programmes/"
→ 0.0 (sitemap) + 0.0 (slug) + 0.05 (depth) + 0.02 (keywords) = 0.07

# Reject immediately
"/study/undergraduate/courses/2026/00675/bsocsc-politics/" (if postgrad_only)
→ -0.7 (sitemap) + (-0.3) (slug) = -1.0
```

---

## Processing Pipeline

### Step 1: Score All Candidates

```python
def score_candidates(
    candidates: List[dict],
    discovery_mode: str = "postgrad_only"
) -> List[dict]:
    """Add confidence score to each candidate."""
    for candidate in candidates:
        url = candidate["url"]
        sitemap_parent = candidate.get("sitemap_parent", "")
        
        candidate["confidence"] = calculate_url_confidence(
            url, sitemap_parent, discovery_mode
        )
    
    return candidates
```

### Step 2: Priority Queue (Not Random Sampling!)

```python
def prioritize_candidates(
    candidates: List[dict],
    limit: int = 500
) -> List[dict]:
    """Sort by confidence, take top N."""
    
    # Remove negative confidence (definitely not programs)
    valid = [c for c in candidates if c["confidence"] > 0.0]
    
    # Sort by confidence descending
    valid.sort(key=lambda c: c["confidence"], reverse=True)
    
    # Take top N
    return valid[:limit]
```

**No more random sampling throwing away 644 masters URLs!**

### Step 3: Classification Strategy

```python
def classify_by_confidence(candidates: List[dict]) -> Tuple[List[Program], List[str]]:
    """
    Classify based on confidence thresholds.
    """
    auto_accepted = []
    needs_validation = []
    needs_gemini = []
    
    for candidate in candidates:
        url = candidate["url"]
        confidence = candidate["confidence"]
        
        if confidence > 0.95:
            # High confidence - auto-accept without fetch
            program = create_program_from_url(url, confidence)
            auto_accepted.append(program)
            
        elif confidence > 0.70:
            # Medium confidence - lightweight validation
            needs_validation.append(url)
            
        else:
            # Low confidence - need Gemini
            needs_gemini.append(url)
    
    logger.info(f"Auto-accepted (>0.95): {len(auto_accepted)}")
    logger.info(f"Needs validation (0.7-0.95): {len(needs_validation)}")
    logger.info(f"Needs Gemini (<0.7): {len(needs_gemini)}")
    
    return auto_accepted, needs_validation, needs_gemini
```

---

## Expected Manchester Results

### With Confidence Scoring

```python
Input: 1300 candidates

After scoring:
  confidence > 0.95:  ~800 URLs  (sitemap + slug match)
  confidence 0.7-0.95: ~100 URLs  (sitemap match, no slug)
  confidence < 0.7:     ~50 URLs  (ambiguous)
  confidence < 0.0:    ~350 URLs  (undergraduate, rejected)

Processing:
  Auto-accept:         800 URLs  (0s)
  Lightweight validate: 100 URLs  (10s)
  Gemini classify:       50 URLs  (50s)
  
Total time: ~60s
Programs found: 800 + 80 + 40 = 920
```

### Current Approach

```
Input: 1300 candidates

After random sampling:
  Selected: 300 (random mix of high/low confidence)
  Discarded: 1000 (including ~500 high-confidence postgrad URLs!)

Processing:
  Auto-confirm:  300 URLs (54s)
  Candidate fetch: 196 URLs (86s)
  Gemini: 132 URLs (60s)
  
Total time: 200s
Programs found: 104 + Gemini results (~140 total?)
```

**Confidence-based: 6.5× more programs in 1/3 the time**

---

## Implementation

### Priority 1: Add Confidence Scoring (30 min)

Create `pipeline/confidence_scorer.py`:

```python
"""URL confidence scoring for program discovery."""

from typing import Dict, List
from urllib.parse import urlparse

# Sitemap path signals
POSTGRAD_SITEMAP_SIGNALS = {
    "/study/masters/courses/": 0.7,
    "/study/postgraduate-research/programmes/": 0.7,
    "/study/postgraduate/": 0.6,
    "/graduate/programs/": 0.7,
    "/academics/graduate/": 0.6,
    "/study/online-blended-learning/": 0.4,
}

UNDERGRAD_SITEMAP_SIGNALS = {
    "/study/undergraduate/courses/": -0.7,
    "/undergraduate/": -0.5,
    "/college/": -0.4,
}

NON_PROGRAM_SIGNALS = {
    "/research-areas/": -0.3,
    "/funding/": -0.4,
    "/faculty/": -0.5,
    "/admissions/": -0.4,
    "/staff/": -0.5,
    "/news/": -0.5,
    "/events/": -0.5,
}

# URL slug patterns
DEGREE_SLUG_PATTERNS = {
    # Research
    "phd-": 0.3, "mphil-": 0.3, "mres-": 0.25, "dphil-": 0.3,
    # Taught masters
    "msc-": 0.3, "ma-": 0.25, "mba-": 0.3, "llm-": 0.3,
    "meng-": 0.25, "mfin-": 0.3, "med-": 0.25,
    # Professional
    "pgce-": 0.3, "pgdip-": 0.25, "pgcert-": 0.2,
    # Undergrad (negative)
    "bsc-": -0.3, "ba-": -0.25, "beng-": -0.3, "llb-": -0.25,
}

def calculate_url_confidence(
    url: str,
    sitemap_parent: str = "",
    discovery_mode: str = "postgrad_only"
) -> float:
    """Calculate confidence that URL is a program page (0.0 to 1.0)."""
    confidence = 0.0
    url_lower = url.lower()
    parent_lower = sitemap_parent.lower()
    
    # Component 1: Sitemap path score
    for pattern, score in POSTGRAD_SITEMAP_SIGNALS.items():
        if pattern in parent_lower:
            confidence += score
            break
    
    # Negative signals
    if discovery_mode == "postgrad_only":
        for pattern, score in UNDERGRAD_SITEMAP_SIGNALS.items():
            if pattern in parent_lower or pattern in url_lower:
                confidence += score
                break
    
    for pattern, score in NON_PROGRAM_SIGNALS.items():
        if pattern in url_lower:
            confidence += score
            break
    
    # Component 2: URL slug score
    for pattern, score in DEGREE_SLUG_PATTERNS.items():
        if pattern in url_lower:
            confidence += score
            break
    
    # Component 3: Directory depth
    path_segments = urlparse(url).path.strip('/').split('/')
    if len(path_segments) >= 5:
        confidence += 0.05
    elif len(path_segments) >= 4:
        confidence += 0.03
    
    # Component 4: Keywords
    PROGRAM_KEYWORDS = ["program", "course", "degree"]
    matches = sum(1 for kw in PROGRAM_KEYWORDS if kw in url_lower)
    confidence += min(matches * 0.02, 0.05)
    
    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, confidence))
```

### Priority 2: Replace Random Sampling (15 min)

In `program_discovery.py`, replace:

```python
# OLD
candidates = random.sample(all_candidates, min(300, len(all_candidates)))
```

With:

```python
# NEW
from pipeline.confidence_scorer import calculate_url_confidence

# Score all candidates
for candidate in all_candidates:
    candidate["confidence"] = calculate_url_confidence(
        url=candidate["url"],
        sitemap_parent=candidate.get("sitemap_parent", ""),
        discovery_mode="postgrad_only"
    )

# Filter and prioritize
valid_candidates = [c for c in all_candidates if c["confidence"] > 0.0]
valid_candidates.sort(key=lambda c: c["confidence"], reverse=True)

# Take top 500 (not random 300!)
candidates = valid_candidates[:500]

logger.info(f"Confidence distribution:")
logger.info(f"  >0.95: {sum(1 for c in candidates if c['confidence'] > 0.95)}")
logger.info(f"  0.7-0.95: {sum(1 for c in candidates if 0.7 < c['confidence'] <= 0.95)}")
logger.info(f"  <0.7: {sum(1 for c in candidates if c['confidence'] <= 0.7)}")
```

### Priority 3: Confidence-Based Classification (30 min)

Update Stage 3 to skip fetch/Gemini for high confidence:

```python
# After scoring, separate by confidence
auto_accepted = []
needs_validation = []
needs_gemini = []

for candidate in candidates:
    confidence = candidate.get("confidence", 0.0)
    url = candidate["url"]
    
    if confidence > 0.95:
        # Auto-accept without fetch/Gemini
        program = {
            "program_name": extract_name_from_url(url),
            "degree_level": infer_degree_from_url(url),
            "url": url,
            "confidence": confidence,
            "method": "confidence_auto"
        }
        auto_accepted.append(program)
    elif confidence > 0.70:
        needs_validation.append(url)
    else:
        needs_gemini.append(url)

logger.info(f"Auto-accepted (confidence >0.95): {len(auto_accepted)}")
logger.info(f"Needs validation (0.7-0.95): {len(needs_validation)}")
logger.info(f"Needs Gemini (<0.7): {len(needs_gemini)}")

# Process needs_validation with current auto-confirm logic
# Process needs_gemini with Gemini
```

---

## Configuration

Make discovery mode configurable:

```python
# In discovery request
{
    "university_name": "University of Manchester",
    "discovery_mode": "postgrad_only"  # or "all" or "undergrad_only"
}
```

---

## Benefits

### 1. **Robust Across Universities**

Confidence scoring works even when structure differs:
- MIT: `/academics/graduate/programs/`
- Stanford: `/programs/graduate/`
- Edinburgh: `/postgraduate/taught/`

Just add patterns to the registry.

### 2. **Graceful Degradation**

No hard failures. Even with wrong patterns:
- URL still gets scored 0.0-0.4
- Falls through to Gemini
- Gemini handles it

### 3. **Debuggable**

Can inspect why URL got high/low confidence:
```
URL: /study/masters/courses/list/20967/msc-robotics/
  sitemap: +0.7
  slug: +0.3
  depth: +0.05
  keywords: +0.02
  TOTAL: 1.07 → 1.0
```

### 4. **Tunable**

Can adjust thresholds:
- Conservative: 0.98 auto-accept, 0.85 validate
- Aggressive: 0.90 auto-accept, 0.60 validate

### 5. **Measurable**

Can track precision by confidence band:
- 0.95-1.0: 99% precision
- 0.70-0.95: 85% precision
- 0.0-0.70: 60% precision (needs Gemini)

---

## Testing Strategy

### Phase 1: Measure Without Changing Behavior

Add scoring but keep current logic:

```python
# Score for measurement only
for candidate in candidates:
    candidate["confidence"] = calculate_url_confidence(...)
    
logger.info("Confidence analysis (not used yet):")
logger.info(f"  Would auto-accept: {sum(1 for c in candidates if c['confidence'] > 0.95)}")
logger.info(f"  Would validate: {sum(1 for c in candidates if 0.7 < c['confidence'] <= 0.95)}")
```

Run on Manchester. Verify ~800 would be auto-accepted.

### Phase 2: Enable for High Confidence Only

Only auto-accept >0.98 confidence:

```python
if confidence > 0.98:
    auto_accept()
else:
    existing_logic()
```

Spot-check 20 auto-accepted programs.

### Phase 3: Full Rollout

Enable all confidence thresholds.

---

## Expected Results

**Manchester with confidence scoring:**

```
1300 candidates scored
800 confidence >0.95 (auto-accept, 0s)
100 confidence 0.7-0.95 (validate, 10s)
50 confidence <0.7 (Gemini, 50s)
350 confidence <0 (rejected)

Total time: 60s
Programs found: 800 + 80 + 40 = 920
```

**vs current (random sampling):**

```
1300 candidates
300 random sample (discards 1000!)
54s auto-confirm
86s candidate fetch
60s Gemini

Total time: 200s
Programs found: ~140
```

**Improvement: 6.5× more programs, 3× faster**

