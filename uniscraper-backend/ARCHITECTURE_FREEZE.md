# Architecture Freeze — Phase 1 Complete

**Date**: 2026-06-25  
**Status**: ✅ Foundation stable, ready to scale

---

## Current State

Four universities working cleanly with four different strategies:

| University | Strategy | Programs | Quality | Notes |
|---|---|---|---|---|
| Arkansas | `anchor` | 10 | 100% | Degree names in `<a>` text |
| UCSD | `plain_text_list` | 186 | 100% | Plain text bullets, no links |
| MIT | `table` | 46 | 100% | Table cells with links |
| Purdue | `heading` | 190 | 100% | H2 in `program-card` divs |

**Total programs extracted**: 432  
**Junk rate**: 0%

---

## Frozen Components

### 1. Extractor Functions (DO NOT MODIFY)

Five stable extractors in `pipeline/extractors.py`:

```python
def extract_anchor(base_url, container)
    # Degree names ARE the anchor text
    # Example: <a href="/programs/cs">MS Computer Science</a>
    
def extract_table(base_url, container)
    # Degree names in table cells (first column)
    # MIT pattern: rows with links = programs, bold-only = headers
    
def extract_heading(base_url, container)
    # Degree names in H2/H3 tags
    # Purdue pattern: scope to program-card divs first
    
def extract_plain_text_list(base_url, container)
    # Plain text list items with degree keywords
    # Returns catalog URL (no individual links)
    
def extract_heading_with_button(base_url, container)
    # Degree in heading, link in separate button
    # Currently unused but available
```

**Rule**: Do not modify these unless a specific university breaks. If a new structure appears, add a **new** extractor rather than generalizing an existing one.

### 2. Configuration Pattern

```python
UNIVERSITY_CONFIG = {
    "domain.edu": {
        "url": "https://...",
        "strategy": "anchor|table|heading|plain_text_list|playwright_table|playwright_anchor",
        "notes": "Human-readable description"
    }
}
```

No auto-detection. No confidence scores. Manual classification only.

### 3. Validation Process

After **every** change, run all 4 universities:

```bash
py -3.13 test_all_four_universities.py
```

Then **manually read** every extracted program. Counts are not evidence:

❌ **Not sufficient**: "Found 46 programs"  
✅ **Sufficient**:
```
1. Architecture
2. Aeronautics and Astronautics
3. Economics
4. MIT Sloan MBA Program
...
```

---

## What Was Proven

### 1. Structure-Specific Beats Universal

Four very different page structures, four different strategies, all working at 100% precision. No universal extractor attempted.

### 2. The Diagnosis → Implementation Gap Is Real

**MIT**: Correctly diagnosed as table, but `list_text` extractor was applied anyway → 40% junk  
**Purdue**: Content confirmed in static HTML, but concluded "needs Playwright" without re-verification → 0 programs

**Fix**: Build the extractor that matches the diagnosis, not the nearest existing tool.

### 3. "Needs Playwright" Was Premature

Purdue showed that:
- 54.1 KB static HTML fetch contained all program names
- "0 programs" meant wrong DOM selector, not missing content
- 190 programs extracted by targeting `program-card` divs

**Rule**: Re-fetch and manually inspect raw HTML before concluding JS-rendering is the problem.

### 4. Manual Verification Catches Everything

Both bugs would have been caught immediately if the full output had been printed and read:

- MIT: "Master's: July 1PhD: October 1" in the list
- Purdue: "Follow Us", "Exploreplus_icon" in the list

**Rule**: Print all extracted programs, read them, only then declare success.

---

## Process for Adding New Universities

### Step 1: Manual Inspection

1. Open the catalog page manually
2. Find one known degree program (e.g., "Computer Science MS")
3. Inspect the HTML around that program
4. Identify the structure:
   - Is the degree name in `<a>` text? → `anchor`
   - Is it in `<li>` or `<p>` plain text? → `plain_text_list`
   - Is it in a table cell? → `table`
   - Is it in `<h2>/<h3>`? → `heading`
   - Does the page have no content until JS runs? → `playwright_*`

### Step 2: Configure

Add to `UNIVERSITY_CONFIG.py`:

```python
"newuniversity.edu": {
    "url": "https://newuniversity.edu/programs",
    "strategy": "anchor",  # Based on Step 1
    "notes": "Degree names in anchor text, clean list"
}
```

### Step 3: Test

```bash
py -3.13 test_all_four_universities.py
```

This now tests **all configured universities** (including the new one).

### Step 4: Manual Verification

Read every single extracted program. Check for:
- Real degree/program names only
- No deadline text ("Master's: July 1")
- No nav menus ("Follow Us", "More Info")
- No UI elements ("Exploreplus_icon")
- No table headers ("Program", "Department")

If junk appears:
1. Inspect HTML around junk item
2. Identify why extractor captured it
3. Either:
   - Add filtering to existing extractor (if same structure, different content)
   - Create new extractor (if fundamentally different structure)

### Step 5: Freeze

Once the university passes validation, add it to the frozen set. Do not modify its extractor unless it breaks.

---

## What NOT to Do

### ❌ Do Not Auto-Detect Strategy

No `classify_page()` or `detect_structure()`. Humans inspect the page structure once and configure it manually.

**Why**: Auto-detection adds complexity and failure modes. Manual classification takes 2 minutes per university and is 100% reliable.

### ❌ Do Not Add Scoring or Confidence

No `confidence: 0.85` or `quality_score: 7/10`. Either the output is 100% clean or it's broken.

**Why**: Confidence scores hide problems. Manual verification forces you to read the actual output.

### ❌ Do Not Use LLM for Validation

No "pass extracted list to LLM to filter junk". Extractors should be deterministic and structure-based.

**Why**: LLM validation is slow, non-deterministic, and masks underlying structural issues.

### ❌ Do Not Trust Counts Alone

"Found 46 programs" is not evidence of success.

**Why**: MIT showed 13 programs with 40% junk. Counts look healthy while hiding garbage.

### ❌ Do Not Generalize Prematurely

If a new university has a slightly different table structure, do not modify `extract_table()` to handle both. Create `extract_table_variant()`.

**Why**: Premature generalization creates fragile extractors. Specific strategies stay stable.

---

## Extractor Design Principles

### 1. Structural, Not Semantic

Extract based on:
- `<a>` vs `<p>` vs `<table>` vs `<h2>`
- Presence/absence of links
- CSS classes (`program-card`)
- Table column position

Not based on:
- "Does this text sound like a degree?"
- Keyword scoring
- LLM classification

### 2. Container Scoping

Always scope to the relevant container first:

```python
container = (
    soup.find('main') or 
    soup.find('article') or 
    soup.find('div', {'id': 'content'}) or
    soup
)
```

For specialized structures (Purdue), scope further:

```python
program_cards = container.find_all('div', class_='program-card')
if program_cards:
    # Extract from cards only
```

### 3. Defensive Filtering

Even with correct structure, filter obvious junk:

```python
# Skip too short/long
if len(text) < 3 or len(text) > 150:
    continue

# Skip known junk phrases
if any(junk in text_lower for junk in JUNK_PHRASES):
    continue
```

But do not rely on keyword filtering as the primary mechanism. Get the structure right first.

### 4. Deduplication

Always deduplicate by normalized name:

```python
normalized = degree_name.lower().strip()
if normalized in seen_names:
    continue
seen_names.add(normalized)
```

---

## Success Metrics

The only metric that matters:

**Manual read-through of all extracted programs shows 0% junk.**

Not:
- ❌ "High confidence score"
- ❌ "Most programs extracted"
- ❌ "Fast execution"

But:
- ✅ "Every single item is a real degree/program name"

---

## Current Extractor Buckets

Based on the 4 working universities, future universities will likely fall into:

### Bucket 1: Anchor List (Arkansas pattern)
- Degree names in `<a>` tag text
- Clean anchor list pages
- Examples: Arkansas, likely many US state university catalogs

### Bucket 2: Plain Text List (UCSD pattern)
- Degree names in plain text `<li>` or `<p>` without links
- Often UC system schools
- Examples: UCSD, possibly UCLA, UC Berkeley

### Bucket 3: Table (MIT pattern)
- Degree names in table cells (first column)
- Rows with links = programs, bold-only = headers
- Examples: MIT, possibly some other catalog systems

### Bucket 4: Heading (Purdue pattern)
- Degree names in `<h2>/<h3>` tags
- Wrapped in specific containers (e.g., `program-card` divs)
- Examples: Purdue, likely many modern university sites

### Bucket 5: Playwright Table (Stanford pattern)
- JavaScript-rendered table
- Requires Playwright fetch, then table extraction
- Examples: Stanford (configured but not yet tested)

### Bucket 6: Playwright Anchor (Manchester pattern)
- JavaScript-rendered anchor list
- Requires Playwright fetch, then anchor extraction
- Examples: Manchester (configured but not yet tested)

---

## Files in Stable State

### Core
- `pipeline/extractors.py` — 5 extractor functions (frozen)
- `UNIVERSITY_CONFIG.py` — 4 working universities (stable)

### Testing
- `test_all_four_universities.py` — comprehensive test runner
- `final_validation.py` — automated validation with known-program checks

### Documentation
- `EXTRACTION_STATUS.md` — current extraction status
- `FIXES_SUMMARY.md` — MIT & Purdue fix details
- `ARCHITECTURE_FREEZE.md` — this document

---

## Next Steps

### Immediate: Test Playwright Universities

Stanford and Manchester are configured but not tested. Run them and verify:

```bash
# Add Stanford and Manchester to test_all_four_universities.py
# Run and manually inspect output
```

Expected: Playwright fetch works, then `anchor` or `table` extractor applies cleanly.

### Short-term: Add 5-10 More Universities

Pick universities from different structural buckets:
- 2-3 more `anchor` universities (confirm pattern holds)
- 1-2 more `table` universities
- 2-3 more `heading` universities
- 1-2 `playwright` universities

Manual classification → configure → test → verify.

### Medium-term: Scale to Top 50

Once 10-15 universities are stable across all buckets, the patterns are proven. Scale to top 50 by:
1. Manual inspection (2 min per university)
2. Classify into existing bucket
3. Configure
4. Test batch
5. Manual verification

No new extractors needed if buckets cover the structures.

---

## What Success Looks Like

In 2 weeks:
- 50 universities configured
- 5-6 extractor functions (same as now, maybe +1)
- All universities at 100% precision
- No confidence scores, no LLM validation
- Simple, explainable, deterministic extraction

The foundation is now **stable**. The rest is classification and configuration, not architecture changes.
