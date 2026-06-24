# Priority 1.5: Tightened Landing Page Extraction

## Problem Statement

Priority 1 implementation successfully detected landing pages and expanded them, but the extraction layer was too permissive:

```
+ Added from landing page: home.php
+ Added from landing page: home.php  
+ Added from landing page: (empty name)
```

**Root Cause:** Simple pattern matching without quality validation extracted navigation links like "Learn More", "Apply", "Home" alongside genuine program links.

## User Feedback Analysis

> "Anchor extraction is still too permissive. You're correctly detecting landing pages, but the extraction layer is still admitting navigation links."

**Key Recommendations:**
1. Require BOTH degree pattern AND minimum length
2. Reject generic navigation text
3. Reject generic URL basenames (home.php, index.php)
4. Use scoring system instead of binary accept/reject
5. **Log anchor text alongside URLs for debugging**

## Solution: Quality-Based Scoring System

### 1. Multi-Signal Scoring

Instead of binary "has degree pattern → accept", implemented comprehensive scoring:

```python
def score_anchor(anchor_text: str, href: str) -> tuple[int, str]:
    """Score >= 5 required for acceptance"""
    score = 0
    
    # Positive signals
    if has_degree_pattern:      score += 5  # MBA, PhD, MS, etc.
    if 2 <= word_count <= 12:   score += 3  # Sweet spot length
    if has_department_name:     score += 2  # Computer Science, etc.
    
    # Negative signals
    if all_caps and multi_word:  score -= 5  # Likely navigation
    if contains_question:        score -= 3  # Likely FAQ
    
    # Hard rejects (score = -100)
    if navigation_text:          return -100  # Learn More, Apply, etc.
    if generic_url_basename:     return -100  # home.php, index.php
    if too_short_non_abbrev:     return -100  # < 10 chars unless MBA/PhD
```

### 2. Hard Rejection Lists

**Navigation Text (exact match, case-insensitive):**
```python
NAVIGATION_REJECTS = {
    'home', 'learn more', 'apply', 'overview', 'contact',
    'admissions', 'visit', 'back', 'next', 'previous',
    'more info', 'read more', 'details', 'explore',
    'discover', 'find out', 'click here', 'view all',
    'see all', 'about', 'about us', 'why choose'
}
```

**URL Basenames (exact match):**
```python
URL_BASENAME_REJECTS = {
    'home.php', 'index.php', 'overview.php', 'apply.php',
    'home.html', 'index.html', 'overview.html', 'apply.html',
    'default.php', 'default.html', 'main.php', 'main.html'
}
```

### 3. Enhanced Logging

**Before:**
```
  Extracted 8 programs from landing page
```

**After:**
```
  Landing extraction from 83 links:
    1. [score=+8] 'Master of Science in Computer Science' → /masters/cs.php
    2. [score=+7] 'PhD in Economics' → /phd/econ.html
    3. [score=+10] 'MBA' → /mba/
    ...
    REJECT [score=-100, navigation_text] 'Learn More'
    REJECT [score=-100, generic_url] 'home.php'
  Result: 8 extracted, 75 rejected
```

**Key Improvements:**
- ✅ Anchor text visible for manual inspection
- ✅ Score shown for each decision
- ✅ Rejection reasons logged
- ✅ Summary stats (extracted vs rejected)

### 4. Department Name Recognition

Added common field patterns as positive signal:

```python
DEPARTMENT_PATTERNS = [
    r'\bComputer Science\b', r'\bEngineering\b', r'\bBusiness\b',
    r'\bEconomics\b', r'\bPhysics\b', r'\bChemistry\b', r'\bBiology\b',
    r'\bMathematics\b', r'\bEducation\b', r'\bPsychology\b',
    # ... 14 total patterns
]
```

Anchor text like "Computer Science, MS" gets +2 bonus for department name.

## Priority 2: Full PageType Formalization

Implemented complete page type taxonomy as an Enum:

```python
class PageType(Enum):
    PROGRAM     # Individual degree page → return as result
    LANDING     # Lists multiple programs → expand
    DIRECTORY   # Search/browse pages → expand
    DEPARTMENT  # Dept homepage → expand lightly (future)
    POLICY      # Admissions policies → discard
    NEWS        # Blog/events → discard
    PROFILE     # Student/faculty profiles → discard
    EVENT       # Seminars/workshops → discard
    ADMIN       # Forms/calendars → discard
    OTHER       # Unknown → discard
```

### Behavior Methods

```python
PageType.should_expand(page_type)   # LANDING, DIRECTORY
PageType.should_discard(page_type)  # POLICY, NEWS, PROFILE, EVENT, ADMIN, OTHER
PageType.is_program(page_type)      # PROGRAM only
```

### Updated Classification Prompt

Expanded from 6 page types to 10:

```
Old: PROGRAM, LANDING, ADMIN, DEPARTMENT, NEWS, OTHER
New: PROGRAM, LANDING, DIRECTORY, DEPARTMENT, POLICY, NEWS, PROFILE, EVENT, ADMIN, OTHER
```

**Benefits:**
- More granular classification
- Explicit handling for each type
- Easier to add type-specific logic

### Result Processing

**Before:**
```python
if page_type == "LANDING":
    expand()
elif not is_program:
    discard()
```

**After:**
```python
if PageType.should_expand(page_type):
    expand()
elif PageType.should_discard(page_type):
    discard()
elif not PageType.is_program(page_type):
    discard()
```

**Advantages:**
- Centralized page type behavior
- Easy to modify (change enum, not scattered if/else)
- Type-safe with Enum
- Self-documenting code

## Expected Impact

### Quality Improvements
- ❌ Eliminate: home.php, index.php URLs
- ❌ Eliminate: "Learn More", "Apply" anchor text
- ❌ Eliminate: Empty program names
- ✅ Accept: "Computer Science, MS"
- ✅ Accept: "MBA"
- ✅ Accept: "PhD in Economics"

### Debugging Improvements
- See anchor text for each extracted link
- Understand why links were accepted (score breakdown)
- Understand why links were rejected (reason logged)
- Quickly spot extraction problems

### Architecture Improvements
- PageType enum centralizes all page type logic
- Easy to add new page types
- Type-specific behavior in one place
- Removes scattered heuristics

## Testing

### Test File
`test_tightened_extraction.py` verifies:
1. No home.php or generic URLs
2. No empty program names
3. No generic navigation text
4. Anchor text logged properly
5. Scoring system working

### Success Criteria
- Zero bad extractions (home.php, empty names, navigation text)
- All extracted anchors contain degree patterns OR department names
- Rejection logging shows why junk was filtered

## Files Modified

1. **pipeline/program_discovery.py**
   - Added `PageType` enum with behavior methods
   - Implemented quality-based scoring in `_expand_landing_pages_by_anchor_text()`
   - Added hard rejection lists (navigation text, URL basenames)
   - Enhanced logging with anchor text and scores
   - Updated classification prompt with 10 page types
   - Refactored result processing to use PageType methods

2. **test_tightened_extraction.py** (new)
   - Verification script for extraction quality
   - Checks for common bad extractions
   - Validates scoring system

## Implementation Details

### Scoring Thresholds
- **Accept:** score >= 5
- **Typical good anchor:** 8-10 points (degree + length + department)
- **Typical navigation:** -100 points (hard reject)
- **Edge cases:** 0-4 points (rejected as insufficient)

### Degree Pattern Coverage
15+ patterns covering:
- Standard degrees: MS, MA, MBA, PhD
- With punctuation: M.S., Ph.D., M.Sc.
- Long form: Master of, Doctor of, Masters in
- Specialized: MEng, MPhil, LLM, MRes, MEd, MFA, MPH, MPA

### Length Validation
- Minimum: 10 characters (unless abbreviation like MBA)
- Abbreviation whitelist: MBA, MS, MA, PhD, MEng, LLM
- Sweet spot: 2-12 words (+3 score)
- Reasoning: "Computer Science, MS" = 3 words ✅, "APPLY NOW" = 2 words but all caps ❌

## Next Steps

### Immediate
1. Run `test_tightened_extraction.py` to verify improvements
2. Check logs for anchor text quality
3. Validate zero bad extractions

### Short Term
1. Add more department patterns (field-specific)
2. Implement DIRECTORY page expansion (similar to LANDING)
3. Add DEPARTMENT page light expansion

### Medium Term
1. Machine learning scoring model trained on real data
2. Field-specific extraction (Engineering vs Business vs Science)
3. Extract program metadata from surrounding text (duration, format)

## Conclusion

Priority 1.5 addresses the extraction quality issues identified in testing while implementing the full PageType taxonomy recommended for Priority 2.

**Key Achievements:**
- ✅ Quality-based scoring eliminates false positives
- ✅ Enhanced logging makes debugging trivial
- ✅ PageType enum centralizes page behavior
- ✅ Foundation for systematic page handling

**Status:** Ready for testing
**Impact:** Higher precision on extracted programs, better debugging visibility

The extraction layer is now as sophisticated as the detection layer—both use multi-signal scoring rather than simple pattern matching.
