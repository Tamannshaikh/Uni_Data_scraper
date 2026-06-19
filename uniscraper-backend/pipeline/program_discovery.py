# pipeline/program_discovery.py
# Discovers program pages on a university website.
# Uses BFS starting from known index paths, with SerpAPI fallback for
# Cloudflare-blocked sites.

import asyncio
import hashlib
import logging
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Keyword sets ──────────────────────────────────────────────────────────────

PROGRAM_KEYWORDS = [
    "program", "programme", "course", "degree",
    "masters", "master", "msc", "ma", "ms",
    "mba", "phd", "doctorate", "doctoral", "graduate",
    "postgraduate", "undergraduate", "bachelor",
    "certificate", "diploma", "taught",
]

DEGREE_LEVEL_MAP = {
    "phd": "PhD",
    "ph.d": "PhD",
    "doctorate": "PhD",
    "doctoral": "PhD",
    "dphil": "PhD",
    "d.phil": "PhD",
    "mba": "MBA",
    "m.b.a": "MBA",
    "msc": "Master's",
    "m.sc": "Master's",
    "master of": "Master's",
    "master's": "Master's",
    "masters": "Master's",
    "postgraduate": "Master's",
    "/ms-": "Master's",        # URL segment: /ms-in-cs, /ms-engineering
    "-ms-": "Master's",
    "meng": "Master's",
    "m.eng": "Master's",
    "mres": "Master's",
    "mphil": "Master's",
    "m.phil": "Master's",
    "llm": "Master's",
    "mfa": "Master's",
    "mpa": "Master's",
    "mph": "Master's",
    "med ": "Master's",        # Master of Education (with space to avoid "medical")
    "bachelor of": "Bachelor's",
    "bachelor's": "Bachelor's",
    "undergraduate": "Bachelor's",
    "/ba-": "Bachelor's",
    "/bsc-": "Bachelor's",
    "/beng-": "Bachelor's",
    "certificate": "Certificate",
    "diploma": "Diploma",
    "graduate certificate": "Certificate",
    "graduate diploma": "Diploma",
}

SKIP_KEYWORDS = [
    "news", "event", "events", "faculty", "staff", "research", "researcher",
    "alumni", "library", "campus", "campus-life", "athletics", "sport",
    "login", "portal", "search", "sitemap", "contact", "about-us",
    "careers", "jobs", "vacancies", "governance", "policy", "privacy",
    "cookie", "accessibility", "donate", "giving", "foundation",
    "calendar", "blog", "media", "press", "publications",
    "conference", "seminar", "workshop", "webinar",
    "class-profile", "class_profile",
    "study-trip", "study_trip",
    "international-students",
    "student-life", "campus-life",
]

# URL patterns that indicate an index/listing page (follow but don't include)
LISTING_PATTERNS = [
    r"/programs/?$",
    r"/programmes/?$",
    r"/courses/?$",
    r"/postgraduate/?$",
    r"/postgrad/?$",
    r"/graduate/?$",
    r"/masters/?$",
    r"/phd/?$",
    r"/study/?$",
    r"/academics/?$",
    r"/study/programs?/?$",
    r"/study/courses?/?$",
    r"/study/masters?/?$",
    r"/study/phd/?$",
    r"/find/postgraduate/?",
    r"/find/graduate/?",
    r"/find/",
    r"/search",
]

# Candidate index paths to try as BFS seeds
INDEX_PATHS = [
    "/programs",
    "/programs/index.html",
    "/programmes",
    "/study",
    "/courses",
    "/graduate-programs",
    "/graduate-programmes",
    "/postgraduate",
    "/postgraduate-programs",
    "/postgraduate-programmes",
    "/degrees",
    "/academics",
    "/academics/programs",
    "/academics/graduate-school",
    "/academics/graduate-school/index.html",
    "/study/programs",
    "/study/courses",
    "/find/postgraduate",
    "/graduate/programs",
    "/graduate/courses",
    "/school-of-graduate-studies/programs",
    "/admissions/programs",
    "/admissions-and-aid/graduate-admissions",
    "/admissions-and-aid/graduate-admissions/index.html",
    "/future-students/programs",
    "/prospective-students/programs",
    "/colleges",
    "/colleges/",
    "/faculties",
    "/departments",
    "/study/programs",
    "/study/courses",
    "/study/postgraduate",
    "/grad/programs",
    "/graduate/apply/programs",
    "/graduate-studies/programs",
    "/gradapplicants/programs",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_listing_page(url: str) -> bool:
    path = urlparse(url).path
    return any(re.search(pat, path, re.IGNORECASE) for pat in LISTING_PATTERNS)


def _should_skip(url: str) -> bool:
    url_lower = url.lower()
    return any(kw in url_lower for kw in SKIP_KEYWORDS)


def _guess_degree_level(url: str, title: str) -> str:
    combined = (url + " " + title).lower()
    # Priority order matters — check more specific first
    priority = [
        ("phd", "PhD"), ("ph.d", "PhD"), ("doctorate", "PhD"),
        ("doctoral", "PhD"), ("dphil", "PhD"),
        ("mba", "MBA"), ("m.b.a", "MBA"),
        ("master of", "Master's"), ("master's", "Master's"),
        ("masters", "Master's"), ("msc", "Master's"), ("m.sc", "Master's"),
        ("meng", "Master's"), ("mres", "Master's"), ("mphil", "Master's"),
        ("llm", "Master's"), ("mfa", "Master's"), ("mpa", "Master's"),
        ("mph", "Master's"), ("postgraduate", "Master's"),
        ("/ms-", "Master's"), ("-ms-", "Master's"),
        ("bachelor of", "Bachelor's"), ("bachelor's", "Bachelor's"),
        ("undergraduate", "Bachelor's"), ("/ba-", "Bachelor's"),
        ("/bsc-", "Bachelor's"), ("/beng-", "Bachelor's"),
        ("graduate certificate", "Certificate"),
        ("graduate diploma", "Diploma"),
        ("certificate", "Certificate"),
        ("diploma", "Diploma"),
    ]
    for kw, level in priority:
        if kw in combined:
            return level
    return "Unknown"


def _clean_program_name(title: str, university_name: str = "") -> str:
    """Strip university name and common suffixes from a page title."""
    name = title
    # Strip common separators and university name
    for sep in [" | ", " - ", " — ", " :: ", " · "]:
        if sep in name:
            parts = name.split(sep)
            # Keep the part that's NOT the university name
            if university_name:
                uni_lower = university_name.lower()
                parts = [p for p in parts if uni_lower not in p.lower()]
            if parts:
                name = parts[0].strip()
                break

    # Strip generic suffixes
    for suffix in [
        "| Study with us", "| Postgraduate", "| Graduate",
        "| Masters", "| PhD", "| Programs",
    ]:
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()

    return name.strip() or title


async def _fetch_html(url: str, timeout: float = 8.0) -> tuple[str, int]:
    """Fetch HTML with a simple httpx GET. Returns (html, status_code)."""
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers=_HEADERS,
        ) as client:
            r = await client.get(url)
            return r.text, r.status_code
    except Exception as e:
        logger.debug(f"[program_discovery] fetch error {url}: {e}")
        return "", 0


def _extract_links(html: str, base_url: str, domain: str) -> list[str]:
    """Extract all internal links from HTML."""
    try:
        soup = BeautifulSoup(html, "lxml")
        links = []
        # Normalize domain — strip www. for comparison
        domain_bare = domain.replace("www.", "")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue
            abs_url = urljoin(base_url, href)
            parsed = urlparse(abs_url)
            if not parsed.scheme.startswith("http"):
                continue
            link_domain = parsed.netloc.replace("www.", "")
            # Same domain or subdomain (e.g. math.mcgill.ca for mcgill.ca)
            if link_domain == domain_bare or link_domain.endswith("." + domain_bare):
                clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                clean = clean.rstrip("/")
                if clean:
                    links.append(clean)
        return list(set(links))
    except Exception:
        return []


def _get_title(html: str) -> str:
    try:
        soup = BeautifulSoup(html, "lxml")
        tag = soup.find("title")
        return tag.get_text(strip=True) if tag else ""
    except Exception:
        return ""


def _word_count(html: str) -> int:
    try:
        soup = BeautifulSoup(html, "lxml")
        return len(soup.get_text().split())
    except Exception:
        return 0


def _is_program_page(url: str, html: str, title: str) -> bool:
    """
    Determine if a page is an individual program page (vs. a listing/admin page).
    Returns True if this looks like an individual program.
    """
    url_lower = url.lower()
    title_lower = title.lower()

    # Must contain at least one degree-level keyword in URL or title
    has_degree_kw = any(kw in url_lower or kw in title_lower for kw in DEGREE_LEVEL_MAP)
    if not has_degree_kw:
        return False

    # If URL itself matches a listing pattern → it's a listing
    if _is_listing_page(url):
        return False

    # Exclude generic structural/admin pages that mention degree levels
    # but are not individual program pages
    ADMIN_PATH_PATTERNS = [
        r"/undergraduate-academics/?$",
        r"/graduate-academics/?$",
        r"/tuition-and-fees",
        r"/tuition-fees",
        r"/admissions-and-aid/?$",
        r"/graduate-admissions/?$",
        r"/undergraduate-admissions/?$",
        r"/how-to-apply",
        r"/apply/?$",
        r"/scholarships/?$",
        r"/financial-aid",
        r"/financial-support",
        r"/contact",
        r"/about/?$",
        r"/events",
        r"/news",
        r"/faculty-staff",
        r"/our-team",
        r"/staff/?$",
        r"/research/?$",
        r"/library/?$",
        r"/campus",
        r"/index\.html?$",
        r"/index/?$",
        r"/class-profile",
        r"/current-students",
        r"/international-students/?$",
        r"/study-trips?",
        r"/student-life",
        r"/alumni/?$",
    ]
    path = urlparse(url).path
    for pat in ADMIN_PATH_PATTERNS:
        if re.search(pat, path, re.IGNORECASE):
            return False

    # Generic titles that are NOT individual programs:
    GENERIC_TITLE_PATTERNS = [
        r"(error 404|page not found|404 not found|403 forbidden|access denied)",
        r"^search(\s*\||\s+results)",
        r"^azure waf",
        r"^undergraduate academics",
        r"^graduate academics",
        r"^tuition (and|&) fees",
        r"^fees and funding",
        r"^graduate admissions",
        r"^undergraduate admissions",
        r"^how to apply",
        r"^scholarships$",
        r"^financial aid",
        r"^contact",
        r"^about$",
        r"^home$",
        r"^search$",
        r"^faculty$",
        r"^staff$",
        r"^program finder",
        r"^all programs",
        r"^our programs",
        r"^browse programs",
        r"^class profile",
        r"^meet ",         # "Meet [Name]: ..."
        r"^international students$",
        r"^current students",
        r"^study trip",
        r"^(international )?study (trip|abroad)",
        r"^mini-mba",      # short courses, not degree programs
        r"^executive education",
        r"^short course",
        r"^phd\s*[–\-—]",  # "PhD – Research topic" = PhD position, not a program
        r"^phd\s*\(",       # "PhD (topic)" styled individual research projects
    ]
    for pat in GENERIC_TITLE_PATTERNS:
        if re.search(pat, title_lower, re.IGNORECASE):
            return False

    # Check if this page is a PROGRAM INDEX (listing) by counting
    # sibling links in the same directory with degree keywords
    try:
        parsed = urlparse(url)
        base_path = parsed.path.rstrip("/")
        dir_path = "/".join(base_path.split("/")[:-1])

        soup = BeautifulSoup(html, "lxml")
        sibling_prog_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("/"):
                abs_href = href
            elif href.startswith("http"):
                abs_href = urlparse(href).path
            else:
                abs_href = dir_path + "/" + href

            if abs_href.startswith(dir_path + "/") and abs_href != base_path:
                link_lower = abs_href.lower()
                if any(kw in link_lower for kw in DEGREE_LEVEL_MAP):
                    sibling_prog_links.append(abs_href)

        if len(sibling_prog_links) > 10:
            return False
    except Exception:
        pass

    return True


# ── Main discovery function ───────────────────────────────────────────────────

async def discover_programs(
    domain: str,
    university_name: str = "",
    max_pages: int = 30,
) -> list[dict]:
    """
    Discover individual program pages on a university domain.

    Strategy:
    1. Find index pages by trying common paths
    2. If none found, fall back to SerpAPI site: search
    3. BFS crawl from index pages, scoring links by program relevance
    4. Filter to actual program pages (not listing pages)
    5. Return up to 200 deduplicated program entries

    Returns:
    [
        {
            "program_name": "Master of Business Administration",
            "degree_level": "MBA",
            "url": "https://...",
        },
        ...
    ]
    """
    base = f"https://{domain}"
    logger.info(f"[program_discovery] Starting discovery for {domain}")

    # ── Step 1: Find index pages ──────────────────────────────────────────────
    # Try both bare domain and www. prefix
    bases_to_try = [base]
    if not domain.startswith("www."):
        bases_to_try.append(f"https://www.{domain}")

    index_pages: list[str] = []
    semaphore = asyncio.Semaphore(3)  # polite concurrency — avoid 429s

    async def check_index(path: str, b: str) -> str | None:
        async with semaphore:
            await asyncio.sleep(0.1)  # small delay to avoid rate-limiting
            url = f"{b}{path}"
            html, status = await _fetch_html(url, timeout=6.0)
            # Lower threshold for known program listing pages
            min_words = 100 if any(seg in path for seg in ["/programs", "/courses", "/study"]) else 300
            if status == 200 and html and _word_count(html) > min_words:
                logger.info(f"[program_discovery] Index page found: {url}")
                return url
            return None

    # Deduplicate paths (INDEX_PATHS has some duplicates)
    unique_paths = list(dict.fromkeys(INDEX_PATHS))
    tasks = [check_index(p, b) for p in unique_paths for b in bases_to_try]
    results = await asyncio.gather(*tasks)
    # Deduplicate found index pages by path
    seen_paths: set[str] = set()
    for r in results:
        if r:
            path_key = urlparse(r).path
            if path_key not in seen_paths:
                seen_paths.add(path_key)
                index_pages.append(r)

    # ── Step 2: SerpAPI fallback if no index pages found ─────────────────────
    # Also collect any direct program pages SerpAPI returns
    serpapi_direct_programs: list[dict] = []

    if not index_pages:
        logger.warning(
            f"[program_discovery] No index pages via direct paths for {domain} "
            f"— trying SerpAPI fallback"
        )
        from config import settings
        if settings.serpapi_key and settings.serpapi_enabled:
            from pipeline.serpapi_client import search_program_pages
            candidate_urls = await search_program_pages(domain, university_name)

            # Track which parent paths we found program pages at
            # so we can do a targeted second SerpAPI search for siblings
            found_program_paths: list[str] = []

            for candidate_url in candidate_urls:
                html, status = await _fetch_html(candidate_url)
                if status != 200 or not html or _word_count(html) < 100:
                    continue
                title = _get_title(html)
                is_prog = _is_program_page(candidate_url, html, title)
                if is_prog:
                    serpapi_direct_programs.append({
                        "program_name": _clean_program_name(title, university_name),
                        "degree_level": _guess_degree_level(candidate_url, title),
                        "url": candidate_url,
                    })
                    logger.info(f"[program_discovery] SerpAPI direct program: {candidate_url}")

                    # Record the parent path pattern for sibling search
                    parsed_c = urlparse(candidate_url)
                    parent_path = "/".join(parsed_c.path.rstrip("/").split("/")[:-1])
                    if parent_path and parent_path not in found_program_paths:
                        found_program_paths.append(parent_path)

                    # Try parent directory as BFS seed
                    if parent_path and parent_path not in seen_paths:
                        parent_url = f"{parsed_c.scheme}://{parsed_c.netloc}{parent_path}"
                        ph, ps = await _fetch_html(parent_url)
                        if ps == 200 and ph and _word_count(ph) > 200:
                            seen_paths.add(parent_path)
                            index_pages.append(parent_url)
                            logger.info(f"[program_discovery] SerpAPI parent as index: {parent_url}")
                elif _word_count(html) > 300:
                    index_pages.append(candidate_url)
                    logger.info(f"[program_discovery] SerpAPI index candidate: {candidate_url}")

            # If we have program path patterns but no usable index pages,
            # do a targeted SerpAPI search for more siblings at those paths
            if found_program_paths and len(serpapi_direct_programs) < 10:
                for prog_path in found_program_paths[:2]:  # max 2 extra searches
                    path_prefix = prog_path.strip("/").split("/")[0]  # e.g. "gradapplicants"
                    sibling_query = f'site:{domain}/{path_prefix} (master OR phd OR msc OR mba OR bachelor)'
                    try:
                        from pipeline.serpapi_client import _track_usage
                        import httpx as _httpx
                        await _track_usage()
                        async with _httpx.AsyncClient(timeout=15.0) as c2:
                            resp2 = await c2.get(
                                "https://serpapi.com/search",
                                params={
                                    "q": sibling_query,
                                    "api_key": settings.serpapi_key,
                                    "num": 10,
                                    "engine": "google",
                                },
                            )
                            sibling_data = resp2.json()
                        sibling_urls = [
                            r.get("link") for r in sibling_data.get("organic_results", [])
                            if r.get("link")
                        ]
                        logger.info(
                            f"[program_discovery] Sibling search for /{path_prefix} "
                            f"returned {len(sibling_urls)} URLs"
                        )
                        for surl in sibling_urls:
                            if surl in [p["url"] for p in serpapi_direct_programs]:
                                continue
                            shtml, sstatus = await _fetch_html(surl)
                            if sstatus != 200 or not shtml or _word_count(shtml) < 100:
                                continue
                            stitle = _get_title(shtml)
                            if _is_program_page(surl, shtml, stitle):
                                serpapi_direct_programs.append({
                                    "program_name": _clean_program_name(stitle, university_name),
                                    "degree_level": _guess_degree_level(surl, stitle),
                                    "url": surl,
                                })
                                logger.info(f"[program_discovery] Sibling program: {surl}")
                    except Exception as e2:
                        logger.debug(f"[program_discovery] Sibling search failed: {e2}")

        if not index_pages and not serpapi_direct_programs:
            logger.warning(
                f"[program_discovery] No index pages found for {domain} (even after SerpAPI)"
            )
            return []

    if not index_pages:
        logger.info(
            f"[program_discovery] Using only SerpAPI direct programs — {len(serpapi_direct_programs)} found"
        )
        return serpapi_direct_programs[:200]

    logger.info(
        f"[program_discovery] Using {len(index_pages)} index page(s) as BFS seeds"
    )

    # ── Step 3: BFS crawl from index pages ───────────────────────────────────
    visited: set[str] = set(index_pages)
    content_hashes: set[str] = set()
    program_candidates: list[dict] = []

    # Queue: (url, depth)
    queue: list[tuple[str, int]] = [(u, 0) for u in index_pages]
    pages_scanned = 0

    fetch_semaphore = asyncio.Semaphore(5)

    async def fetch_and_process(url: str, depth: int) -> dict | None:
        nonlocal pages_scanned
        async with fetch_semaphore:
            html, status = await _fetch_html(url)
            pages_scanned += 1

            if status != 200 or not html or _word_count(html) < 50:
                return None

            # Skip soft-404 / error pages by title
            raw_title_check = _get_title(html)
            if re.search(
                r"(error 404|page not found|404 not found|403 forbidden|access denied)",
                raw_title_check, re.IGNORECASE
            ):
                return None

            # Content dedup
            ch = hashlib.md5(html[:2000].encode("utf-8", errors="ignore")).hexdigest()
            if ch in content_hashes:
                return None
            content_hashes.add(ch)

            title = raw_title_check
            clean_title = _clean_program_name(title, university_name)
            degree_level = _guess_degree_level(url, title)

            is_program = _is_program_page(url, html, title)
            all_links = _extract_links(html, url, domain)

            return {
                "url": url,
                "html": html,
                "title": title,
                "clean_title": clean_title,
                "degree_level": degree_level,
                "is_program": is_program,
                "links": all_links,
                "depth": depth,
            }

    while queue and pages_scanned < max_pages:
        # Process current wave
        current_wave = queue[:10]  # Max 10 concurrent
        queue = queue[10:]

        wave_tasks = [fetch_and_process(url, depth) for url, depth in current_wave]
        wave_results = await asyncio.gather(*wave_tasks)

        for page_info in wave_results:
            if page_info is None:
                continue

            url = page_info["url"]
            depth = page_info["depth"]

            # If it's a program page, add to candidates
            if page_info["is_program"]:
                program_candidates.append({
                    "program_name": page_info["clean_title"],
                    "degree_level": page_info["degree_level"],
                    "url": url,
                })

            # Queue links for next depth (max depth=3 to handle deeper structures)
            if depth < 3:
                for link in page_info["links"]:
                    if link in visited:
                        continue
                    if _should_skip(link):
                        continue
                    link_lower = link.lower()
                    # Always follow /programs/, /programmes/, /colleges/, /faculties/
                    # these are structural pages that lead to individual programs
                    structural = any(seg in link_lower for seg in [
                        "/programs/", "/programmes/", "/colleges/",
                        "/faculties/", "/schools/", "/departments/",
                        "/graduate-school", "/postgraduate", "/graduate/",
                        "/study/", "/gradapplicants/",
                    ])
                    # Also follow links with program keywords in URL
                    has_prog_kw = any(kw in link_lower for kw in PROGRAM_KEYWORDS)
                    if structural or has_prog_kw or _is_listing_page(link):
                        visited.add(link)
                        # Prioritize /programs/ and /programme/ links to front of queue
                        if "/programs/" in link_lower or "/programme" in link_lower:
                            queue.insert(0, (link, depth + 1))
                        else:
                            queue.append((link, depth + 1))

    logger.info(
        f"[program_discovery] BFS complete — "
        f"{pages_scanned} pages scanned, "
        f"{len(program_candidates)} program candidates"
    )

    # ── Step 3b: SerpAPI fallback if BFS found nothing ───────────────────────
    # This handles sites that serve index pages fine but block BFS crawling
    if not program_candidates and not serpapi_direct_programs:
        logger.warning(
            f"[program_discovery] BFS found 0 programs on {domain} — "
            f"trying SerpAPI fallback"
        )
        from config import settings
        if settings.serpapi_key and settings.serpapi_enabled:
            from pipeline.serpapi_client import search_program_pages
            candidate_urls = await search_program_pages(domain, university_name)
            found_paths: list[str] = []

            for candidate_url in candidate_urls:
                html, status = await _fetch_html(candidate_url)
                if status != 200 or not html or _word_count(html) < 100:
                    continue
                title = _get_title(html)
                if re.search(r"(error 404|page not found|403 forbidden)", title, re.IGNORECASE):
                    continue
                if _is_program_page(candidate_url, html, title):
                    serpapi_direct_programs.append({
                        "program_name": _clean_program_name(title, university_name),
                        "degree_level": _guess_degree_level(candidate_url, title),
                        "url": candidate_url,
                    })
                    logger.info(f"[program_discovery] SerpAPI (post-BFS) program: {candidate_url}")
                    parsed_c = urlparse(candidate_url)
                    pp = "/".join(parsed_c.path.rstrip("/").split("/")[:-1])
                    if pp and pp not in found_paths:
                        found_paths.append(pp)

            # Sibling search for each path pattern found
            if found_paths and len(serpapi_direct_programs) < 10:
                for prog_path in found_paths[:2]:
                    path_prefix = prog_path.strip("/").split("/")[0]
                    sibling_query = (
                        f'site:{domain}/{path_prefix} '
                        f'(master OR phd OR msc OR mba OR bachelor OR graduate)'
                    )
                    try:
                        from pipeline.serpapi_client import _track_usage
                        import httpx as _httpx
                        await _track_usage()
                        async with _httpx.AsyncClient(timeout=15.0) as c2:
                            resp2 = await c2.get(
                                "https://serpapi.com/search",
                                params={
                                    "q": sibling_query,
                                    "api_key": settings.serpapi_key,
                                    "num": 10,
                                    "engine": "google",
                                },
                            )
                            sibling_data = resp2.json()
                        existing_urls = {p["url"] for p in serpapi_direct_programs}
                        for surl in [r.get("link") for r in sibling_data.get("organic_results", []) if r.get("link")]:
                            if surl in existing_urls:
                                continue
                            shtml, sstatus = await _fetch_html(surl)
                            if sstatus != 200 or not shtml or _word_count(shtml) < 100:
                                continue
                            stitle = _get_title(shtml)
                            if re.search(r"(error 404|page not found|403)", stitle, re.IGNORECASE):
                                continue
                            if _is_program_page(surl, shtml, stitle):
                                serpapi_direct_programs.append({
                                    "program_name": _clean_program_name(stitle, university_name),
                                    "degree_level": _guess_degree_level(surl, stitle),
                                    "url": surl,
                                })
                                existing_urls.add(surl)
                                logger.info(f"[program_discovery] Sibling program: {surl}")
                    except Exception as e2:
                        logger.debug(f"[program_discovery] Sibling search failed: {e2}")

    # ── Step 4: Deduplicate by normalized program name ────────────────────────
    # Merge BFS candidates with any SerpAPI direct programs
    all_candidates = program_candidates + serpapi_direct_programs
    seen_names: set[str] = set()
    deduplicated: list[dict] = []

    for prog in all_candidates:
        norm_name = re.sub(r"\s+", " ", prog["program_name"].lower().strip())
        if norm_name and norm_name not in seen_names:
            seen_names.add(norm_name)
            deduplicated.append(prog)

    # Cap at 200
    final = deduplicated[:200]

    logger.info(
        f"[program_discovery] Final: {len(final)} unique programs "
        f"(from {len(all_candidates)} candidates)"
    )

    return final
