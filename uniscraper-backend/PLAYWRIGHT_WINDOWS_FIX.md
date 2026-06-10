# Playwright on Windows - NotImplementedError Fix

## Issue Summary
- **Error:** `NotImplementedError` when Playwright runs inside FastAPI/Uvicorn background tasks
- **Location:** `asyncio.base_events._make_subprocess_transport`
- **Cause:** Windows ProactorEventLoop doesn't support subprocess pipes needed by Playwright
- **Impact:** Tier 1 (Crawl4AI) fails, system falls back to Tier 2 (Firecrawl) ✅

## Environment
- Python: 3.12.10
- Playwright: 1.60.0
- Windows: 11 Pro Build 26200
- Framework: FastAPI + Uvicorn

## Error Trace
```python
File "asyncio\base_events.py", line 528, in _make_subprocess_transport
    raise NotImplementedError
NotImplementedError
```

## Current Status
✅ **System is working correctly** - automatically falls back to Tier 2 (Firecrawl)
- Tier 1 (Crawl4AI): Fails on Windows due to ProactorEventLoop
- Tier 2 (Firecrawl): SUCCESS - bypasses Cloudflare
- Tier 3 (Custom httpx): Works as final fallback

## Fix Options

### Option 1: Use SelectorEventLoop (Recommended for Development)
Add this to `main.py` before any async operations:

```python
import sys
import asyncio

if sys.platform == 'win32':
    # Use SelectorEventLoop on Windows for subprocess support
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

**Pros:** 
- Simple one-line fix
- Enables full subprocess support
- Tier 1 (Crawl4AI) will work

**Cons:**
- SelectorEventLoop is slightly slower than ProactorEventLoop on Windows
- May have different performance characteristics

### Option 2: Use Patchright instead of Playwright
Crawl4AI supports Patchright (Playwright fork optimized for automation):

```python
# In config.py or .env
CRAWL4AI_BROWSER = "patchright"  # instead of "playwright"
```

**Pros:**
- Designed to work around bot detection
- Better stealth features
- May handle Windows event loop better

**Cons:**
- Additional dependency
- Less mature than Playwright

### Option 3: Keep Current Fallback System (Recommended for Production)
No changes needed - the three-tier system handles this gracefully:

```
Tier 1 (Crawl4AI) → Fails on Windows → Falls back to Tier 2 (Firecrawl) → SUCCESS
```

**Pros:**
- No code changes needed
- Firecrawl is cloud-based, more reliable for Cloudflare bypass
- Works consistently across all platforms
- Proven successful (Melbourne University test)

**Cons:**
- Uses Firecrawl API credits
- Slightly slower than local Playwright

### Option 4: Deploy to Linux
On Linux (Railway, Docker, AWS), ProactorEventLoop issue doesn't exist:

**Pros:**
- All three tiers work natively
- Better performance
- Production environment

**Cons:**
- Requires deployment
- Not useful for local Windows development

## Recommendation

### For Local Development (Windows):
**Use Option 3** - Keep current fallback system. It's working perfectly and requires no changes.

### For Production (Railway/Cloud):
**Deploy to Linux** - All tiers will work natively, including Tier 1 (Crawl4AI) with stealth Chromium.

### If You Need Tier 1 on Windows:
**Use Option 1** - Add the SelectorEventLoop policy to `main.py`:

```python
# Add to main.py at the top, before @app.on_event("startup")
import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

## Test Results

### Standalone Playwright Test: ✅ SUCCESS
```bash
py test_playwright_error.py
✓ Playwright context created
✓ Browser launched successfully!
✓ New page created
✓ Page loaded: Example Domain
```

### Playwright in FastAPI/Uvicorn: ❌ NotImplementedError
```
ERROR:asyncio:Task exception was never retrieved
NotImplementedError
```

### Current System with Fallback: ✅ SUCCESS
```
Tier 1 → Failed (NotImplementedError)
Tier 2 → SUCCESS (Firecrawl bypassed Cloudflare)
Result: 11 fields extracted from Melbourne University
```

## Conclusion
The system is **production-ready as-is**. The three-tier fallback architecture handles the Windows limitation gracefully, and Tier 2 (Firecrawl) successfully bypasses Cloudflare protection.

No immediate action required unless you specifically need Tier 1 (Crawl4AI) to work on Windows for development purposes.
