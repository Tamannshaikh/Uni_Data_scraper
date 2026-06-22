import re
from urllib.parse import urlparse

REGEX = re.compile(
    r"^(bs|ba|bfa|bme|bse|bsn|bba|bsba|bsrs|bsw|bsed|bsph|bscs|bsis|"
    r"bsa|bgs|bsce|bsee|bsme|bsie|bsit|bscpe|bscp|bste|bas|"
    r"beng|bsc|llb|barch|bbe|bmus|bm|bcom|btech|bca|bdes|"
    r"aas|aasn|ags|as|aa|minor|concentration|track|endorsement"
    r")([-_]|$|in-)",
    re.IGNORECASE
)

def drop_prefix(slug):
    for p in ("online-", "on-campus-", "campus-", "part-time-", "full-time-"):
        if slug.startswith(p):
            return slug[len(p):]
    return slug

tests = [
    ("DROP", "https://www.astate.edu/programs/bas-in-organizational-supervision.html"),
    ("DROP", "https://www.astate.edu/programs/bgs-in-general-studies.html"),
    ("DROP", "https://www.astate.edu/programs/bsa-in-agricultural-business.html"),
    ("DROP", "https://www.astate.edu/programs/bsce-in-civil-engineering.html"),
    ("DROP", "https://www.astate.edu/programs/bsee-in-electrical-engineering.html"),
    ("DROP", "https://www.astate.edu/programs/bsme-in-mechanical-engineering.html"),
    ("DROP", "https://www.astate.edu/programs/bs-in-accounting.html"),
    ("DROP", "https://www.astate.edu/programs/ba-in-chemistry.html"),
    ("DROP", "https://www.astate.edu/programs/minor-in-finance.html"),
    ("DROP", "https://www.astate.edu/programs/aas-in-law-enforcement.html"),
    ("DROP", "https://www.astate.edu/programs-aos-online/online-bsn-in-nursing-rn-to-bsn.html"),
    ("DROP", "https://www.astate.edu/programs-aos-online/online-bsa-in-agricultural-studies.html"),
    ("DROP", "https://www.astate.edu/programs-aos-online/online-bse-in-elementary-education.html"),
    ("DROP", "https://www.astate.edu/programs-aos-online/online-ags-in-general-studies.html"),
    ("KEEP", "https://www.astate.edu/programs-aos-online/online-ma-in-communication-studies.html"),
    ("KEEP", "https://www.astate.edu/programs-aos-online/online-ms-in-strategic-communication.html"),
    ("KEEP", "https://www.astate.edu/programs-aos-online/online-msn-in-nursing-psychiatric.html"),
    ("KEEP", "https://www.astate.edu/programs/ms-in-computer-science.html"),
    ("KEEP", "https://www.astate.edu/programs/ma-in-sociology.html"),
    ("KEEP", "https://www.astate.edu/programs/phd-in-heritage-studies.html"),
    ("KEEP", "https://www.astate.edu/programs/msa-in-agriculture.html"),
    ("KEEP", "https://www.manchester.ac.uk/study/masters/courses/list/09994/msc-business-psychology/"),
    ("KEEP", "https://www.manchester.ac.uk/study/postgraduate-research/programmes/list/05482/phd-mphil-astronomy/"),
]

all_ok = True
for want, url in tests:
    path = urlparse(url.lower()).path
    slug = path.rstrip("/").rsplit("/", 1)[-1]
    slug = slug.rsplit(".", 1)[0] if "." in slug else slug
    slug = drop_prefix(slug)
    dropped = bool(REGEX.match(slug))
    got = "DROP" if dropped else "KEEP"
    ok = got == want
    if not ok:
        all_ok = False
    status = "OK" if ok else "FAIL"
    print(f"[{status}] {got} (want {want}) slug={slug}")

print()
print("ALL PASS" if all_ok else "SOME TESTS FAILED")
