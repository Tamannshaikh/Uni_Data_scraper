"""
University-specific extraction configuration.

Each university has:
- url: The catalog/program listing page
- strategy: Which extractor to use based on page structure

Strategies:
- "anchor": Degree names are in <a> tag text
- "list_text": Degree names in <li> or similar list items
- "heading": Degree names in <h2>/<h3> tags
- "heading_with_button": Degree in heading, link in separate button
- "plain_text_list": Degree names in plain text bullets (no dedicated URL)
- "playwright_table": JavaScript-rendered table (needs Playwright)
- "playwright_anchor": JavaScript-rendered anchors (needs Playwright)
"""

UNIVERSITY_CONFIG = {
    # ========================================================================
    # WORKING - Category A: Clean anchor lists
    # ========================================================================
    "uark.edu": {
        "url": "https://catalog.uark.edu/graduatecatalog/programsofstudy/",
        "strategy": "anchor",
        "notes": "Works perfectly - degree names in anchor text"
    },
    
    # ========================================================================
    # Category B: Heading/list text (not in anchors)
    # ========================================================================
    "mit.edu": {
        "url": "https://oge.mit.edu/graduate-admissions/programs/fields-of-study/",
        "strategy": "table",
        "notes": "Degree names in table cells (first column)"
    },
    
    "purdue.edu": {
        "url": "https://www.purdue.edu/gradschool/academics/graduate-degree-programs.html",
        "strategy": "heading",
        "notes": "Degree names in <h2>, needs less strict filtering"
    },
    
    # ========================================================================
    # Category C: JavaScript-rendered or plain text
    # ========================================================================
    "ucsd.edu": {
        "url": "https://catalog.ucsd.edu/graduate/degrees-offered/index.html",
        "strategy": "plain_text_list",
        "notes": "Degrees in plain text bullets, no individual links"
    },
    
    "stanford.edu": {
        "url": "https://applygrad.stanford.edu/portal/programs",
        "strategy": "playwright_table",
        "notes": "JavaScript-rendered table, needs Playwright"
    },
    
    "manchester.ac.uk": {
        "url": "https://www.manchester.ac.uk/study/masters/courses/list/",
        "strategy": "playwright_anchor",
        "notes": "JavaScript-rendered, then extract anchors"
    },
    
    # ========================================================================
    # TODO: Top universities to configure
    # ========================================================================
    # "berkeley.edu": {...},  # Blocks requests - needs different approach
    # "harvard.edu": {...},
    # "cmu.edu": {...},
    # "caltech.edu": {...},
    # "cornell.edu": {...},
    # "columbia.edu": {...},
    # "princeton.edu": {...},
    # "yale.edu": {...},
    # "uchicago.edu": {...},
    # "northwestern.edu": {...},
    # "duke.edu": {...},
    # "jhu.edu": {...},
    # "umich.edu": {...},
    # "uiuc.edu": {...},
    # "gatech.edu": {...},
}


def get_university_config(domain: str):
    """Get configuration for a university domain."""
    return UNIVERSITY_CONFIG.get(domain)


def is_configured(domain: str) -> bool:
    """Check if university has manual configuration."""
    return domain in UNIVERSITY_CONFIG
