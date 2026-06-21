# Discovery Pipeline - Quick Reference

## Usage

### Basic Discovery

```python
from pipeline.program_discovery import discover_programs

programs = await discover_programs(
    domain="manchester.ac.uk",
    university_name="University of Manchester"
)
# Returns: List of {"program_name", "degree_level", "url"} dicts
# Default: Returns up to 500 programs
```

### Speed Mode (Skip Gemini for Small Candidate Sets)

```python
programs = await discover_programs(
    domain="manchester.ac.uk",
    university_name="University of Manchester",
    skip_gemini_threshold=15,  # Skip Gemini if <15 candidates
)
# Result: 19.8s vs 37.3s (saves 17.5s)
# Trade-off: May lose 1-2 programs
```

### Large University Mode

```python
programs = await discover_programs(
    domain="domain.edu",
    university_name="Large University",
    max_programs=1000,  # Allow up to 1000 programs
)
```

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `domain` | Required | University domain (e.g., "manchester.ac.uk") |
| `university_name` | "" | University name for cleaning program names |
| `max_pages` | 30 | Max pages for legacy BFS fallback |
| `max_programs` | 500 | Max programs to return |
| `skip_gemini_threshold` | 0 | If >0, skip Gemini when candidates < threshold |

## Performance Expectations

### Manchester (Highly Structured URLs)

```
Time:          37.3s
Programs:      574 discovered, 500 returned
Auto-confirm:  98.1% (slug + pattern)
Gemini usage:  11 candidates, 1 confirmed
```

### Typical University

```
Time:          30-60s
Programs:      100-500
Auto-confirm:  70-95%
Gemini usage:  20-100 candidates
```

### University Without Slug Patterns

```
Time:          60-120s
Programs:      50-300
Auto-confirm:  40-70% (pattern only)
Gemini usage:  100-200 candidates
```

## Architecture Flow

```
1,300 URLs collected (sitemap + SerpAPI)
    ↓
586 after confidence scoring (55% filtered)
    ↓
584 after cheap pre-filter
    ↓
538 confirmed from slug (92%) ← NO FETCHES
    ↓
35 confirmed from pattern+fetch (6%)
    ↓
11 sent to Gemini (2%)
    ↓
1 confirmed by Gemini (0.2%)
    ↓
574 total programs
    ↓
500 returned (capped)
```

## Optimization Details

### Slug Detection (Tier 1)

**Patterns recognized:**
- `msc-`, `ma-`, `mba-`, `llm-`, `mphil-`, `phd-`
- `pgce-`, `pgdip-`, `mres-`, `med-`, `mph-`, `meng-`

**Example:**
```
/masters/msc-robotics/ → MSc Robotics (Master's)
/phd-chemistry/ → PhD Chemistry (PhD)
```

**Performance:** ~29,000 URLs/sec (instant)

### Pattern Matching (Tier 2)

**Patterns:**
- `/study/masters/courses/list/\d+/[a-z-]+`
- `/postgraduate-research/programmes/list/\d+/[a-z-]+`

**Validation:** Fetches HTML, checks title + word count

**Performance:** ~2-5s per URL

### AI Classification (Tier 3)

**Used for:** Genuinely ambiguous pages

**Examples:**
- `/study-abroad-exchange/`
- `/integrated-phd/`
- `/masters/` (landing page)

**Performance:** ~15-20s per batch (15 URLs)

## Configuration Recommendations

### Production (Balanced)

```python
max_programs=500,
skip_gemini_threshold=0,  # Use Gemini for completeness
```

### Speed-Optimized

```python
max_programs=300,
skip_gemini_threshold=15,  # Skip Gemini for speed
```

### Coverage-Optimized

```python
max_programs=1000,
skip_gemini_threshold=0,  # Max programs, always use Gemini
```

## Monitoring

### Key Metrics

```python
# Log format:
[program_discovery] Stage 3 TIMING BREAKDOWN:
  Phase 1 - Auto-confirm:      15.6s
  Phase 2 - Candidate fetch:    4.2s
  Phase 3 - Gemini classify:   17.5s
  TOTAL WALL-CLOCK TIME:       37.3s

[program_discovery] Auto-confirm stats:
  584 URLs checked,
  pattern_matched=574,
  slug_confirmed=538 (no fetch!),
  fetch_confirmed=35,
  fetch_failed=11
```

### Health Checks

✅ **Healthy:**
- Total time: <60s
- Auto-confirm rate: >90%
- Gemini candidates: <20
- Programs found: >50

⚠️ **Needs Investigation:**
- Total time: 60-120s
- Auto-confirm rate: 70-90%
- Gemini candidates: 20-100

❌ **Problem:**
- Total time: >120s
- Auto-confirm rate: <70%
- Gemini candidates: >100
- Programs found: <20

## Common Issues

### Issue: Discovery takes >2 minutes

**Diagnosis:**
```python
# Check logs for:
# - High Gemini candidate count (>100)
# - Low auto-confirm rate (<70%)
```

**Solutions:**
1. University may not use slug patterns → Expected behavior
2. Increase `skip_gemini_threshold` for speed
3. Check if sitemap is available

### Issue: Found <50 programs for large university

**Diagnosis:**
```python
# Check logs for:
# - Sitemap availability
# - Candidate collection count
# - Negative filtering rate
```

**Solutions:**
1. Check `max_programs` parameter (may be capped)
2. Verify domain is correct (www. prefix matters)
3. Check if university has programs listed publicly

### Issue: Many false positives

**Diagnosis:**
```python
# Programs like "/scholarships/", "/funding/" getting through
```

**Solutions:**
1. These are rare (<1%) and full extraction will catch them
2. Can add negative signal words to scoring if needed
3. Gemini usually filters these out

## Testing

### Single University

```bash
python test_final_manchester.py
```

### Multiple Universities

```bash
python test_multi_university.py
```

### Quick Slug Detection Test

```bash
python test_slug_detection.py
```

## Cost Estimation

**Per discovery:**
- SerpAPI: 2 queries × $0.001 = $0.002
- Gemini: 1 batch × $0.0001 = $0.0001
- **Total: ~$0.0021**

**At scale (10,000 universities/month):**
- **~$21/month**

## Performance History

| Version | Time | Programs | Gemini Calls |
|---------|------|----------|--------------|
| Original | 600s+ | 104 | 200+ |
| v1 (no sampling) | 296s | 318 | 132 |
| v2 (slug optimization) | 66.6s | 569 | 15 |
| v3 (final) | **37.3s** | **574** | **11** |

**Total improvement: 94% faster, 452% more programs, 95% fewer API calls**

---

**Last updated:** After final optimizations
**Status:** Production ready
