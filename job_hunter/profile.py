"""
job_hunter/profile.py

Structured profile extracted from the candidate's resume, used to score and
filter scraped job postings for relevance. Tune the keyword weights, exclude
lists, and employer lists below to fit your own resume/target roles.
"""

CANDIDATE = {
    "name": "Joseph R. Ink",
    "location": "Dumfries, VA",
    "target_location": "Dallas-Fort Worth, TX",
    "clearance": ["TS/SCI", "Yankee White"],
}

# Location strings considered a match for the Dallas metro target area.
# Used to filter/boost postings; remote roles are always included since
# they're viable regardless of metro.
DALLAS_METRO_LOCATIONS = [
    "dallas", "fort worth", "dfw", "irving", "plano", "frisco",
    "arlington, tx", "richardson, tx", "addison, tx", "las colinas",
    "grapevine", "mckinney", "denton, tx", "texas", "remote",
]

# Core keywords the candidate is strongly qualified for.
# Weighted: higher weight = stronger signal of a good match.
SKILL_WEIGHTS = {
    # Tier 1: primary specialization (highest weight)
    "exchange online": 5,
    "microsoft 365": 5,
    "m365": 5,
    "microsoft teams": 5,
    "teams voice": 4,
    "direct routing": 4,
    "microsoft purview": 4,
    "ediscovery": 4,
    "compliance center": 3,
    "data loss prevention": 3,
    "dlp": 3,
    "retention polic": 3,
    "information governance": 4,
    "messaging": 4,

    # Tier 2: strong adjacent skills
    "powershell": 4,
    "microsoft graph": 4,
    "graph api": 4,
    "sharepoint online": 3,
    "onedrive": 3,
    "cloud migration": 3,
    "unified communications": 3,
    "collaboration engineer": 5,
    "messaging engineer": 5,
    "exchange administrator": 5,

    # Tier 3: security/compliance/governance
    "nist": 2,
    "rmf": 2,
    "stig": 2,
    "information assurance": 2,
    "identity and access management": 2,
    "iam": 2,
    "azure": 2,
    "active directory": 2,

    # Clearance signal (very high weight - rare qualifier)
    "ts/sci": 8,
    "top secret": 6,
    "yankee white": 10,
    "security clearance": 5,
    "cleared": 3,
}

# Oil & Gas industry signal - Dallas-Fort Worth has a dense concentration of
# upstream/midstream/downstream energy company HQs and regional offices that
# hire enterprise M365/messaging/compliance engineers. These keywords boost
# jobs at energy-sector employers without requiring O&G domain experience.
OIL_GAS_KEYWORDS = {
    "oil and gas": 6,
    "oil & gas": 6,
    "upstream": 3,
    "midstream": 3,
    "downstream": 3,
    "energy sector": 4,
    "pipeline": 3,
    "refinery": 3,
    "exploration and production": 4,
    "e&p": 3,
    "petroleum": 3,
    "drilling": 2,
    "oilfield": 3,
    "energy company": 3,
}

# Employers with major Dallas-Fort Worth presence in energy - used as a
# company-name match bonus (helps surface relevant postings even if the
# posting text itself doesn't mention "oil and gas" explicitly).
# NOTE: intentionally using precise/full names (not bare "vistra") since
# some tokens collide with unrelated companies (e.g. "Vistra Communications
# LLC" is an unrelated defense contractor, not the energy company).
DALLAS_OIL_GAS_EMPLOYERS = [
    "energy transfer", "atmos energy", "pioneer natural resources",
    "exxonmobil", "exxon mobil", "conocophillips", "hunt oil",
    "hunt consolidated", "trinity industries", "targa resources",
    "kimberly-clark", "tenaris", "range resources", "devon energy",
    "occidental", "oxy", "phillips 66", "marathon petroleum",
    "energy transfer partners", "vistra corp", "vistra energy",
    "hf sinclair", "eog resources", "oncor", "hunt oil company",
]

# Tech/security vendors whose product stacks and roles closely match the
# candidate's M365/security/compliance/collaboration background - strong
# fit even outside the Dallas metro (some are remote-friendly).
# NOTE: "dell" alone is too generic/collision-prone - use "dell technologies".
TARGET_TECH_SECURITY_EMPLOYERS = [
    "microsoft", "palo alto networks", "crowdstrike", "proofpoint",
    "rubrik", "veeam", "okta", "dell technologies", "servicenow",
]

# Combined explicit target-employer list used for the scoring bonus below.
TARGET_EMPLOYERS = DALLAS_OIL_GAS_EMPLOYERS + TARGET_TECH_SECURITY_EMPLOYERS

# Subset used for direct per-employer Adzuna searches. Excludes "microsoft"
# because as a bare search term it's overwhelmingly diluted by unrelated
# postings that merely mention Microsoft technologies (500k+ results, real
# Microsoft-posted jobs don't surface within any reasonable page count).
# The candidate is also already employed at Microsoft per his resume, so
# external searching there isn't the priority anyway.
ADZUNA_SEARCH_EMPLOYERS = [e for e in TARGET_EMPLOYERS if e != "microsoft"]

# Certifications held (used as a bonus match signal)
CERTIFICATIONS = [
    "ms-700", "ms-721", "az-900", "ai-900", "sc-900",
    "ccna", "security+", "network+",
]

# Job title patterns considered a strong fit (used for filtering/boosting)
TARGET_TITLE_PATTERNS = [
    "messaging engineer",
    "exchange online",
    "exchange administrator",
    "m365 engineer",
    "microsoft 365 engineer",
    "collaboration engineer",
    "teams engineer",
    "teams administrator",
    "unified communications",
    "cloud collaboration",
    "compliance engineer",
    "governance engineer",
    "information assurance",
]

# Titles/keywords to exclude (avoid false positives from generic keyword
# overlap - e.g., healthcare "care teams", land surveying, unrelated dev work)
EXCLUDE_KEYWORDS = [
    "sales", "retail", "warehouse", "driver", "nurse", "teacher",
    " rn ", "rn,", "rn -", "rn(", "registered nurse", "respiratory therapist",
    "rrt", "lvn", "lpn", "cna ", "physician", "clinical", "patient care",
    "surveyor", "hvac", "android developer", "ios developer",
    "mobile developer", "construction", "proposal specialist",
    "investments operations", "investment analyst", "land surveying",
    "civil engineer", "mechanical engineer", "electrical engineer",
    "structural engineer", "land development",
]

# Title-only excludes: checked against the job TITLE only (not the full
# description), since these terms are common in legitimate posting body
# text (e.g. "familiarity with service desk escalation") but signal the
# wrong role type when they appear in the title itself.
EXCLUDE_TITLE_KEYWORDS = [
    "desktop support",
    "linux",  # candidate's expertise is Windows/M365, not Linux administration
    "consult",  # covers "Consultant" / "Consulting"
    "service desk",
    "help desk",
    "administrative assistant",
    "executive assistant",
    "office manager",
    "receptionist",
]

# Minimum skill-relevance score (BEFORE location/industry bonuses) required
# for a job to be considered a real match. Prevents jobs with zero actual
# skill overlap from qualifying purely on the Dallas-metro location bonus.
MIN_SKILL_SCORE = 7


def company_matches(company: str, target_employer: str) -> bool:
    """
    Check if a job's company name actually IS the target employer, not just
    a job that happens to mention the employer's name (e.g. "CrowdStrike"
    used as a required-skill keyword in an unrelated job's description).
    """
    return target_employer in (company or "").lower()


def is_dallas_metro(location: str) -> bool:
    """Return True if a location string matches the Dallas-Fort Worth metro
    (or is remote, which is always viable)."""
    loc = (location or "").lower()
    return any(area in loc for area in DALLAS_METRO_LOCATIONS)


def score_job(title: str, description: str, company: str = "", location: str = "") -> int:
    """
    Score a job posting's relevance based on keyword overlap with the
    candidate's resume, plus Dallas-Fort Worth location fit and Oil & Gas
    industry bonus. Higher score = better match.

    Returns -1 if the job should be hard-excluded, or 0 if it doesn't meet
    the minimum skill-relevance bar (location/industry bonuses alone are
    never enough to qualify a job).
    """
    text = f"{title} {description}".lower()
    company_lower = (company or "").lower()
    title_lower = (title or "").lower()

    for exclude in EXCLUDE_KEYWORDS:
        if exclude in text:
            return -1  # Hard exclude

    for exclude in EXCLUDE_TITLE_KEYWORDS:
        if exclude in title_lower:
            return -1  # Hard exclude (title-based)

    skill_score = 0
    for keyword, weight in SKILL_WEIGHTS.items():
        if keyword in text:
            skill_score += weight

    for cert in CERTIFICATIONS:
        if cert in text:
            skill_score += 2

    for pattern in TARGET_TITLE_PATTERNS:
        if pattern in title.lower():
            skill_score += 6  # Strong bonus for title match

    if skill_score < MIN_SKILL_SCORE:
        return 0  # Not enough real skill overlap - reject regardless of bonuses

    score = skill_score

    # Oil & Gas industry bonus (mentioned in posting text)
    for keyword, weight in OIL_GAS_KEYWORDS.items():
        if keyword in text:
            score += weight

    # Target-employer bonus (energy + tech/security vendors worth pursuing,
    # matched by company name)
    for employer in TARGET_EMPLOYERS:
        if employer in company_lower:
            score += 8
            break

    # Dallas-Fort Worth location bonus (or remote, always viable)
    if location and is_dallas_metro(location):
        score += 5

    return score
