# config/known_catalogs.py
# Known graduate program catalog URLs for top 100 universities
#
# These URLs point directly to comprehensive program listings,
# bypassing the need for discovery via Jina Search.
#
# Maintenance: URLs should be verified periodically as universities
# occasionally redesign their websites.

KNOWN_CATALOG_URLS = {
    # USA - Top Universities
    "mit.edu": "https://catalog.mit.edu/degree-charts/",
    "stanford.edu": "https://applygrad.stanford.edu/portal/programs",
    "harvard.edu": "https://gsas.harvard.edu/programs-study/degree-programs",
    "princeton.edu": "https://gradschool.princeton.edu/academics/fields-study",
    "yale.edu": "https://gsas.yale.edu/academics/programs-and-degrees",
    "columbia.edu": "https://gsas.columbia.edu/degree-programs",
    "upenn.edu": "https://catalog.upenn.edu/programs/",
    "cornell.edu": "https://gradschool.cornell.edu/academics/fields-of-study/",
    "brown.edu": "https://graduateschool.brown.edu/academics/programs",
    "dartmouth.edu": "https://graduate.dartmouth.edu/programs",
    "duke.edu": "https://gradschool.duke.edu/academics/programs-degrees/",
    "northwestern.edu": "https://www.tgs.northwestern.edu/admission/academic-programs/",
    "uchicago.edu": "https://grad.uchicago.edu/programs/",
    "jhu.edu": "https://e-catalogue.jhu.edu/",
    "caltech.edu": "https://www.gradoffice.caltech.edu/admissions/graduate-studies-options",
    "cmu.edu": "https://www.cmu.edu/graduate/programs/index.html",
    
    # USA - UC System
    "berkeley.edu": "https://grad.berkeley.edu/programs/list/",
    "ucla.edu": "https://grad.ucla.edu/programs/",
    "ucsd.edu": "https://catalog.ucsd.edu/graduate/degrees-offered/",
    "uci.edu": "https://grad.uci.edu/programs/",
    "ucdavis.edu": "https://grad.ucdavis.edu/programs",
    "ucsb.edu": "https://www.graddiv.ucsb.edu/programs",
    
    # USA - State Universities
    "gatech.edu": "https://catalog.gatech.edu/programs/",
    "purdue.edu": "https://www.purdue.edu/gradschool/academics/graduate-degree-programs.html",
    "illinois.edu": "https://grad.illinois.edu/admissions/departments",
    "umich.edu": "https://rackham.umich.edu/programs-of-study/",
    "osu.edu": "https://gpadmissions.osu.edu/programs/programs.aspx",
    "utexas.edu": "https://gradschool.utexas.edu/academics/programs",
    "tamu.edu": "https://grad.tamu.edu/academics/programs",
    "wisconsin.edu": "https://grad.wisc.edu/programs/",
    "washington.edu": "https://grad.uw.edu/programs/",
    "umn.edu": "https://grad.umn.edu/programs",
    "maryland.edu": "https://gradschool.umd.edu/programs",
    "ufl.edu": "https://catalog.ufl.edu/graduate/",
    "fsu.edu": "https://gradschool.fsu.edu/programs",
    "asu.edu": "https://degrees.apps.asu.edu/masters-phd/major-list/letter/all",
    "msu.edu": "https://reg.msu.edu/AcademicPrograms/",
    "rutgers.edu": "https://gradstudy.rutgers.edu/programs",
    "psu.edu": "https://bulletins.psu.edu/graduate/programs/",
    
    # USA - Other Top Universities
    "vanderbilt.edu": "https://gradschool.vanderbilt.edu/programs/",
    "rice.edu": "https://ga.rice.edu/programs-study/",
    "virginia.edu": "https://graduate.as.virginia.edu/programs",
    "unc.edu": "https://gradschool.unc.edu/programs/",
    "ncsu.edu": "https://grad.ncsu.edu/programs/",
    "usc.edu": "https://gradadm.usc.edu/programs/",
    "bu.edu": "https://www.bu.edu/academics/graduate/",
    "nyu.edu": "https://www.nyu.edu/admissions/graduate-admissions/programs.html",
    "washu.edu": "https://graduateschool.wustl.edu/programs",
    
    # UK - Top Universities
    "ox.ac.uk": "https://www.ox.ac.uk/admissions/graduate/courses",
    "cam.ac.uk": "https://www.postgraduate.study.cam.ac.uk/courses",
    "imperial.ac.uk": "https://www.imperial.ac.uk/study/courses/",
    "ucl.ac.uk": "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees",
    "kcl.ac.uk": "https://www.kcl.ac.uk/study/postgraduate-taught/courses",
    "ed.ac.uk": "https://www.ed.ac.uk/studying/postgraduate/degrees",
    "manchester.ac.uk": "https://www.manchester.ac.uk/study/masters/courses/",
    "bristol.ac.uk": "https://www.bristol.ac.uk/study/postgraduate/",
    "warwick.ac.uk": "https://warwick.ac.uk/study/postgraduate/courses/",
    "glasgow.ac.uk": "https://www.gla.ac.uk/postgraduate/taught/",
    "leeds.ac.uk": "https://courses.leeds.ac.uk/",
    "sheffield.ac.uk": "https://www.sheffield.ac.uk/postgraduate/taught/courses",
    "birmingham.ac.uk": "https://www.birmingham.ac.uk/postgraduate/courses",
    "nottingham.ac.uk": "https://www.nottingham.ac.uk/pgstudy/courses/",
    "southampton.ac.uk": "https://www.southampton.ac.uk/courses/postgraduate.page",
    "durham.ac.uk": "https://www.durham.ac.uk/study/courses/postgraduate/",
    "lse.ac.uk": "https://www.lse.ac.uk/study-at-lse/Graduate",
    "st-andrews.ac.uk": "https://www.st-andrews.ac.uk/subjects/",
    "york.ac.uk": "https://www.york.ac.uk/study/postgraduate-taught/courses/",
    "exeter.ac.uk": "https://www.exeter.ac.uk/study/postgraduate/courses/",
    
    # Canada - Top Universities
    "utoronto.ca": "https://future.utoronto.ca/academics/",
    "ubc.ca": "https://www.grad.ubc.ca/prospective-students/graduate-degree-programs",
    "mcgill.ca": "https://www.mcgill.ca/gradapplicants/programs",
    "uwaterloo.ca": "https://uwaterloo.ca/graduate-studies-postdoctoral-affairs/future-students/programs",
    "ualberta.ca": "https://www.ualberta.ca/graduate-programs/",
    "uottawa.ca": "https://www.uottawa.ca/study/graduate-studies",
    "westernu.ca": "https://grad.uwo.ca/prospective_students/programs/program_list.html",
    "queensu.ca": "https://www.queensu.ca/sgs/programs",
    "mcmaster.ca": "https://future.mcmaster.ca/programs/graduate/",
    "dal.ca": "https://www.dal.ca/faculty/gradstudies/programs.html",
    
    # Australia - Top Universities
    "unimelb.edu.au": "https://study.unimelb.edu.au/find/courses/graduate/",
    "sydney.edu.au": "https://www.sydney.edu.au/courses/courses/pc.html",
    "unsw.edu.au": "https://www.unsw.edu.au/study/postgraduate",
    "monash.edu": "https://www.monash.edu/study/courses/find-a-course",
    "anu.edu.au": "https://programsandcourses.anu.edu.au/",
    "uq.edu.au": "https://study.uq.edu.au/study-options/programs",
    "adelaide.edu.au": "https://www.adelaide.edu.au/degree-finder/",
    "uts.edu.au": "https://www.uts.edu.au/future-students/find-a-course",
    "rmit.edu.au": "https://www.rmit.edu.au/study-with-us/levels-of-study/postgraduate-study",
    "deakin.edu.au": "https://www.deakin.edu.au/course",
    
    # Singapore
    "nus.edu.sg": "https://www.nus.edu.sg/registrar/academic-information-policies/graduate-programmes",
    "ntu.edu.sg": "https://www.ntu.edu.sg/admissions/graduate",
    "smu.edu.sg": "https://admissions.smu.edu.sg/graduate-programmes",
    
    # Hong Kong
    "hkust.edu.hk": "https://prog-crs.hkust.edu.hk/pg",
    "hku.hk": "https://gradsch.hku.hk/prospective_students/programmes",
    "cuhk.edu.hk": "https://www.gs.cuhk.edu.hk/admissions/programme",
    
    # China
    "tsinghua.edu.cn": "https://www.tsinghua.edu.cn/en/Admissions/Graduate_Programs.htm",
    "pku.edu.cn": "https://english.pku.edu.cn/Admissions/Graduate_Programs.htm",
    
    # Europe - Continental
    "ethz.ch": "https://ethz.ch/en/studies/master/degree-programmes.html",
    "epfl.ch": "https://www.epfl.ch/education/master/programs/",
    "tum.de": "https://www.tum.de/en/studies/degree-programs",
    "kth.se": "https://www.kth.se/en/studies/master",
    "tudelft.nl": "https://www.tudelft.nl/en/education/programmes",
    "ku.dk": "https://studies.ku.dk/masters/",
    "helsinki.fi": "https://www.helsinki.fi/en/admissions-and-education/degree-programmes",
}


def get_known_catalog_url(domain: str) -> str:
    """
    Get the known catalog URL for a university domain.
    
    Args:
        domain: University domain (e.g., "mit.edu", "stanford.edu")
    
    Returns:
        Known catalog URL if available, None otherwise
    """
    return KNOWN_CATALOG_URLS.get(domain)


def has_known_catalog(domain: str) -> bool:
    """Check if a university has a known catalog URL."""
    return domain in KNOWN_CATALOG_URLS
