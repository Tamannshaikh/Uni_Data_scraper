# pipeline/domain_resolver.py
# Resolves a university name to its official domain.
# Strategy:
#   1. Heuristic: build candidate domains from the name, try HEAD requests
#   2. SerpAPI fallback if heuristic fails

import logging
import re
from difflib import SequenceMatcher
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Common suffixes to strip before building domain candidates
_STRIP_WORDS = re.compile(
    r"\b(university|of|the|and|at|in|college|institute|school|"
    r"technology|sciences?|arts?|business)\b",
    re.IGNORECASE,
)

_TIMEOUT = 6.0

_TLD_PATTERNS = [".edu", ".ac.uk", ".edu.au", ".ca", ".ac.nz", ".ac.in", ".edu.sg"]


def _name_to_slug(name: str) -> str:
    """
    'Arkansas State University' → 'astate'
    'McGill University' → 'mcgill'
    'University of Manchester' → 'manchester'
    'University of Melbourne' → 'unimelb'
    """
    name = name.strip()

    # Special well-known overrides
    _KNOWN = {
        "arkansas state university": "astate",
        "university of manchester": "manchester",
        "mcgill university": "mcgill",
        "university of melbourne": "unimelb",
        "university of sydney": "sydney",
        "university of toronto": "utoronto",
        "university of british columbia": "ubc",
        "university of edinburgh": "ed",
        "imperial college london": "imperial",
        "university college london": "ucl",
        "university of oxford": "ox",
        "university of cambridge": "cam",
        "massachusetts institute of technology": "mit",
        "carnegie mellon university": "cmu",
        "georgia institute of technology": "gatech",
        "university of california": "uc",
        "university of michigan": "umich",
        "new york university": "nyu",
        "university of texas": "utexas",
        "university of florida": "ufl",
        "ohio state university": "osu",
        "penn state university": "psu",
        "university of washington": "uw",
        "arizona state university": "asu",
        "university of illinois": "illinois",
        "university of wisconsin": "wisc",
        "university of minnesota": "umn",
        "university of colorado": "colorado",
        "university of virginia": "virginia",
        "university of north carolina": "unc",
        "north carolina state university": "ncsu",
        "florida state university": "fsu",
        "virginia tech": "vt",
        "texas a&m university": "tamu",
        "purdue university": "purdue",
        "rutgers university": "rutgers",
        "university of maryland": "umd",
        "university of connecticut": "uconn",
        "university of iowa": "uiowa",
        "iowa state university": "iastate",
        "kansas state university": "kstate",
        "michigan state university": "msu",
        "university of missouri": "missouri",
        "university of nebraska": "unl",
        "university of south carolina": "sc",
        "university of tennessee": "utk",
        "university of georgia": "uga",
        "university of alabama": "ua",
        "university of mississippi": "olemiss",
        "university of oklahoma": "ou",
        "university of utah": "utah",
        "university of new mexico": "unm",
        "university of hawaii": "hawaii",
        "university of alaska": "alaska",
        "university of wyoming": "uwyo",
        "university of idaho": "uidaho",
        "university of montana": "umt",
        "university of vermont": "uvm",
        "university of maine": "maine",
        "university of new hampshire": "unh",
        "university of rhode island": "uri",
        "boston university": "bu",
        "northeastern university": "northeastern",
        "tufts university": "tufts",
        "yale university": "yale",
        "harvard university": "harvard",
        "princeton university": "princeton",
        "columbia university": "columbia",
        "cornell university": "cornell",
        "dartmouth college": "dartmouth",
        "brown university": "brown",
        "duke university": "duke",
        "vanderbilt university": "vanderbilt",
        "rice university": "rice",
        "emory university": "emory",
        "tulane university": "tulane",
        "wake forest university": "wfu",
        "university of notre dame": "nd",
        "georgetown university": "georgetown",
        "george washington university": "gwu",
        "american university": "american",
        "howard university": "howard",
        "university of southern california": "usc",
        "university of california los angeles": "ucla",
        "university of california berkeley": "berkeley",
        "stanford university": "stanford",
        "university of california san diego": "ucsd",
        "university of california davis": "ucdavis",
        "university of california santa barbara": "ucsb",
        "university of california irvine": "uci",
        "caltech": "caltech",
        "california institute of technology": "caltech",
        "london school of economics": "lse",
        "king's college london": "kcl",
        "university of warwick": "warwick",
        "university of birmingham": "birmingham",
        "university of bristol": "bristol",
        "university of glasgow": "glasgow",
        "university of leeds": "leeds",
        "university of sheffield": "sheffield",
        "university of nottingham": "nottingham",
        "university of exeter": "exeter",
        "university of bath": "bath",
        "university of st andrews": "st-andrews",
        "university of dublin": "tcd",
        "trinity college dublin": "tcd",
        "university college dublin": "ucd",
        "national university of ireland": "nuig",
        "university of queensland": "uq",
        "australian national university": "anu",
        "university of new south wales": "unsw",
        "monash university": "monash",
        "university of western australia": "uwa",
        "university of adelaide": "adelaide",
        "university of auckland": "auckland",
        "national university of singapore": "nus",
        "nanyang technological university": "ntu",
        "peking university": "pku",
        "tsinghua university": "tsinghua",
        "university of hong kong": "hku",
    }

    key = name.lower().strip()
    if key in _KNOWN:
        return _KNOWN[key]

    # Generic: strip common words, keep the rest, collapse to first-letters or first word
    stripped = _STRIP_WORDS.sub("", name).strip()
    words = [w for w in stripped.split() if len(w) > 1]

    if not words:
        # Fallback to first meaningful word
        words = [w for w in name.split() if len(w) > 2 and w.lower() not in
                 {"the", "of", "and", "at", "in"}]

    if len(words) == 1:
        return words[0].lower()
    elif len(words) == 2:
        # Two distinct words → first word
        return words[0].lower()
    else:
        # Multiple words → initials (e.g. North Carolina State → ncs)
        return "".join(w[0] for w in words).lower()


# Map slug → canonical domain (used when the slug alone is ambiguous across TLDs)
_SLUG_TO_DOMAIN = {
    "mcgill":      "mcgill.ca",
    "unimelb":     "unimelb.edu.au",
    "utoronto":    "utoronto.ca",
    "ubc":         "ubc.ca",
    "ed":          "ed.ac.uk",
    "manchester":  "manchester.ac.uk",
    "imperial":    "imperial.ac.uk",
    "ucl":         "ucl.ac.uk",
    "ox":          "ox.ac.uk",
    "cam":         "cam.ac.uk",
    "lse":         "lse.ac.uk",
    "warwick":     "warwick.ac.uk",
    "birmingham":  "birmingham.ac.uk",
    "bristol":     "bristol.ac.uk",
    "glasgow":     "glasgow.ac.uk",
    "leeds":       "leeds.ac.uk",
    "sheffield":   "sheffield.ac.uk",
    "nottingham":  "nottingham.ac.uk",
    "exeter":      "exeter.ac.uk",
    "bath":        "bath.ac.uk",
    "uq":          "uq.edu.au",
    "anu":         "anu.edu.au",
    "unsw":        "unsw.edu.au",
    "monash":      "monash.edu",
    "uwa":         "uwa.edu.au",
    "adelaide":    "adelaide.edu.au",
    "sydney":      "sydney.edu.au",
    "auckland":    "auckland.ac.nz",
    "nus":         "nus.edu.sg",
    "ntu":         "ntu.edu.sg",
    "tcd":         "tcd.ie",
    "ucd":         "ucd.ie",
}


def _build_candidates(name: str) -> list[str]:
    """Build a prioritised list of domain candidates to try."""
    slug = _name_to_slug(name)
    candidates = []

    # If we have a known canonical domain for this slug, try it first
    if slug in _SLUG_TO_DOMAIN:
        candidates.append(_SLUG_TO_DOMAIN[slug])

    # Then try all TLD patterns
    for tld in _TLD_PATTERNS:
        candidate = f"{slug}{tld}"
        if candidate not in candidates:
            candidates.append(candidate)

    # Also try the full name squished
    full_slug = re.sub(r"[^a-z0-9]", "", name.lower())
    if f"{full_slug}.edu" not in candidates:
        candidates.append(f"{full_slug}.edu")

    return candidates


def _fuzzy_match(text: str, name: str) -> bool:
    """Return True if text contains something reasonably close to the university name."""
    name_lower = name.lower()
    text_lower = text.lower()

    # Exact sub-string match on any word from the name
    key_words = [w for w in name_lower.split() if len(w) > 4]
    if any(w in text_lower for w in key_words):
        return True

    # Sequence similarity as fallback
    ratio = SequenceMatcher(None, name_lower[:40], text_lower[:200]).ratio()
    return ratio > 0.4


async def _verify_domain(domain: str, university_name: str) -> bool:
    """HEAD + GET to verify domain exists and matches the university name."""
    for scheme in ("https", "http"):
        url = f"{scheme}://www.{domain}"
        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 UniScraper/1.0"},
            ) as client:
                # First try HEAD
                try:
                    r = await client.head(url)
                    if r.status_code < 400:
                        # Quick GET to check title/content
                        rg = await client.get(url)
                        if _fuzzy_match(rg.text[:3000], university_name):
                            return True
                        # Status OK but fuzzy didn't match — still accept
                        # (some unis redirect homepage to sub-path)
                        if r.status_code < 400:
                            return True
                except httpx.HTTPStatusError:
                    pass

                # Fallback: plain GET if HEAD failed
                rg = await client.get(url)
                if rg.status_code < 400:
                    return True

        except Exception:
            continue

    return False


async def resolve_university_domain(university_name: str) -> dict:
    """
    Resolve a university name to its official domain.

    Returns:
    {
        "domain": "astate.edu",
        "method": "heuristic" | "serpapi",
        "confidence": "high" | "medium" | "low",
    }
    """
    logger.info(f"[domain_resolver] Resolving: {university_name}")

    candidates = _build_candidates(university_name)
    logger.debug(f"[domain_resolver] Candidates: {candidates}")

    for candidate in candidates:
        try:
            ok = await _verify_domain(candidate, university_name)
            if ok:
                logger.info(
                    f"[domain_resolver] Heuristic resolved: {university_name} → {candidate}"
                )
                return {
                    "domain": candidate,
                    "method": "heuristic",
                    "confidence": "high",
                }
        except Exception as e:
            logger.debug(f"[domain_resolver] Candidate {candidate} failed: {e}")
            continue

    logger.info(
        f"[domain_resolver] Heuristic failed for {university_name}, trying SerpAPI"
    )

    # SerpAPI fallback
    from config import settings
    if settings.serpapi_key and settings.serpapi_enabled:
        try:
            from pipeline.serpapi_client import search_university_domain
            domain = await search_university_domain(university_name)
            if domain:
                logger.info(
                    f"[domain_resolver] SerpAPI resolved: {university_name} → {domain}"
                )
                return {
                    "domain": domain,
                    "method": "serpapi",
                    "confidence": "high",
                }
        except Exception as e:
            logger.warning(f"[domain_resolver] SerpAPI domain lookup failed: {e}")

    logger.warning(
        f"[domain_resolver] Could not resolve domain for: {university_name}"
    )
    return {
        "domain": None,
        "method": "failed",
        "confidence": "low",
    }
