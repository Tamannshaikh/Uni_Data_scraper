# UniScraper — University Admission Intelligence

**Live Backend URL:** [https://huggingface.co/spaces/Tamanna1234/uniscraper-backend](https://huggingface.co/spaces/Tamanna1234/uniscraper-backend)

A full-stack AI extraction system that scrapes university program pages and structures admission data into a clean, queryable format. Built for the AutoNova Pod internship challenge.

**Features:**
- ✅ **Phase 1 — Single URL Scraping** — Extract structured admission data from any program URL
- ✅ **Phase 2 — University Program Discovery** — Search by university name, discover all programs, click to scrape
- ✅ **Three-Tier Fetching Pipeline** — Custom → Firecrawl → Crawl4AI waterfall for maximum reliability
- ✅ **Four-Tier AI Extraction** — Google Vertex AI → Gemini API → Groq → Ollama fallback chain
- ✅ **Multi-Search Discovery** — Jina AI → SerpAPI → SearchAPI for comprehensive program finding
- ✅ **Gap Detection & Targeted Recrawl** — Detects missing critical fields and fetches additional pages
- ✅ **Anti-Hallucination Rules** — AI models never invent data; all values traced to source URLs

---

## What it does

### Phase 1 — Single URL Scrape

Paste a university program URL → get structured admission data in **~60–140 seconds**:

- IELTS / TOEFL / PTE / Duolingo requirements
- Tuition fees (domestic + international, with itemized cost breakdowns)
- Application deadlines
- Academic entry requirements
- Program duration, intake months, degree level
- Scholarships and additional requirements

Every field includes `field_sources` attribution linking back to the exact source URL.

### Phase 2 — University Program Discovery ⭐ NEW

Type a university name → discover all available programs → click to scrape any of them:

1. **Domain Resolution** — resolves "Arkansas State University" → `astate.edu` automatically
2. **Program Discovery** — BFS crawls the site to find all program pages
3. **Program List** — displays grouped, filterable results (PhD / MBA / Master's / Bachelor's)
4. **One-click Scrape** — clicking any program card immediately triggers the Phase 1 pipeline

**⚠️ Note:** Phase 2 works well with some universities (Arkansas State, McGill, etc.) but may not find programs for all universities due to varying website structures, anti-bot protections, and catalog layouts. Phase 1 (single URL scraping) remains the most reliable method for extracting admission data.

---

## Architecture

```
Frontend (React 19 + TanStack Router)
    │
    ├── /            Single URL scraper (Phase 1)
    ├── /discover    University search + program discovery (Phase 2)
    ├── /batch       Multi-URL batch scraper
    └── /history     Past results archive
    │
    └── FastAPI Backend (Python 3.11+)
            │
            ├── Phase 2: Discovery Pipeline
            │     ├── Domain Resolver                   heuristic + search API fallback
            │     ├── Program Discovery                 BFS crawler with scoring
            │     ├── Jina AI Search                    primary search engine (10M free tokens)
            │     ├── SerpAPI Client                    fallback #1 for blocked sites
            │     ├── SearchAPI Client                  fallback #2 when SerpAPI exhausted
            │     └── Discovery Orchestrator            async + 24h MongoDB cache
            │
            ├── Phase 1: Scrape Pipeline
            │     ├── Three-Tier Intelligent Fetching
            │     │     ├── Tier 1: Custom (httpx → Playwright)  [FAST]
            │     │     ├── Tier 2: Firecrawl                    [CLOUDFLARE]
            │     │     └── Tier 3: Crawl4AI                     [DEEP CRAWL]
            │     │
            │     ├── Page Classifier       admissions / english / tuition / etc.
            │     ├── AI Extractor (Pass 1) Vertex AI → Gemini → Groq → Ollama
            │     ├── Gap Analyzer          detects missing critical fields
            │     ├── Targeted Recrawl      fetches 2–5 more pages if gaps found
            │     ├── AI Extractor (Pass 2) re-extraction with new pages
            │     ├── Regex Extractor       pre/post-LLM fallback layer
            │     ├── Field Validator       semantic sanity checks
            │     └── MongoDB               results + 24h cache
```

---

## Phase 2 — Discovery Details

### How domain resolution works

| Input | Method | Domain |
|---|---|---|
| "Arkansas State University" | Heuristic (slug → `astate.edu`) | `astate.edu` |
| "McGill University" | Known override → `mcgill.ca` | `mcgill.ca` |
| "University of Manchester" | Heuristic → `manchester.ac.uk` | `manchester.ac.uk` |
| Unknown university | SerpAPI web search fallback | varies |

The heuristic generates domain candidates (`.edu`, `.ac.uk`, `.edu.au`, `.ca`) and verifies them with a HEAD request. SerpAPI is only called when the heuristic fails.

### How program discovery works

```
domain resolved
    │
    ├── Step 1: Find index pages
    │     Try ~35 common paths (/programs, /study, /colleges, etc.)
    │     Low concurrency (3 at a time) to avoid rate-limiting
    │
    ├── Step 2: SerpAPI fallback (if Step 1 finds nothing)
    │     Two targeted searches for program + graduate pages
    │     Sibling search for program path patterns found
    │
    ├── Step 3: BFS crawl (depth ≤ 3, max 80 pages)
    │     Follow /programs/, /colleges/, /faculties/, /study/ links
    │     Prioritise /programs/* URLs to front of queue
    │     Skip: news, events, staff, login, campus, etc.
    │
    ├── Step 3b: SerpAPI fallback if BFS finds 0 programs
    │     Handles sites that serve index pages but block BFS
    │
    └── Step 4: Filter + deduplicate
          is_program_page(): degree keyword + not admin/listing
          Filter 404s, error pages, nav pages, class profiles
          Cap at 200 programs
```

### Performance

| University | Domain method | Programs found | Time | Notes |
|---|---|---|---|---|
| Arkansas State University | Heuristic | 16 | ~56s | ✅ Works well |
| McGill University | Heuristic | 6–8 | ~50–90s | ✅ Works well |
| University of Melbourne | SerpAPI (WAF-blocked) | varies | ~90s | ⚠️ Partial results |

**Discovery Reliability:** Phase 2 discovery works well with universities that have:
- Standard program catalog structures (`/programs/`, `/academics/`, etc.)
- Accessible BFS-friendly navigation
- Minimal anti-bot protections

Universities with heavy JavaScript rendering, strong WAF protection, or non-standard catalog layouts may return limited or no results. For best results, use Phase 1 (direct URL scraping) for critical data extraction.

Results are cached in MongoDB for 24 hours — repeat searches are instant.

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 19, TanStack Router/Query/Start, Tailwind CSS v4, shadcn/ui |
| Backend | FastAPI, Python 3.11+, asyncio |
| Crawling | Tier 1: Custom (httpx + Playwright), Tier 2: Firecrawl, Tier 3: Crawl4AI |
| Discovery | BFS crawler + Jina AI Search + SerpAPI + SearchAPI |
| Database | MongoDB Atlas (Motor async driver) |
| AI Extraction | Vertex AI → Gemini 2.5 Flash → Groq → Ollama (qwen2.5:1.5b) |
| HTML parsing | BeautifulSoup + lxml |

---

## Running locally

### Backend

```bash
cd uniscraper-backend

# Install deps (no venv needed if running directly)
pip install -r requirements.txt

# Copy and fill in your keys
cp .env.example .env

python main.py
# or: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Required `.env` values:

```env
GEMINI_API_KEY=your_gemini_key
MONGODB_URI=your_mongodb_atlas_uri

# Phase 2 — program discovery (at least one search API required)
JINA_API_KEY=your_jina_key         # primary, 10M free tokens at jina.ai
SERPAPI_KEY=your_serpapi_key       # fallback #1, free tier at serpapi.com
SEARCHAPI_KEY=your_searchapi_key   # fallback #2 when SerpAPI exhausted
```

Optional (recommended for production):
```env
# Google Vertex AI (recommended by reviewers for higher quotas)
VERTEX_ENABLED=true
VERTEX_PROJECT_ID=your_gcp_project_id
GOOGLE_APPLICATION_CREDENTIALS=./credentials/vertex-key.json

# Enhanced fetching
FIRECRAWL_API_KEY=your_key         # Tier 2 fetching
CRAWL4AI_ENABLED=true              # Tier 3 fetching

# Additional AI fallbacks
GROQ_API_KEY=your_key              # Fast fallback LLM
```

### Frontend

```bash
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## API

### Phase 1 — Scraping

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/scrape` | Start a scrape, returns `scrape_id` |
| `GET` | `/api/v1/scrape/{id}` | Poll for result |
| `DELETE` | `/api/v1/scrape/{id}` | Delete a result |
| `POST` | `/api/v1/scrapes/batch` | Queue multiple URLs (25s stagger) |
| `GET` | `/api/v1/batch/{id}` | Batch progress |
| `GET` | `/api/v1/scrapes` | History (paginated) |
| `GET` | `/api/v1/export/csv` | Export all results as CSV |

### Phase 2 — Discovery

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/discover` | Start discovery, returns `discovery_id` |
| `GET` | `/api/v1/discover/{id}` | Poll for result (programs list) |

### Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | `{"status": "ok"}` |

### Example — discover programs

```bash
# Start discovery
curl -X POST http://localhost:8000/api/v1/discover \
  -H "Content-Type: application/json" \
  -d '{"university_name": "Arkansas State University"}'

# Response
{ "discovery_id": "abc123", "status": "processing" }

# Poll until status = "success"
curl http://localhost:8000/api/v1/discover/abc123
```

Discovery response:
```json
{
  "university_name": "Arkansas State University",
  "domain": "astate.edu",
  "status": "success",
  "programs_count": 16,
  "programs": [
    { "program_name": "Master of Athletic Training", "degree_level": "Master's", "url": "https://..." },
    { "program_name": "MBA in Marketing", "degree_level": "MBA", "url": "https://..." }
  ],
  "elapsed_seconds": 55.9
}
```

---

## Anti-hallucination system

Gemini is strictly prohibited from inventing any values:

| ❌ Forbidden | ✅ Allowed |
|---|---|
| Invent IELTS/TOEFL scores | Extract from supplied page text |
| Estimate tuition fees | Return `null` for missing fields |
| Guess deadlines or GPA | Identify which page types are missing |
| Use prior knowledge | Suggest where to find missing data |

Every extracted value has a `field_sources` entry with the exact source URL.

---

## Rate limiting

- **Vertex AI / Gemini:** self-throttles to 3 RPM (semaphore + 20s gap + rolling window)
- **On 429:** auto-fallback Groq → Ollama → Gemini Flash-Lite
- **Batch:** 25s stagger between URLs
- **Discovery:** 3-concurrent max on index path checks, 5-concurrent on BFS
- **Jina AI:** tracked per request, free 10M tokens
- **SerpAPI:** tracked monthly, warns at 80 calls (free tier ~100/month)
- **SearchAPI:** used as final fallback when other search APIs exhausted
