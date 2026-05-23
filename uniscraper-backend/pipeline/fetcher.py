# pipeline/fetcher.py
# fetch_page(url: str) -> dict
# Tries httpx first (fast path). Falls back to Playwright for JS-rendered pages.
# Returns a consistent dict — never raises.

import asyncio
import logging

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

_HTTPX_TIMEOUT = 15.0
_PLAYWRIGHT_TIMEOUT = 30_000  # ms
_MIN_WORD_COUNT = 200


def _count_words(html: str) -> int:
    """Quick word count on visible body text."""
    try:
        soup = BeautifulSoup(html, "lxml")
        body = soup.find("body")
        text = body.get_text(" ") if body else soup.get_text(" ")
        return len(text.split())
    except Exception:
        return 0


async def _fetch_with_httpx(url: str) -> dict:
    """Attempt to fetch the page with httpx. Returns result dict."""
    async with httpx.AsyncClient(
        timeout=_HTTPX_TIMEOUT,
        follow_redirects=True,
        headers=_HEADERS,
    ) as client:
        response = await client.get(url)
        html = response.text
        final_url = str(response.url)
        status_code = response.status_code
        word_count = _count_words(html)
        return {
            "html": html,
            "method_used": "httpx",
            "status_code": status_code,
            "final_url": final_url,
            "word_count": word_count,
            "error": None,
        }


async def _fetch_with_playwright(url: str) -> dict:
    """Fetch the page using a headless Chromium browser via Playwright."""
    # Temporarily disabled on Windows due to subprocess issues
    # TODO: Fix Windows Playwright integration
    raise Exception("Playwright temporarily disabled on Windows - use httpx fallback")


async def fetch_page(url: str) -> dict:
    """
    Fetch a web page, trying httpx first and falling back to Playwright
    if the page appears to be JS-rendered or returns an error status.

    Always returns a dict — never raises an exception.
    """
    logger.info(f"[fetcher] {url} — trying httpx...")

    # --- Attempt 1: httpx ---
    httpx_result = None
    try:
        httpx_result = await _fetch_with_httpx(url)

        # Accept the httpx result if it looks like real content
        if (
            httpx_result["status_code"] is not None
            and httpx_result["status_code"] < 400
            and httpx_result["word_count"] >= _MIN_WORD_COUNT
        ):
            logger.info(
                f"[fetcher] {url} — httpx OK, {httpx_result['word_count']} words"
            )
            return httpx_result

        reason = (
            f"status {httpx_result['status_code']}"
            if httpx_result["status_code"] and httpx_result["status_code"] >= 400
            else f"only {httpx_result['word_count']} words (JS-rendered?)"
        )
        logger.info(f"[fetcher] {url} — httpx insufficient ({reason}), trying Playwright...")

    except Exception as e:
        logger.info(f"[fetcher] {url} — httpx failed ({e}), trying Playwright...")

    # --- Attempt 2: Playwright ---
    try:
        pw_result = await _fetch_with_playwright(url)
        logger.info(
            f"[fetcher] {url} — playwright, {pw_result['word_count']} words"
        )
        return pw_result

    except Exception as e:
        logger.error(f"[fetcher] {url} — Playwright also failed: {type(e).__name__}: {e}")
        # Return whatever httpx got (even if thin), or a full-failure dict
        if httpx_result and httpx_result.get("html"):
            httpx_result["error"] = f"Playwright fallback failed: {e}"
            return httpx_result

        return {
            "html": None,
            "method_used": None,
            "status_code": None,
            "final_url": url,
            "word_count": 0,
            "error": str(e),
        }
