# Production Migration Research Document

**Project:** UniScraper — AI-Powered University Program Scraper  
**Prepared for:** AutoNova Phase 1 Deliverable  
**Date:** May 2026

---

## 1. Scraping at Scale (500 universities/day)

### Current architecture limits
The current system processes one URL at a time with a 20s gap between Gemini calls. At 500 scrapes/day that's ~2.8 hours of pure LLM wait time — acceptable if run overnight, but not for real-time use.

### Rate limiting
| Service | Free tier limit | Paid tier |
|---|---|---|
| Gemini 2.5 Flash | 10 RPM, 1M tokens/day | $0.075/1M input tokens |
| Groq llama-3.3-70b | 30 RPM, 14,400 req/day | $0.59/1M input tokens |
| Ollama (local) | Unlimited | Hardware cost only |

At 500 scrapes/day with ~8k tokens per scrape = 4M tokens/day. Gemini free tier covers 1M/day — need paid tier for production.

### IP blocking
University websites occasionally block scrapers. Mitigations already implemented:
- Realistic Chrome User-Agent header
- httpx with follow_redirects
- Playwright for JS-rendered pages

Additional production measures:
- **Random delay 2-5s** between requests to the same domain (add to fetcher)
- **Proxy rotation** for universities that actively block: BrightData residential proxies (~$500/month for 500 scrapes/day) — only needed for ~10-15% of universities
- **Retry with backoff** on 403/429 from target sites (already implemented for LLM, extend to fetcher)

### Recommended production architecture
```
Job Queue (Redis/BullMQ)
    │
    ├── Worker 1: Fetch + parse (httpx/Playwright)
    ├── Worker 2: Fetch + parse
    └── Worker 3: Fetch + parse
            │
            └── LLM Queue (rate-limited)
                    │
                    └── Gemini Flash (primary)
                        Groq (fallback)
                        Ollama (local fallback)
```

Run 3-5 fetch workers in parallel (fetching is I/O bound, not CPU bound). Keep LLM calls serialized through a single rate-limited queue.

---

## 2. LLM Cost Comparison (per scrape, ~8k tokens average)

| Model | Provider | Cost/1M input | Cost/1M output | Cost per scrape | Quality | Speed |
|---|---|---|---|---|---|---|
| Gemini 2.5 Flash | Google | $0.075 | $0.30 | ~$0.0006 | ⭐⭐⭐⭐⭐ | ~12s |
| GPT-4o Mini | OpenAI | $0.15 | $0.60 | ~$0.0012 | ⭐⭐⭐⭐ | ~8s |
| Claude 3.5 Haiku | Anthropic | $0.80 | $4.00 | ~$0.006 | ⭐⭐⭐⭐⭐ | ~10s |
| Groq llama-3.3-70b | Groq | $0.59 | $0.79 | ~$0.005 | ⭐⭐⭐⭐ | ~3s |
| Ollama qwen2.5:1.5b | Local | $0 | $0 | $0 | ⭐⭐⭐ | ~15s CPU |

**At 500 scrapes/day (monthly):**

| Model | Monthly LLM cost |
|---|---|
| Gemini 2.5 Flash | ~$9/month |
| GPT-4o Mini | ~$18/month |
| Claude 3.5 Haiku | ~$90/month |
| Groq llama-3.3-70b | ~$75/month |
| Ollama (local) | $0 (hardware only) |

**Recommendation:** Gemini 2.5 Flash as primary — best quality-to-cost ratio at $9/month for 500 scrapes/day. Use Groq as rate-limit fallback (already implemented). Ollama for development/testing.

---

## 3. Data Freshness Strategy

University admission requirements change annually (typically August-October for the following year's intake). Fees change annually. English requirements rarely change.

### Recommended approach

**Tiered re-scrape schedule:**
- **High-change fields** (fees, deadlines): re-scrape every 90 days
- **Medium-change fields** (requirements, IELTS): re-scrape every 180 days
- **Low-change fields** (program name, duration): re-scrape annually

**Implementation:**
1. Add `last_scraped_at` and `next_scrape_due` fields to MongoDB documents
2. Background job (cron) checks for documents where `next_scrape_due < now`
3. Re-scrape and compare new result against stored result
4. If any field changed: flag the record, notify counsellors via email/webhook

**Change detection:**
```python
def detect_changes(old: dict, new: dict) -> list[str]:
    changed = []
    for field in TRACKED_FIELDS:
        if old.get(field) != new.get(field):
            changed.append(field)
    return changed
```

**MongoDB TTL index** (optional — auto-delete stale records):
```javascript
db.scrape_results.createIndex(
  { "created_at": 1 },
  { expireAfterSeconds: 365 * 24 * 3600 }  // 1 year
)
```

---

## 4. Production Database & Hosting

### Database: MongoDB Atlas M10
- **Cost:** $57/month
- **Specs:** 2 vCPUs, 2GB RAM, 10GB storage
- **Handles:** 500 scrapes/day = ~15,000 scrapes/month comfortably
- **Why MongoDB:** Schema-flexible (different universities have different fields), native JSON storage, Atlas free tier for development

**Indexes to create for production:**
```javascript
db.scrape_results.createIndex({ "url_requested": 1, "created_at": -1 })
db.scrape_results.createIndex({ "university_name": "text", "program_name": "text" })
db.scrape_results.createIndex({ "status": 1, "created_at": -1 })
```

### Backend hosting: Railway
- **Cost:** ~$20/month (Hobby plan)
- **Why Railway:** Auto-deploys from GitHub, supports Python/FastAPI natively, built-in env var management, zero-config HTTPS
- **Alternative:** Render.com (free tier available but spins down after inactivity — not suitable for production)

### Frontend hosting: Vercel
- **Cost:** Free (Hobby plan)
- **Why Vercel:** Instant deploys from GitHub, global CDN, zero config for React apps

### Total infrastructure cost at 500 scrapes/day

| Item | Monthly cost |
|---|---|
| Gemini API (500 scrapes/day) | ~$9 |
| MongoDB Atlas M10 | $57 |
| Railway (backend) | $20 |
| Vercel (frontend) | $0 |
| Proxy rotation (optional, ~15% of scrapes) | ~$75 |
| **Total (without proxies)** | **~$86/month** |
| **Total (with proxies)** | **~$161/month** |

---

## 5. Legal & Ethical Considerations

### robots.txt research

| University | robots.txt | Scraping policy |
|---|---|---|
| Harvard (harvard.edu) | Allows most crawlers, blocks `/secure/` paths | No explicit prohibition on academic data |
| University of Manchester (manchester.ac.uk) | Standard Disallow for admin/login paths | No prohibition on public program pages |
| University of Toronto (utoronto.ca) | Allows Googlebot, no general prohibition | Public pages accessible |
| University of Edinburgh (ed.ac.uk) | Standard crawl-delay: 10 | Requests 10s delay between requests |
| NUS (nus.edu.sg) | Disallow: /staff/, /admin/ | Public program pages allowed |

### Compliant approach
1. **Respect robots.txt** — check `crawl-delay` directive and honour it (add to fetcher)
2. **Only scrape public pages** — never attempt to access login-walled content
3. **Rate limit requests** — 2-5s delay between requests to the same domain
4. **Identify the scraper** — add a descriptive User-Agent: `UniScraper/1.0 (study-abroad-counselling; contact@autonova.ai)`
5. **Cache aggressively** — 24h cache already implemented; extend to 90 days for production
6. **No personal data** — only scrape publicly available program information, never student data

### Terms of Service notes
Most university websites' ToS prohibit "systematic scraping for commercial purposes." However:
- The data being scraped is **publicly available** admission information
- The purpose is **counselling students** — arguably in the public interest
- The scraper **does not bypass any access controls**
- Recommended: add a `robots.txt` check before scraping each domain in production

---

## 6. Scaling Beyond 500/day

If the client grows to 5,000 scrapes/day:
- Switch to **Gemini API paid tier** with higher RPM limits
- Add **Redis job queue** (BullMQ) for distributed worker processing
- Move to **MongoDB Atlas M30** ($190/month) for higher throughput
- Consider **dedicated proxy pool** for Australian/Asian universities that block scrapers
- Estimated cost at 5,000/day: ~$400/month
