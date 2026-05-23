# Day 1 Alignment Document — UniScraper Pod

**Date:** May 2026  
**Pod:** AI Automation (x2) + Web Dev (x1)  
**Project:** AI-Powered Smart University Program Scraper

---

## 1. Pipeline Walkthrough (agreed end-to-end flow)

```
User pastes URL into dashboard
    │
    ▼
POST /api/v1/scrape
    │  Check 24h cache → return cached result if found
    │
    ▼
Background task: run_scrape(scrape_id, url)
    │
    ├── fetch_page(url)
    │     httpx (fast, 15s timeout)
    │     → if < 200 words: Playwright (headless Chromium)
    │
    ├── extract_relevant_links(html)
    │     Score all <a href> by keyword relevance
    │     Return top 4 (configurable via MAX_SUBPAGES)
    │
    ├── Fetch sub-pages concurrently (max 3 at a time)
    │     Each classified: admissions / english / tuition / overview / etc.
    │
    ├── extract_pdfs_from_page(html)
    │     Find PDF links, download, extract text (max 2)
    │
    ├── extract_fields(combined_text, pages_data)
    │     Field-specific context routing (IELTS → english page, fees → tuition page)
    │     Regex pre-extraction (IELTS, TOEFL, fees, deadlines as anchor hints)
    │     Gemini 2.5 Flash → Groq llama-3.3-70b → Ollama qwen2.5:1.5b → Flash-Lite
    │     Semantic validation (PhD duration, IELTS range, GPA context)
    │     Regex fallbacks (fill nulls LLM missed)
    │
    ├── Build field_sources attribution
    │     Map each non-null field → source URL
    │
    └── Save to MongoDB
          Status: success (≥8 fields) / partial / failed

Frontend polls GET /api/v1/scrape/{id} every 2s until complete
Results displayed in ResultsCard component
```

---

## 2. Output Schema (committed Day 1, not changed)

```json
{
  "university_name": "string | null",
  "program_name": "string | null",
  "degree_level": "string | null",
  "program_duration": "string | null",
  "intake_months": ["string"] | null,
  "application_deadlines": "string | null",
  "min_academic_requirement": "string | null",
  "accepted_qualifications": "string | null",
  "english_requirements": {
    "ielts": "string | null",
    "toefl": "string | null",
    "pte": "string | null",
    "duolingo": "string | null",
    "notes": "string | null"
  } | null,
  "tuition_fees": {
    "domestic": "string | null",
    "international": "string | null",
    "currency": "string | null",
    "notes": "string | null"
  } | null,
  "other_fees": "string | null",
  "scholarships": "string | null",
  "work_experience": "string | null",
  "other_requirements": "string | null",
  "confidence_notes": "string | null",
  "field_sources": {
    "field_name": "source_url",
    "english_requirements.ielts": "source_url"
  },
  "source_urls": ["string"],
  "status": "processing | running | success | partial | failed | cached",
  "created_at": "ISO8601 timestamp",
  "elapsed_seconds": "number",
  "llm_model": "string"
}
```

**Rules:**
- Fields not found on page → `null` (never hallucinated)
- `confidence_notes` used for genuine ambiguity only
- Schema is fixed — no fields removed, additions allowed

---

## 3. API Contract

All endpoints under `/api/v1/`:

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/scrape` | `{url, context_hint?}` | `{scrape_id, status}` |
| GET | `/scrape/{id}` | — | Full ScrapeResult |
| DELETE | `/scrape/{id}` | — | 204 |
| GET | `/scrapes` | `?page&limit&search&status` | `{data[], total, page, pages}` |
| POST | `/scrapes/batch` | `{urls[]}` | `{batch_id, scrape_ids[], total, estimated_seconds}` |
| GET | `/batch/{id}` | — | `{total, completed, processing, success_count, ...}` |
| GET | `/scrapes/export/csv` | `?all=true` or `?scrape_ids=id1,id2` | CSV download |
| GET | `/health` | — | `{status, version}` |

---

## 4. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Backend | FastAPI (Python 3.12) | Async, fast, great for background tasks |
| Database | MongoDB Atlas | Schema-flexible, JSON-native, free tier |
| Primary LLM | Gemini 2.5 Flash | Best quality/cost, large context window |
| Fallback LLM 1 | Groq llama-3.3-70b | Fast cloud inference, separate quota |
| Fallback LLM 2 | Ollama qwen2.5:1.5b | Local, no quota, works offline |
| Fallback LLM 3 | Gemini 2.5 Flash-Lite | Higher RPM limit than Flash |
| HTTP fetching | httpx (async) | Fast, follows redirects, async-native |
| JS rendering | Playwright (Chromium) | Better async support than Selenium |
| HTML parsing | BeautifulSoup + lxml | Fast, reliable |
| PDF extraction | pdfplumber | Best text extraction quality |
| Frontend | React 19 + TanStack Router/Query | Modern, type-safe, fast |
| Styling | Tailwind CSS v4 | Utility-first, dark mode |
| Frontend hosting | Vercel | Zero-config, free |
| Backend hosting | Railway | Auto-deploy from GitHub |

---

## 5. Team Responsibilities

| Task | Owner |
|---|---|
| Scraping pipeline (fetcher, link extractor, PDF extractor) | AI Automation |
| LLM extraction engine (prompts, routing, fallbacks) | AI Automation |
| Regex pre-extraction and validation | AI Automation |
| Rate limiting and retry logic | AI Automation |
| All backend API endpoints | AI Automation |
| MongoDB schema and queries | AI Automation |
| Dashboard UI (all routes and components) | Web Dev |
| Results card, timeline, history, batch UI | Web Dev |
| Export (JSON/CSV) | Web Dev |
| API integration (frontend ↔ backend) | Web Dev |
| Validation testing (10+ universities) | AI Automation |
| Production Migration Document | AI Automation |

---

## 6. Phase 2 Decision

**Decision:** Attempt Phase 2 after Phase 1 is fully validated.  
**Approach:** Google Custom Search API to find program URL from university name + program name, then run Phase 1 pipeline on discovered URL.  
**Status:** Not yet implemented — Phase 1 prioritised.

---

## 7. Definition of Done (Phase 1)

- [ ] Scrapes 10+ real university pages successfully
- [ ] All 15 required fields in schema
- [ ] Null fields returned with notes (no hallucinations)
- [ ] JS-rendered pages handled (Playwright)
- [ ] Multi-page following working
- [ ] PDF extraction working
- [ ] Dashboard shows all fields clearly
- [ ] History, batch, export all working
- [ ] Validation report documented
- [ ] Production migration document written
- [ ] README with setup instructions
- [ ] Clean Git repo with meaningful commits
