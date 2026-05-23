# UniScraper Backend

AI-powered university admission data extraction API. Scrapes program pages, extracts structured admission data using an LLM, and serves results via a REST API.

---

## Prerequisites

- Python 3.11+
- Node.js (required by Playwright for browser binaries)
- MongoDB (local or Atlas)
- OpenRouter API key

---

## Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd uniscraper-backend

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Playwright browser (Chromium only)
playwright install chromium
```

---

## Environment Setup

```bash
cp .env.example .env
```

Open `.env` and fill in:

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `MONGODB_URI` | MongoDB connection string |
| `DB_NAME` | Database name (default: `autonova_scraper`) |
| `MAX_SUBPAGES` | Max sub-pages to fetch per scrape (default: 4) |
| `MAX_PDFS` | Max PDFs to extract per page (default: 2) |
| `LLM_MODEL` | OpenRouter model ID (default: `google/gemini-flash-1.5`) |
| `CORS_ORIGINS` | Comma-separated allowed origins |

---

## Running Locally

```bash
uvicorn main:app --reload
```

API available at: `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs`

---

## Running Tests

```bash
# All unit tests
pytest tests/

# Integration tests only (requires real API keys)
pytest tests/ -m integration

# Validation suite (10 universities)
pytest tests/validation/ -v
```

---

## API Reference

### `POST /api/v1/scrape`
Start a new scrape.

**Request body:**
```json
{
  "url": "https://university.edu/programs/cs",
  "context_hint": "fees for international students"
}
```

**Response:**
```json
{
  "scrape_id": "abc123",
  "status": "processing"
}
```

---

### `GET /api/v1/scrape/{scrape_id}`
Get a scrape result by ID.

**Response:** Full `ScrapeResult` object.

---

### `GET /api/v1/scrapes`
List past scrapes (paginated).

**Query params:** `page` (default: 1), `limit` (default: 20)

**Response:**
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "pages": 3
}
```

---

### `POST /api/v1/scrapes/batch`
Start a batch scrape.

**Request body:**
```json
{
  "urls": ["https://uni-a.edu/prog-1", "https://uni-b.edu/prog-2"]
}
```

**Response:**
```json
{
  "batch_id": "batch_xyz",
  "total": 2,
  "status": "queued"
}
```

---

### `GET /api/v1/batch/{batch_id}`
Get batch job status and per-URL progress.

---

### `GET /api/v1/scrapes/export/csv`
Download all scrape results as a CSV file.

**Response:** `text/csv` attachment.

---

### `GET /health`
Health check.

**Response:** `{"status": "ok", "version": "1.0.0"}`

---

## Project Structure

| Folder/File | Purpose |
|---|---|
| `main.py` | FastAPI app entry point, router registration, CORS |
| `config.py` | Typed settings loaded from `.env` |
| `database.py` | Motor MongoDB client singleton, collection references |
| `models/` | Pydantic schemas for requests and responses |
| `routers/` | FastAPI route handlers, one file per feature area |
| `pipeline/` | Core scraping logic: fetch → extract links → extract PDFs → AI extract → merge |
| `prompts/` | LLM prompt strings, kept separate for easy tuning |
| `utils/` | Shared helpers: HTML cleaning, URL utilities, CSV building |
| `tests/` | Unit and integration tests |
| `tests/validation/` | 10-university validation suite with JSON result output |
| `scripts/` | Developer utilities: test a single URL, seed mock data |
