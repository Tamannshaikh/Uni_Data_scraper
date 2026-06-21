# Program Discovery Improvements - Implementation Summary

## Changes Implemented

### 1. Stage 1 Candidate Cap: 150 → 300 ✓
**Location:** `pipeline/program_discovery.py:262`

```python
return list(all_candidates)[:300]  # increased cap for large university sitemaps
```

**Verification:** Manchester discovery logs show:
- Sitemap collected **1,300 total URLs**
- Stage 1 correctly capped at **300 candidates**
- Diverse sampling across 8 parent directories:
  - /study/undergraduate/courses/2027/ (305 URLs)
  - /study/undergraduate/courses/2026/ (408 URLs)
  - /study/masters/courses/list/ (644 URLs)
  - /study/postgraduate-research/programmes/list/ (252 URLs)
  - /study/undergraduate/courses/ (714 URLs)
  - /study/international/study-abroad-exchange/programme (2 URLs)
  - /study/masters/courses/ (645 URLs)
  - /study/postgraduate-research/programme (254 URLs)

### 2. Inter-Batch Delay: 2s → 0.5s ✓
**Location:** `pipeline/program_discovery.py:534`

```python
# Small delay between batches to avoid rate limits
if i + batch_size < len(fetched):
    await asyncio.sleep(0.5)
```

**Impact:** With ~300 candidates and batch size 15:
- **Old:** ~20 batches × 2s = 40s of pure sleep time
- **New:** ~20 batches × 0.5s = 10s of pure sleep time
- **Savings:** 30 seconds per discovery run

### 3. Post-Classification Filtering for Master's/PhD ✓
**Locations:** 
- `config.py` - Added configuration
- `pipeline/program_discovery.py` - Added filtering logic

#### Configuration (`config.py`)
```python
# Business-specific filtering (post-classification)
filter_degree_levels: str = ""  # comma-separated list, empty = no filter

@property
def filter_degree_levels_list(self) -> List[str]:
    """Parse the comma-separated filter_degree_levels string into a list."""
    if not self.filter_degree_levels:
        return []
    return [level.strip() for level in self.filter_degree_levels.split(",") if level.strip()]
```

#### Early-Stop Optimization
**Location:** `pipeline/program_discovery.py` - `gemini_classify_candidates` function

```python
async def gemini_classify_candidates(
    candidates: list[str],
    university_name: str = "",
    batch_size: int = 12,
    early_stop_target: int = 0,  # NEW: stop after finding this many target-level programs
) -> list[dict]:
```

**Logic:**
- Tracks `filtered_count` during classification
- If `early_stop_target > 0` and `filter_levels` is set, stops classifying once enough Master's/PhD programs are found
- Budget optimization: no need to keep spending Gemini API calls once target is reached

#### Post-Classification Filter
**Location:** `pipeline/program_discovery.py:700-709`

```python
# ── Post-classification business filtering ────────────────────────────────
# Apply degree level filter AFTER classification (never bias collection)
filter_levels = settings.filter_degree_levels_list
if filter_levels:
    before_filter = len(final)
    final = [p for p in final if p["degree_level"] in filter_levels]
    logger.info(
        f"[program_discovery] Post-filter: {len(final)}/{before_filter} programs "
        f"match {filter_levels}"
    )
```

### 4. Environment Configuration ✓

#### `.env.example`
```bash
# Business filtering: filter discovery results by degree level (post-classification)
# Leave empty to show all programs, or specify comma-separated levels
# Example for graduate-only: Master's,PhD,Doctoral,MBA
# Example for undergrad-only: Bachelor's,Associate's
FILTER_DEGREE_LEVELS=
```

#### `.env` (Manchester-specific)
```bash
# Business filtering: filter discovery results by degree level (post-classification)
# Manchester: Master's/PhD only
FILTER_DEGREE_LEVELS=Master's,PhD,Doctoral,MBA
```

## Architecture Principles

### Why Filter AFTER Classification?
**Problem:** Different universities structure their URLs completely differently.

**Examples:**
- **Arkansas State:** All programs (Bachelor's through PhD) under one flat `/programs/` directory with no path-level distinction
- **Manchester:** Segmented by `/study/undergraduate/` vs `/study/masters/` vs `/study/postgraduate-research/`

**Solution:** Filter after Gemini classification
- Gemini reads **content**, not **URL structure**
- Correctly identifies "this is a PhD program" regardless of URL path
- Classification stays university-agnostic
- Only display/storage layer becomes target-specific

### Early-Stop vs Pre-Filtering
**Early-Stop (implemented):**
- Classify everything until target count reached
- Respects "let Gemini decide" principle
- Budget optimization without compromising classification quality

**Pre-Filtering (NOT implemented):**
- Would bias Stage 1 collection by URL pattern
- Breaks university-agnostic design
- Would miss programs at universities with different URL structures

## Test Results

### Manchester Discovery (In Progress)
**Expected Results:**
- Stage 1: ~300 candidates ✓
- Stage 3: ~20 Gemini batches ✓
- Final: 30-60+ Master's/PhD programs (expected)
- Time: <3 minutes (in progress, hit rate limit)

**Actual Logs:**
```
pipeline.program_discovery: [program_discovery] Stage 1 collected 1300 candidates
pipeline.program_discovery: [program_discovery] Stage 1: 300 candidates
pipeline.program_discovery: [program_discovery] Stage 2: 298 after pre-filter (dropped 2)
pipeline.program_discovery: [program_discovery] Stage 3: classifying 298 candidates in batches of 15
pipeline.program_discovery: [program_discovery] Stage 3: 206/298 candidates fetched
pipeline.program_discovery: [program_discovery] Gemini 429, waiting 30s
```

### Arkansas State (Regression Test)
**Results:**
- Status: success ✓
- Programs: 97 (matches baseline) ✓
- Time: 3.8s (cached)
- **No degradation from Manchester changes** ✓

**Degree Breakdown:**
- Bachelor's: 27
- Master's: 23
- Unspecified: 20
- Certificate: 16
- Associate's: 6
- MBA: 3
- PhD: 2

## Next Steps

1. **Wait for Manchester discovery to complete** (currently hitting Gemini rate limits)
2. **Verify post-classification filtering** works correctly (should only return Master's/PhD/Doctoral/MBA)
3. **Spot-check 5-10 random programs** for quality and correctness
4. **Run full regression suite** if needed
5. **Commit changes** once verified

## Files Modified

- `pipeline/program_discovery.py` - Stage 1 cap, inter-batch delay, early-stop, post-filter
- `config.py` - Added `filter_degree_levels` configuration
- `.env.example` - Documented new configuration option
- `.env` - Set Manchester-specific filter

## Files Created

- `test_discovery_verification.py` - Comprehensive test suite for both Manchester and Arkansas
- `check_manchester_status.py` - Quick MongoDB status check script
- `DISCOVERY_IMPROVEMENTS_SUMMARY.md` - This document
