# MIT & Purdue Extraction Fixes — Complete

**Date**: 2026-06-25  
**Status**: ✅ Both fixes verified and passing validation

---

## Summary

Two genuine problems were identified and fixed:

1. **MIT**: Was returning 13 programs with ~40% junk (8 real + 5 junk items)
2. **Purdue**: Was returning 0 programs (wrong DOM scoping)

Both are now **fully fixed** and extracting cleanly:
- **MIT**: 46 programs, 100% clean
- **Purdue**: 190 programs, 100% clean

---

## MIT Fix Details

### Problem
```
Real programs (8):
  - Computational Science and Engineering PhD*
  - MIT Sloan MBA Program
  - ...

Junk (5):
  - Master's: July 1PhD: October 1
  - Degree programsFields of studyDoctoral degrees...
  - Certificate & online programs
```

Precision: **~60%**

### Root Cause
The page structure was correctly diagnosed as a **table** in an earlier session:
- "It's a table with program names in the first column"

However, the `list_text` extractor was applied anyway, which read `<li>` and `<p>` elements **near** the table (deadline text, nav menus) instead of the table cells themselves.

Classic pattern: **correct diagnosis → nearest existing tool → wrong result**

### Fix
Added genuine `table` strategy to `pipeline/extractors.py`:

```python
def extract_table(base_url: str, container: BeautifulSoup) -> List[Dict]:
    """
    Extract degrees from table cells.
    
    MIT-specific: Each linked row is a program. Section headers 
    are bold with no links.
    """
    programs = []
    seen_names = set()
    
    for table in container.find_all('table'):
        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if not cells:
                continue
            
            first_cell = cells[0]
            
            # MIT pattern: programs have links, section headers don't
            link = first_cell.find('a', href=True)
            if not link:
                continue  # Skip section headers
            
            text = first_cell.get_text(' ', strip=True)
            
            # Skip header row
            if text in ['Program', 'Field', 'Department']:
                continue
            
            # Basic filtering
            if len(text) < 3 or len(text) > 150:
                continue
            
            degree_name = clean_degree_name(text)
            normalized = degree_name.lower()
            
            if normalized in seen_names:
                continue
            
            seen_names.add(normalized)
            url = urljoin(base_url, link['href'])
            
            programs.append({
                'degree_name': degree_name,
                'url': url
            })
    
    return programs
```

Updated `UNIVERSITY_CONFIG.py`:
```python
"mit.edu": {
    "url": "https://oge.mit.edu/graduate-admissions/programs/fields-of-study/",
    "strategy": "table",  # Changed from "list_text"
}
```

### MIT Table Structure
The page has 56 table rows:
- **Row 1**: Table header ("Program")
- **Rows with [BOLD] only**: Section headers ("School of Engineering", "Sloan School of Management")
- **Rows with [LINK]**: Actual programs (46 total)

The fix: only extract rows that have a link in the first cell.

### Result
**Before**: 8 programs, ~40% junk  
**After**: 46 programs, 0% junk

Sample extracted programs:
- Architecture
- Aeronautics and Astronautics
- Economics
- MIT Sloan MBA Program
- Physics
- Biology
- Computational Science and Engineering PhD*

---

## Purdue Fix Details

### Problem
**Extraction result**: 0 programs

OR (with `heading_with_button` strategy):
```
Junk extracted:
  - Follow Us
  - Exploreplus_icon
  - Informationplus_icon
```

### Root Cause
The session had **already observed** Purdue's static HTML containing program names:
```html
<h2>Computer Science</h2>
<a>MORE INFO</a>
<a>ADMISSION REQUIREMENTS</a>
```

This was from a 54.1 KB fetch showing real content in static HTML. The "0 programs" result meant the extractor was pointed at the **wrong DOM container**, not that the content was missing or JS-rendered.

The generic `extract_heading()` was doing:
```python
main.find_all("h2")  # Too broad
```

But Purdue stores programs in:
```html
<div class="program-card">
    <h2>Computer Science</h2>
    <a>MORE INFO</a>
</div>
```

Without scoping to `program-card` divs, the extractor was reading navigation H2s, UI elements, and footer text.

### Fix
Updated `extract_heading()` in `pipeline/extractors.py` to look for `program-card` containers **first**:

```python
def extract_heading(base_url: str, container: BeautifulSoup) -> List[Dict]:
    """
    Extract degrees from heading tags.
    
    For Purdue: looks specifically for <div class="program-card"> containers.
    Less strict - accepts program names without explicit degree keywords.
    """
    programs = []
    seen_names = set()
    
    # Try Purdue-style first: program-card divs
    program_cards = container.find_all(
        'div', 
        class_=lambda x: x and ('program-card' in ' '.join(x) if isinstance(x, list) else 'program-card' in x)
    )
    
    if program_cards:
        for card in program_cards:
            heading = card.find(['h2', 'h3'])
            if not heading:
                continue
            
            text = heading.get_text(strip=True)
            
            # Basic sanity checks
            if len(text) < 3 or len(text) > 150:
                continue
            
            text_lower = text.lower()
            
            # Filter junk
            if any(junk in text_lower for junk in JUNK_PHRASES):
                continue
            
            degree_name = clean_degree_name(text)
            normalized = degree_name.lower()
            
            if normalized in seen_names:
                continue
            
            seen_names.add(normalized)
            
            # Find link in this card
            link = card.find('a', href=True)
            url = urljoin(base_url, link['href']) if link else base_url
            
            programs.append({
                'degree_name': degree_name,
                'url': url
            })
        
        return programs
    
    # Fallback: generic H2/H3 extraction
    # (existing generic logic for other universities)
```

### Result
**Before**: 0 programs (or junk like "Follow Us")  
**After**: 190 programs, 0% junk

Sample extracted programs:
- Aeronautics and Astronautics
- Computer Science
- Biomedical Engineering
- Artificial Intelligence and Machine Learning
- Psychology (PNW)
- Mathematics

---

## Validation Results

### Test 1: Full Output Display
`test_all_four_universities.py` — prints **every single extracted item**

Results:
- ✅ Arkansas: 10 programs, all clean
- ✅ UCSD: 186 programs, all clean
- ✅ MIT: 46 programs, all clean (no deadline text, no nav junk)
- ✅ Purdue: 190 programs, all clean (no "Follow Us", no UI elements)

### Test 2: Known Programs Check
`final_validation.py` — validates known programs are present + zero junk patterns

Checks:
1. Known real programs are extracted (e.g., "MIT Sloan MBA Program", "Computer Science")
2. No junk patterns detected ("master's: july", "follow us", "more info", etc.)
3. All URLs are valid HTTP(S)

Results:
```
✅ PASS - uark.edu
✅ PASS - ucsd.edu
✅ PASS - mit.edu
✅ PASS - purdue.edu

🎉 ALL 4 UNIVERSITIES PASSED VALIDATION
```

---

## Key Lessons

### 1. Count ≠ Quality
"Found 13 programs" looked healthy but hid 40% junk. "Found 0 programs" looked like total failure but was just wrong DOM scoping.

**Rule going forward**: Print the actual list, read it, only then decide if the strategy is right.

### 2. Diagnosis → Implementation Gap
Both bugs followed the same pattern:
1. Correct diagnosis made (MIT = table, Purdue static HTML has content)
2. Nearest existing tool applied instead (list_text, generic heading extractor)
3. Result: bug

**Fix**: Build the extractor that matches the diagnosis, not the one that's closest.

### 3. Purdue: "Needs Playwright" Was Premature
The session concluded "needs Playwright" without re-verifying against the HTML that was **already fetched and inspected**. That 54.1 KB fetch showed program names in static HTML, contradicting the Playwright conclusion.

**Rule**: Re-fetch and manually inspect the raw HTML before concluding JS-rendering is the problem.

---

## Architecture Freeze

This is now the stable extraction architecture:

```python
UNIVERSITY_CONFIG = {
    "uark.edu": {
        "strategy": "anchor"  # Degree names in <a> text
    },
    "mit.edu": {
        "strategy": "table"  # Table cells with links
    },
    "purdue.edu": {
        "strategy": "heading"  # H2 in program-card divs
    },
    "ucsd.edu": {
        "strategy": "plain_text_list"  # Plain text bullets
    },
}
```

Five extractor functions:
1. `extract_anchor()` — degree names ARE the anchor text
2. `extract_table()` — degree names in table cells (first column)
3. `extract_heading()` — degree names in H2/H3 (with container scoping)
4. `extract_plain_text_list()` — plain text list items
5. `extract_heading_with_button()` — degree in heading, link in button (unused currently)

No scoring. No confidence. No LLM. No generic "smart" extraction.

---

## Next Steps

**Do not add new universities** until these four are stable:
- ✅ MIT returns only real programs
- ✅ Purdue returns only real programs
- ✅ Arkansas stays clean
- ✅ UCSD stays clean

**All four are now stable.**

New universities will mostly fall into existing buckets:
- **anchor**: Arkansas, likely many US catalogs
- **table**: MIT, likely some other table-based pages
- **heading**: Purdue, likely many program-card style pages
- **plain_text_list**: UCSD, some UC system schools
- **playwright_table** / **playwright_anchor**: Stanford, Manchester (JS-rendered)

---

## Files Changed

### Modified
- `pipeline/extractors.py`:
  - Rewrote `extract_table()` with MIT-specific link-based filtering
  - Updated `extract_heading()` with Purdue-style program-card scoping
- `UNIVERSITY_CONFIG.py`:
  - Changed MIT strategy from `"list_text"` to `"table"`

### Added
- `test_all_four_universities.py` — comprehensive test with full output
- `final_validation.py` — automated validation with known-program checks
- `verify_mit_completeness.py` — MIT table structure inspector
- `EXTRACTION_STATUS.md` — current extraction status documentation
- `FIXES_SUMMARY.md` — this document
