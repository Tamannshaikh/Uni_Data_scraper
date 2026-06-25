# University Extraction Status

**Last Updated**: 2026-06-25  
**Status**: All 4 configured universities passing validation

## Summary

All 4 universities now extract cleanly with **zero junk** (no deadline text, no nav menus, no "Follow Us" buttons).

| University | Programs | Strategy | Status |
|---|---|---|---|
| Arkansas | 10 | `anchor` | ✅ Working |
| UCSD | 186 | `plain_text_list` | ✅ Working |
| MIT | 46 | `table` | ✅ Fixed |
| Purdue | 190 | `heading` | ✅ Fixed |

## What Was Fixed

### MIT (table strategy)
**Problem**: Was returning 8 programs with ~40% junk (deadline text like "Master's: July 1PhD: October 1", nav concatenation like "Degree programsFields of study...")

**Root cause**: The `list_text` extractor was reading `<li>` and `<p>` elements near the table instead of the table cells themselves, even though the page structure was correctly diagnosed as a table.

**Fix**: Added genuine `table` strategy to `extractors.py`:
```python
def extract_table(base_url, container):
    # MIT pattern: programs have links, section headers don't
    for row in table.find_all('tr'):
        cells = row.find_all(['td', 'th'])
        if not cells:
            continue
        
        first_cell = cells[0]
        
        # Programs have links, section headers are bold with no links
        link = first_cell.find('a', href=True)
        if not link:
            continue  # Skip section headers
        
        text = first_cell.get_text(' ', strip=True)
        # Extract program...
```

**Result**: Now extracts 46 clean programs (Architecture, Economics, Biology, MIT Sloan MBA, etc.)

### Purdue (heading strategy)
**Problem**: Was returning 0 programs (or junk like "Follow Us", "Exploreplus_icon" when using `heading_with_button` strategy).

**Root cause**: The heading extractor was searching for generic `<h2>` tags in the `<main>` container, but Purdue's actual structure wraps programs in `<div class="program-card">` containers. Without scoping to these containers, the extractor was reading navigation elements and UI text instead of program names.

**Fix**: Updated `extract_heading()` to look for `program-card` divs first:
```python
def extract_heading(base_url, container):
    # Try Purdue-style first: program-card divs
    program_cards = container.find_all('div', class_=lambda x: x and 'program-card' in ...)
    
    if program_cards:
        for card in program_cards:
            heading = card.find(['h2', 'h3'])
            if not heading:
                continue
            
            text = heading.get_text(strip=True)
            # Filter junk, extract program...
```

**Result**: Now extracts 190 clean programs (Aeronautics and Astronautics, Computer Science, Biomedical Engineering, etc.)

## Validation Methodology

All 4 universities tested with `test_all_four_universities.py`:
1. Fetch page via httpx
2. Extract programs using configured strategy
3. Print **every single extracted item** for manual verification
4. Manually read through the list to confirm:
   - Every item is a real degree/program name
   - Zero deadline text
   - Zero nav-menu concatenation
   - Zero UI element junk

**Bar for success**: 100% precision. A count alone (e.g., "13 programs") is not sufficient — the actual list must be read and verified.

## Architecture

```python
UNIVERSITY_CONFIG = {
    "uark.edu": {
        "strategy": "anchor"  # Degree names ARE the anchor text
    },
    "mit.edu": {
        "strategy": "table"  # Degree names in table cells with links
    },
    "purdue.edu": {
        "strategy": "heading"  # Degree names in H2 within program-card divs
    },
    "ucsd.edu": {
        "strategy": "plain_text_list"  # Plain text bullets, no individual links
    }
}
```

Five extractor functions:
- `extract_anchor()` — degree names in `<a>` tag text
- `extract_table()` — degree names in table cells (first column)
- `extract_heading()` — degree names in `<h2>/<h3>` tags (with program-card scoping)
- `extract_plain_text_list()` — plain text list items with degree keywords
- `extract_heading_with_button()` — degree in heading, link in separate button (not currently used)

No scoring. No confidence. No LLM. No generic "smart" extraction. Per-university strategy selection based on observed page structure.

## Next Steps

Do not add new universities until:
1. MIT returns only real programs ✅ **DONE**
2. Purdue returns only real programs ✅ **DONE**
3. Arkansas stays clean ✅ **DONE**
4. UCSD stays clean ✅ **DONE**

Once these four are stable, remaining universities will mostly fall into the same structural buckets:
- **anchor** bucket: Arkansas, likely many US state universities
- **table** bucket: MIT, likely some other catalogues
- **heading** bucket: Purdue, likely many program-card style pages
- **plain_text_list** bucket: UCSD, some UC system schools
- **playwright_table** / **playwright_anchor**: Stanford, Manchester, others with JS-rendered content

## Files Changed

- `pipeline/extractors.py` — Added `extract_table()`, updated `extract_heading()` with program-card scoping
- `UNIVERSITY_CONFIG.py` — Changed MIT strategy from `list_text` to `table`
- `test_all_four_universities.py` — Comprehensive test runner with full output display
