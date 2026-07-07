# pipeline/ai_extractor.py
# extract_fields(combined_text, primary_url, context_hint) -> dict
#
# Hybrid extraction: regex pre-extraction → AI call → regex fallbacks.
# Model routing (priority order):
#   PRIMARY   — OpenRouter (google/gemini-2.5-flash)
#   FALLBACK 1 — Gemini direct API (gemini-2.5-flash)
#   FALLBACK 2 — Groq Llama (fast cloud, separate quota)
#   FALLBACK 3 — Qwen2.5:1.5b via Ollama (local, no quota)

import asyncio
import json
import logging
import random
import re
import time

import httpx

from config import settings
from prompts.extraction_prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from utils.text_cleaner import clean_html, clean_text_content, truncate_text
from utils.section_classifier import classify_text_sections, get_admission_focused_text
from utils.field_validators import validate_extraction_result
from utils.page_classifier import classify_page, FIELD_TO_PAGE_TYPES
from pipeline.regex_extractor import (
    extract_regex_hints,
    extract_regex_hints_from_sections,
    apply_regex_fallbacks,
    format_hints_for_prompt,
)

logger = logging.getLogger(__name__)

# ── OpenRouter (primary) ──────────────────────────────────────────────────────
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Priority order of free models (July 2026) - VERIFIED WORKING IDs:
# 1. Llama 3.3 70B: Stable, excellent extraction, good context
# 2. Nemotron Super 120B: Large context, complex reasoning, agentic workflows
# 3. GPT-OSS 120B: Strong JSON formatting, code generation
# 4. Qwen3-Next 80B: Fast inference, good structured extraction (if available)
_OPENROUTER_FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",      # Primary: Stable, verified working
    "nvidia/nemotron-3-super-120b-a12b:free",      # Fallback 1: Large context
    "openai/gpt-oss-120b:free",                    # Fallback 2: JSON cleanup
    "qwen/qwen3-next-80b-a3b-instruct:free",       # Fallback 3: Fast (if on account)
]
_OPENROUTER_MODEL = _OPENROUTER_FREE_MODELS[0]  # Default to Llama 3.3 70B

# ── Gemini direct (fallback 1) ────────────────────────────────────────────────
_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={api_key}"
)
_GEMINI_FALLBACK_MODEL = "gemini-2.5-flash"  # direct Gemini API model

# ── Ollama (local fallback) ────────────────────────────────────────────────────
_OLLAMA_URL = "http://localhost:11434/api/chat"
_OLLAMA_MODEL = "qwen2.5:1.5b"  # Fast on CPU (~10-15s), good enough for fallback

# ── Groq (cloud fallback) ─────────────────────────────────────────────────────
_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.3-70b-versatile"  # Best Groq model for structured extraction

# ── Gemini rate-limit controls ────────────────────────────────────────────────
# Free tier: 10 RPM, ~4M TPM for Flash. We enforce 3 RPM to stay safe.
_GEMINI_SEMAPHORE = asyncio.Semaphore(1)   # Only ONE Gemini call at a time globally

# Retry delays: 30s → 60s → 120s → 180s → 240s  (aggressive backoff)
_RETRY_DELAYS = [30, 60, 120, 180, 240]
_MAX_RETRIES = len(_RETRY_DELAYS)

# ── Request rate tracker ──────────────────────────────────────────────────────
_MAX_RPM = 3                                # Hard cap: 3 requests per minute
_request_timestamps: list[float] = []       # Rolling window of recent call times


def _enforce_rpm_limit() -> float:
    """
    Returns how many seconds to sleep to stay under _MAX_RPM.
    Prunes timestamps older than 60s from the rolling window.
    """
    now = time.monotonic()
    # Drop timestamps older than 60 seconds
    cutoff = now - 60.0
    while _request_timestamps and _request_timestamps[0] < cutoff:
        _request_timestamps.pop(0)

    if len(_request_timestamps) >= _MAX_RPM:
        # Oldest request in window — sleep until it falls out of the 60s window
        oldest = _request_timestamps[0]
        wait = (oldest + 60.0) - now
        return max(0.0, wait)
    return 0.0

_EXPECTED_KEYS = [
    "university_name", "program_name", "degree_level", "program_duration",
    "intake_months", "application_deadlines", "min_academic_requirement",
    "accepted_qualifications", "english_requirements", "tuition_fees",
    "other_fees", "scholarships", "work_experience", "other_requirements",
    "confidence_notes",
]

_NULL_RESULT = {k: None for k in _EXPECTED_KEYS}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _looks_like_html(text: str) -> bool:
    return bool(re.search(r"<[a-zA-Z][^>]{0,100}>", text))


def _extract_json_from_text(raw: str) -> dict | None:
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def _parse_llm_response(raw: str) -> dict:
    # Temporary debug for Oxford issues
    if len(raw) < 100:
        print(f"[DEBUG] Very short response ({len(raw)} chars): {raw}")
    elif "ox.ac.uk" in raw or len(raw) > 3000:
        print(f"[DEBUG] Large response ({len(raw)} chars), first 300: {raw[:300]}")
    
    try:
        result = json.loads(raw.strip())
        if isinstance(result, dict):
            for key in _EXPECTED_KEYS:
                if key not in result:
                    result[key] = None
            return result
    except json.JSONDecodeError as e:
        if len(raw) > 1000:  # Only log for substantial responses
            print(f"[DEBUG] JSON error on {len(raw)} char response: {e}")
            print(f"[DEBUG] Response end: ...{raw[-200:]}")

    logger.warning("[ai_extractor] primary JSON parse failed, trying regex extraction")
    result = _extract_json_from_text(raw)
    if result:
        for key in _EXPECTED_KEYS:
            if key not in result:
                result[key] = None
        return result

    logger.error("[ai_extractor] could not parse LLM response as JSON")
    failed = dict(_NULL_RESULT)
    failed["confidence_notes"] = "LLM returned unparseable response"
    return failed


def _safe_fallback(reason: str) -> dict:
    result = dict(_NULL_RESULT)
    result["confidence_notes"] = reason
    return result


# ── API call ──────────────────────────────────────────────────────────────────

def _compress_context_for_free_models(context: str, max_chars: int = 15000) -> str:
    """
    Aggressively compress context for OpenRouter free models.
    
    Free models have tight context limits and reject long inputs.
    Target: <15k chars (from typical 40k+ raw context).
    
    Strategy:
    1. Take only the most information-dense sections
    2. Truncate long pages to first 1000 chars
    3. Remove low-priority/generic content
    """
    if len(context) <= max_chars:
        return context
    
    logger.info(f"[compress] Input {len(context)} chars → compressing to ~{max_chars}")
    
    # Split into sections
    sections = context.split("\n===")
    compressed_sections = []
    char_budget = max_chars
    
    # Priority order: fees > english > admission > program > scholarships > intake
    SECTION_PRIORITY = {
        "FEES INFORMATION": 1,
        "ENGLISH REQUIREMENTS": 2,
        "ADMISSION DETAILS": 3,
        "PROGRAM INFORMATION": 4,
        "SCHOLARSHIPS": 5,
        "INTAKE": 6,
    }
    
    # Sort sections by priority
    sorted_sections = []
    for section in sections:
        priority = 999
        for key, p in SECTION_PRIORITY.items():
            if key in section.upper():
                priority = p
                break
        sorted_sections.append((priority, section))
    
    sorted_sections.sort(key=lambda x: x[0])
    
    # Take sections until budget exhausted
    for priority, section in sorted_sections:
        section_text = "===" + section if compressed_sections else section
        
        # Truncate individual section if too long
        if len(section_text) > 3000:
            # Keep header + first 2500 chars
            header_end = section_text.find("\n", 100)
            if header_end == -1:
                header_end = 100
            header = section_text[:header_end]
            body = section_text[header_end:header_end + 2500]
            section_text = header + body + "\n...[truncated for brevity]"
        
        if len(section_text) <= char_budget:
            compressed_sections.append(section_text)
            char_budget -= len(section_text)
        else:
            # Last section — take what we can
            if char_budget > 500:
                compressed_sections.append(section_text[:char_budget])
            break
    
    result = "\n".join(compressed_sections)
    logger.info(f"[compress] Output {len(result)} chars ({len(result)/len(context)*100:.1f}% of original)")
    return result


async def _call_openrouter(user_prompt: str, model: str | None = None, compress: bool = True) -> str:
    """
    Call OpenRouter API with intelligent free model fallback chain.
    
    Free model priority (July 2026):
    1. Llama 3.3 70B Instruct (stable, verified working)
    2. Nemotron Super 120B (large context, complex reasoning)
    3. GPT-OSS 120B (strong JSON formatting)
    4. Qwen3-Next 80B (fast inference, if available on account)
    
    Implements automatic fallback when a model fails or hits rate limits.
    
    Args:
        user_prompt: The full user prompt (may be long)
        model: Specific model to try first (optional)
        compress: If True, compress context for free models (default True)
    """
    if not settings.openrouter_api_key:
        raise ValueError("No OPENROUTER_API_KEY configured")

    # Compress context if needed for free models
    if compress and len(user_prompt) > 20000:
        logger.info(f"[openrouter] Large context detected ({len(user_prompt)} chars) — compressing")
        user_prompt = _compress_context_for_free_models(user_prompt, max_chars=15000)

    # Determine model priority list
    if model:
        # If specific model requested, use it first, then fallbacks
        models_to_try = [model] + [m for m in _OPENROUTER_FREE_MODELS if m != model]
    else:
        # Use configured model or default free model chain
        configured_model = getattr(settings, "openrouter_model", None)
        if configured_model and configured_model in _OPENROUTER_FREE_MODELS:
            models_to_try = [configured_model] + [m for m in _OPENROUTER_FREE_MODELS if m != configured_model]
        else:
            models_to_try = _OPENROUTER_FREE_MODELS

    last_error = None
    
    for attempt_model in models_to_try:
        try:
            logger.info(f"[openrouter] Trying {attempt_model} ({len(user_prompt)} chars)")
            
            payload = {
                "model": attempt_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
                "temperature": 0,
                "max_tokens": settings.llm_max_tokens,
                "response_format": {"type": "json_object"},
            }
            headers = {
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://uniscraper.app",
                "X-Title": "UniScraper",
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(_OPENROUTER_URL, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

            result = data["choices"][0]["message"]["content"]
            logger.info(f"[openrouter] ✅ {attempt_model} succeeded")
            return result
            
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get("error", {}).get("message", "")
            except:
                pass
            
            if status_code == 404:
                logger.warning(f"[openrouter] {attempt_model} not found (404) — model may not exist — trying next")
            elif status_code == 400:
                logger.warning(f"[openrouter] {attempt_model} bad request (400): {error_detail} — trying next")
            elif status_code == 429:
                logger.warning(f"[openrouter] {attempt_model} rate limited (429) — trying next model")
            elif status_code >= 500:
                logger.warning(f"[openrouter] {attempt_model} server error ({status_code}) — trying next model")
            else:
                logger.warning(f"[openrouter] {attempt_model} failed ({status_code}): {error_detail} — trying next")
            last_error = e
            await asyncio.sleep(1)  # Brief pause before next attempt
            
        except (KeyError, IndexError) as e:
            logger.warning(f"[openrouter] {attempt_model} returned unexpected structure — trying next model")
            last_error = e
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.warning(f"[openrouter] {attempt_model} failed: {type(e).__name__}: {e} — trying next model")
            last_error = e
            await asyncio.sleep(1)
    
    # All models failed
    raise ValueError(
        f"All OpenRouter free models failed. Last error: {last_error}. "
        f"Models tried: {', '.join(models_to_try)}"
    )


# ── Gemini direct API caller ──────────────────────────────────────────────────

async def _call_gemini(user_prompt: str, model: str | None = None) -> str:
    async with _GEMINI_SEMAPHORE:  # Only one Gemini call at a time globally
        # ── RPM rate limiter (rolling window) ─────────────────────────────────
        rpm_wait = _enforce_rpm_limit()
        if rpm_wait > 0:
            logger.info(f"[rate-limit] RPM cap reached — waiting {rpm_wait:.1f}s")
            await asyncio.sleep(rpm_wait)

        # Track this request in the rolling window
        _request_timestamps.append(time.monotonic())

        use_model = model or _GEMINI_FALLBACK_MODEL
        url = _GEMINI_URL.format(
            model=use_model,
            api_key=settings.gemini_api_key,
        )
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Unexpected Gemini response structure: {e} — {str(data)[:300]}")


# ── Ollama (local) caller ─────────────────────────────────────────────────────

async def _call_ollama(user_prompt: str) -> str:
    """
    Call local Ollama with Qwen2.5:7b.
    No rate limiting — runs locally.
    Truncates to 6k chars to keep CPU inference under ~45s.
    """
    MAX_LOCAL_CHARS = 6000
    if len(user_prompt) > MAX_LOCAL_CHARS:
        # Always truncate from the end — the page text is at the bottom
        user_prompt = user_prompt[:MAX_LOCAL_CHARS] + "\n--- END COMBINED PAGE TEXT ---"

    payload = {
        "model": _OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": 2000,  # Enough for the JSON schema
        },
    }

    async with httpx.AsyncClient(timeout=45.0) as client:  # 1.5b runs in ~10-15s on CPU
        response = await client.post(_OLLAMA_URL, json=payload)
        response.raise_for_status()
        data = response.json()

    try:
        return data["message"]["content"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Unexpected Ollama response structure: {e} — {str(data)[:300]}")


async def _is_ollama_available() -> bool:
    """Quick health check — returns True if Ollama is running locally."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get("http://localhost:11434/api/tags")
            return r.status_code == 200
    except Exception:
        return False


# ── Groq caller ───────────────────────────────────────────────────────────────

async def _call_groq(user_prompt: str) -> str:
    """
    Call Groq API (OpenAI-compatible) with llama-3.3-70b-versatile.
    Fast cloud inference, separate quota from Gemini.
    Truncates to 12k chars — Groq has generous context but we keep it focused.
    """
    MAX_GROQ_CHARS = 12000
    if len(user_prompt) > MAX_GROQ_CHARS:
        user_prompt = user_prompt[:MAX_GROQ_CHARS] + "\n--- END COMBINED PAGE TEXT ---"

    payload = {
        "model": _GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        "temperature": 0,
        "max_tokens": 4000,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(_GROQ_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Unexpected Groq response structure: {e} — {str(data)[:300]}")


# ── Public entry point ────────────────────────────────────────────────────────

def calculate_page_relevance_score(page_data: dict, field_group: str) -> int:
    """
    Calculate relevance score for a page based on field group.
    Uses page_type + URL + content keywords with proper negative weights.
    
    CRITICAL FIX: University-wide admission/tuition pages (e.g., /tuition-and-fees/)
    must score VERY HIGH for fee extraction — these pages contain the actual amounts.
    """
    url = page_data.get("url", "")
    url = url.lower() if isinstance(url, str) else ""
    
    page_type = page_data.get("page_type", "other")
    
    content = page_data.get("content", "")
    # Handle case where content might be a list (defensive programming)
    if isinstance(content, list):
        content = " ".join(str(item) for item in content)
    elif not isinstance(content, str):
        content = str(content) if content else ""
    content = content.lower()

    score = 50  # base

    # ── LAYER 1: Page type match ──────────────────────────────────────────────
    PAGE_TYPE_SCORES = {
        "english_requirements": {
            "english_requirements": +80, "admissions": +20, "programme_overview": +30,
            "tuition": -20, "scholarships": -20, "curriculum": -30,
        },
        "tuition_fees": {
            "tuition": +100,  # INCREASED: Tuition pages are the source of truth
            "programme_overview": +40,  # REDUCED: Main page rarely has actual fees
            "admissions": +60,  # INCREASED: Admission pages often link to tuition info
            "english_requirements": -20, "curriculum": -30,
        },
        "application_deadlines": {
            "admissions": +80, "programme_overview": +40,
            "tuition": -10, "english_requirements": -10,
        },
        "program_duration": {
            "programme_overview": +80, "admissions": +20,
            "tuition": -10, "english_requirements": -20,
        },
        "intake_months": {
            "programme_overview": +80, "admissions": +30,
            "tuition": -10, "english_requirements": -20,
        },
        "scholarships": {
            "scholarships": +100, "tuition": +40, "admissions": +30,
            "programme_overview": +20, "curriculum": -20,
        },
    }
    if field_group in PAGE_TYPE_SCORES:
        score += PAGE_TYPE_SCORES[field_group].get(page_type, 0)

    # ── LAYER 2: URL signals ──────────────────────────────────────────────────
    # CRITICAL: University-wide tuition pages
    if field_group == "tuition_fees":
        # MAXIMUM priority for actual tuition/fee pages
        TUITION_EXACT_URLS = [
            "tuition-and-fees",
            "tuition_and_fees",
            "cost-of-attendance",
            "tuition-fees",
            "graduate-tuition",
            "tuition/",
            "/fees/graduate",
            "/fees/international",
            "admissions-and-aid/tuition",
            "admissions/tuition",
            "bursar",
            "student-accounts",
        ]
        
        if any(pattern in url for pattern in TUITION_EXACT_URLS):
            score += 200  # This page almost certainly has fees
        
        # PENALISE constructed/fake sub-pages
        # These are URLs that end in /fees but were constructed
        # by appending /fees to a .html page URL
        if (url.endswith(".html/fees") or
            ".html/entry-requirements" in url or
            ".html/how-to-apply" in url or
            ".html/overview" in url or
            ".html/english" in url):
            score -= 100  # These are fake constructed URLs
        
        # Medium priority for admission/aid pages (if not already boosted)
        elif any(pattern in url for pattern in ["admissions-and-aid", "financial-aid", "funding"]):
            score += 60
    
    # Positive: specialized sub-pages
    if any(t in url for t in ["language", "english", "ielts", "toefl"]):
        if field_group == "english_requirements":
            score += 40
        else:
            score -= 20
    if any(t in url for t in ["fee", "tuition", "cost", "funding"]):
        if field_group == "tuition_fees":
            score += 40  # Additional boost on top of the specific patterns above
        elif field_group == "scholarships":
            score += 30
        else:
            score -= 10
    if any(t in url for t in ["scholarship", "bursary", "financial-aid", "financial_aid", "fellowship", "grant"]):
        if field_group == "scholarships":
            score += 80
        else:
            score -= 10
    if any(t in url for t in ["admission", "apply", "entry", "requirement"]):
        if field_group in ("application_deadlines", "program_duration"):
            score += 20
    # Negative: generic university-wide pages
    if any(t in url for t in ["visa", "immigration", "cas", "undergraduate"]):
        score -= 30

    # ── LAYER 3: Content keyword density ─────────────────────────────────────
    FIELD_KEYWORDS = {
        "english_requirements": ["ielts", "toefl", "pte", "duolingo", "english language requirement", "language proficiency"],
        "tuition_fees":         ["tuition fee", "course fee", "tuition and fee", "per credit hour", 
                                 "£", "$", "aud", "cad", "per year", "per annum", "annual fee", 
                                 "indicative fee", "semester fee", "per semester",
                                 "graduate tuition", "resident tuition", "non-resident tuition"],
        "application_deadlines":["deadline", "closing date", "apply by", "applications close", "applications due", "due date", "key dates", "key application", "applications open"],
        "program_duration":     ["12 months", "24 months", "full-time", "part-time", "duration", "programme length"],
        "intake_months":        ["september intake", "january intake", "october intake", "march intake", "july intake",
                                 "february intake", "start date", "intake", "commence", "commencement",
                                 "march, july", "march and july", "semester 1", "semester 2"],
        "scholarships":         ["scholarship", "bursary", "financial aid", "fellowship", "grant", "funding",
                                 "award", "stipend", "assistantship", "waiver"],
    }
    if field_group in FIELD_KEYWORDS:
        hits = sum(1 for kw in FIELD_KEYWORDS[field_group] if kw in content)
        score += hits * 20

    return max(0, score)


def build_field_specific_context(pages_data: list, field_group: str, max_chars: int = 8000) -> str:
    """
    Return ALL relevant pages for a field group above a relevance threshold.
    
    ARCHITECTURAL CHANGE (bucket-based approach):
    - Score all pages for relevance to field_group
    - Include ALL pages with score > threshold (not just top 1)
    - Order by score (best first)
    - Truncate only when hitting char limit
    
    This ensures the LLM sees all relevant information, not just
    the single "best" page which might not have complete info.
    
    Example: For tuition_fees, include:
    - Main fees page (score=410)
    - International fees page (score=390) 
    - Scholarship page (score=270)
    - Funding page (score=250)
    
    Let the LLM synthesize from multiple sources rather than
    forcing the routing layer to pick a single "truth" page.
    """
    if not pages_data:
        return ""

    scored = sorted(
        [(calculate_page_relevance_score(p, field_group), p) for p in pages_data],
        key=lambda x: x[0],
        reverse=True,
    )
    
    # COMPREHENSIVE LOGGING: Show ALL scores to analyze threshold
    if field_group in ["tuition_fees", "english_requirements"]:
        logger.info(f"[ai_extractor] {field_group} - ALL PAGE SCORES:")
        for i, (score, page) in enumerate(scored[:15], 1):  # Show top 15
            url_short = page['url'][-70:] if len(page['url']) > 70 else page['url']
            logger.info(
                f"  #{i:2d} score={score:3d} words={page.get('word_count', 0):5d} "
                f"url={url_short}"
            )
        if len(scored) > 15:
            logger.info(f"  ... and {len(scored) - 15} more pages")
    
    # RELEVANCE THRESHOLD: Include all pages above this score
    # - Positive score = relevant
    # - >100 = highly relevant
    # - >200 = critical page
    # TODO: After testing 20-30 universities, adjust based on empirical data
    RELEVANCE_THRESHOLD = 60
    
    parts = []
    used = 0
    pages_included = 0
    
    for score, page_data in scored:
        # STOP if below relevance threshold
        if score < RELEVANCE_THRESHOLD:
            logger.debug(
                f"[ai_extractor] {field_group}: stopping at score={score} "
                f"(threshold={RELEVANCE_THRESHOLD})"
            )
            break
        
        content = page_data.get("content", "")
        url     = page_data.get("url", "")
        ptype   = page_data.get("page_type", "other")
        header  = f"\n--- {ptype.upper()} (score:{score}) | {url} ---\n"

        available = max_chars - used
        if available <= 500:
            logger.debug(f"[ai_extractor] {field_group}: char limit reached")
            break

        if len(header) + len(content) <= available:
            parts.append(header + content)
            used += len(header) + len(content)
            pages_included += 1
        else:
            # Truncate to fit
            keep = available - len(header) - 30
            if keep > 500:
                parts.append(header + content[:keep] + "\n...[truncated]")
                used = max_chars
                pages_included += 1
            break

    result = "\n".join(parts)
    top_url = scored[0][1].get("url", "")[-50:] if scored else ""
    top_score = scored[0][0] if scored else 0
    
    # Count how many pages were above threshold but couldn't fit
    above_threshold = sum(1 for score, _ in scored if score >= RELEVANCE_THRESHOLD)
    below_threshold = sum(1 for score, _ in scored if score < RELEVANCE_THRESHOLD)
    
    # Show score distribution for analysis
    score_distribution = []
    for threshold in [200, 150, 100, 80, 50, 0]:
        count = sum(1 for score, _ in scored if score >= threshold)
        score_distribution.append(f">={threshold}:{count}")
    
    logger.info(
        f"[ai_extractor] {field_group}: included {pages_included}/{above_threshold} "
        f"relevant pages (threshold={RELEVANCE_THRESHOLD}), {len(result)} chars, "
        f"top_score={top_score}"
    )
    logger.info(
        f"[ai_extractor] {field_group}: score distribution: "
        + " | ".join(score_distribution) + f" | total={len(scored)}"
    )
    
    return result


async def extract_fields(
    combined_text: str,
    primary_url: str,
    context_hint: str = "",
    pages_data: list = None,
    content_format: str = "html",   # "markdown" (Tier 1/2) or "html" (Tier 3)
) -> dict:
    """
    Hybrid extraction pipeline:
      1. Regex pre-extraction (fast, deterministic)
      2. Smart truncation (keeps relevant paragraphs)
      3. Single Gemini call with regex hints injected into prompt
      4. Regex fallback (fills nulls the LLM missed)

    content_format="markdown": content is already clean fit_markdown from Crawl4AI
      or Firecrawl — skip the clean_html() step (it would corrupt markdown tables).
    content_format="html": legacy path — run clean_html() first.

    Returns dict with all _EXPECTED_KEYS (None where not found).
    """
    # ── Step 1: Clean text ────────────────────────────────────────────────────
    raw_chars = len(combined_text)

    if content_format == "markdown":
        # Already clean — just normalise whitespace, don't strip structure
        cleaned = clean_text_content(combined_text)
        print(f"[AI] Markdown input (Tier 1/2) — skipping clean_html()")
    elif _looks_like_html(combined_text):
        cleaned = clean_html(combined_text)
    else:
        cleaned = clean_text_content(combined_text)

    clean_chars = len(cleaned)

    # ── Step 2: Field-specific context building ──────────────────────────────
    if pages_data:
        # Each field gets its own ranked page selection — 6000-10000 chars each
        # Increased budgets for exhaustive crawling — information is often buried deep
        # CRITICAL: Tuition fees get MORE budget because they're often on separate pages
        program_context  = build_field_specific_context(pages_data, "program_duration",      6000)
        english_context  = build_field_specific_context(pages_data, "english_requirements",  6000)
        fees_context     = build_field_specific_context(pages_data, "tuition_fees",          10000)  # INCREASED
        admission_context= build_field_specific_context(pages_data, "application_deadlines", 8000)
        intake_context   = build_field_specific_context(pages_data, "intake_months",         6000)
        scholarship_context = build_field_specific_context(pages_data, "scholarships",       6000)

        # Deduplicate: if intake top page == admission top page, skip the repeat
        intake_section = ""
        if intake_context and intake_context.strip() != admission_context.strip():
            intake_section = "=== INTAKE & DATES ===\n" + intake_context

        scholarship_section = ""
        if scholarship_context:
            scholarship_section = "=== SCHOLARSHIPS & FUNDING ===\n" + scholarship_context

        extraction_text = "\n\n".join(filter(None, [
            "=== PROGRAM INFORMATION ===\n"  + program_context,
            "=== ENGLISH REQUIREMENTS ===\n" + english_context,
            "=== FEES INFORMATION ===\n"     + fees_context,
            "=== ADMISSION DETAILS ===\n"    + admission_context,
            intake_section,
            scholarship_section,
        ])).strip()

        print(f"[ROUTING] Built targeted context: {len(extraction_text)} chars")
    else:
        sections = classify_text_sections(cleaned, primary_url)
        admission_focused = get_admission_focused_text(sections)
        extraction_text = admission_focused if admission_focused else cleaned
        print(f"[SECTION] Using section classification: {len(extraction_text)} chars")

    # ── Step 3: Page-aware regex pre-extraction ──────────────────────────────
    # Extract section headers for context-aware regex
    section_headers = []
    if "===" in extraction_text:
        section_headers = [line.strip() for line in extraction_text.split('\n') 
                          if line.strip().startswith('===') and line.strip().endswith('===')]
    
    hints = extract_regex_hints_from_sections(extraction_text, section_headers)
    hints_block = format_hints_for_prompt(hints)

    found_hints = [k for k, v in hints.items() if v]
    if found_hints:
        print(f"[REGEX] Pre-extracted: {', '.join(found_hints)}")

    # ── Step 4: Smart truncation ──────────────────────────────────────────────
    truncated = truncate_text(extraction_text, settings.llm_context_limit)
    final_chars = len(truncated)

    print(f"[AI] Raw: {raw_chars:,} -> cleaned: {clean_chars:,} -> "
          f"section-focused: {len(extraction_text):,} -> sending: {final_chars:,} chars to Gemini ({settings.llm_model})")
    logger.info(f"[ai_extractor] {primary_url} — "
                f"raw={raw_chars} clean={clean_chars} focused={len(extraction_text)} sending={final_chars}")

    # ── Step 5: Build prompt with regex hints ─────────────────────────────────
    user_prompt = USER_PROMPT_TEMPLATE.format(
        source_url=primary_url,
        context_hint=context_hint or "Extract all available program information",
        regex_hints=hints_block,
        page_text=truncated,
    )

    # ── Step 6: LLM call — Gemini 2.5 Flash (primary) → Groq → Ollama ────────
    raw_response = None
    model_used = "unknown"

    # ── PRIMARY: Gemini 2.5 Flash direct API ──────────────────────────────────
    if settings.gemini_api_key:
        try:
            logger.info("[ai_extractor] Trying Gemini 2.5 Flash (primary)")
            print("[ai_extractor] Using Gemini 2.5 Flash")
            raw_response = await _call_gemini(user_prompt, model="gemini-2.5-flash")
            model_used = "gemini-2.5-flash"
            logger.info("[ai_extractor] Gemini extraction succeeded")
            print("[ai_extractor] Gemini extraction complete")
        except Exception as gem_err:
            logger.warning(f"[ai_extractor] Gemini failed: {type(gem_err).__name__}: {gem_err} — falling back to Groq")
            print(f"[ai_extractor] Gemini error — falling back to Groq")
            raw_response = None
    else:
        print("[ai_extractor] No GEMINI_API_KEY configured")

    # ── FALLBACK 1: Groq ──────────────────────────────────────────────────────
    if raw_response is None:
        if settings.groq_api_key:
            try:
                logger.info(f"[ai_extractor] Trying Groq/{_GROQ_MODEL} (fallback 2)")
                print(f"[ai_extractor] Using Groq/{_GROQ_MODEL}")
                raw_response = await _call_groq(user_prompt)
                model_used = f"groq/{_GROQ_MODEL}"
                logger.info("[ai_extractor] Groq fallback succeeded")
                print("[ai_extractor] Groq extraction complete")
            except Exception as groq_err:
                logger.warning(f"[ai_extractor] Groq fallback failed: {type(groq_err).__name__}: {groq_err}")
                print(f"[ai_extractor] Groq error — trying Ollama")
        else:
            print("[ai_extractor] No GROQ_API_KEY — skipping Groq fallback")

    # ── FALLBACK 3: Ollama (local) ─────────────────────────────────────────────
    if raw_response is None:
        try:
            if await _is_ollama_available():
                logger.info(f"[ai_extractor] Trying Ollama/{_OLLAMA_MODEL} (fallback 3)")
                print(f"[ai_extractor] Using Ollama/{_OLLAMA_MODEL}")
                raw_response = await _call_ollama(user_prompt)
                model_used = f"ollama/{_OLLAMA_MODEL}"
                logger.info("[ai_extractor] Ollama fallback succeeded")
                print("[ai_extractor] Ollama extraction complete")
            else:
                print("[ai_extractor] Ollama not running — all fallbacks exhausted")
        except Exception as ollama_err:
            logger.warning(f"[ai_extractor] Ollama fallback failed: {type(ollama_err).__name__}: {ollama_err}")

    if raw_response is None:
        fallback = _safe_fallback("Gemini extraction failed after all retries")
        validated_fallback = validate_extraction_result(fallback, extraction_text)
        r = apply_regex_fallbacks(validated_fallback, hints, extraction_text)
        r["_model_used"] = "failed"
        return r

    # ── Step 7: Parse LLM response ────────────────────────────────────────────
    result = _parse_llm_response(raw_response)

    # ── Step 8: Apply validation rules ────────────────────────────────────────
    result = validate_extraction_result(result, extraction_text)

    # ── Step 9: Regex fallbacks — fill any nulls the LLM missed ──────────────
    result = apply_regex_fallbacks(result, hints, extraction_text)

    non_null = sum(1 for v in result.values() if v is not None)
    status_str = "success" if non_null > 4 else "sparse"
    print(f"[AI] Extraction {status_str} - {non_null} non-null fields (model: {model_used})")
    logger.info(f"[ai_extractor] {primary_url} — {non_null} non-null fields extracted (model: {model_used})")

    result["_model_used"] = model_used  # internal key, stripped before saving
    return result
