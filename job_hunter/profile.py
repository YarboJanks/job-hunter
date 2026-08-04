"""
job_hunter/profile.py

Loads the ACTIVE candidate profile and exposes the scoring logic used to
rank job postings. The profile itself is dynamic: it's loaded from
data/profile.json, which is generated/replaced by running

    python update_resume.py path/to/resume.pdf

Every time you run that with a new resume, the old profile is fully wiped
and replaced - there's no manual editing of keyword lists required. If no
resume has ever been parsed, a small generic sample profile is used instead
so the tool still runs out of the box (with SAMPLE_PROFILE_ACTIVE = True).
"""

from job_hunter.resume_intake import load_profile

# Minimal placeholder used only until a real resume has been parsed. Kept
# intentionally generic/small - it exists so imports don't fail before the
# user's first `update_resume.py` run, not as a real profile.
_SAMPLE_PROFILE = {
    "candidate": {
        "name": "Sample Candidate",
        "location": "",
        "target_location": "Remote",
        "current_employer": "",
        "clearance": [],
    },
    "skill_weights": {
        "python": 4,
        "sql": 3,
        "project management": 3,
    },
    "certifications": [],
    "target_title_patterns": [],
    "exclude_keywords": [],
    "exclude_title_keywords": [],
    "target_employers": [],
    "metro_locations": ["remote"],
    "industry_keywords": {},
    "min_skill_score": 5,
}

_profile = load_profile()
SAMPLE_PROFILE_ACTIVE = _profile is None
if _profile is None:
    _profile = _SAMPLE_PROFILE

CANDIDATE = _profile.get("candidate", {})
SKILL_WEIGHTS = _profile.get("skill_weights", {})
CERTIFICATIONS = _profile.get("certifications", [])
TARGET_TITLE_PATTERNS = _profile.get("target_title_patterns", [])
EXCLUDE_KEYWORDS = _profile.get("exclude_keywords", [])
EXCLUDE_TITLE_KEYWORDS = _profile.get("exclude_title_keywords", [])
TARGET_EMPLOYERS = _profile.get("target_employers", [])
METRO_LOCATIONS = _profile.get("metro_locations", ["remote"])
INDUSTRY_KEYWORDS = _profile.get("industry_keywords", {})
MIN_SKILL_SCORE = _profile.get("min_skill_score", 5)

# Subset used for direct per-employer Adzuna/Jooble searches. Excludes the
# candidate's current employer (if known) since external searching there
# isn't useful and floods results with internal-mobility noise.
_current_employer = (CANDIDATE.get("current_employer") or "").lower()
ADZUNA_SEARCH_EMPLOYERS = [
    e for e in TARGET_EMPLOYERS if e.lower() != _current_employer
]


def company_matches(company: str, target_employer: str) -> bool:
    """
    Check if a job's company name actually IS the target employer, not just
    a job that happens to mention the employer's name (e.g. a required-skill
    keyword in an unrelated job's description).
    """
    return target_employer in (company or "").lower()


def is_target_metro(location: str) -> bool:
    """Return True if a location string matches the candidate's target metro
    area(s) (or is remote, which is always viable)."""
    loc = (location or "").lower()
    return any(area in loc for area in METRO_LOCATIONS)


def score_job(title: str, description: str, company: str = "", location: str = "") -> int:
    """
    Score a job posting's relevance based on keyword overlap with the
    active candidate profile, plus target-metro location fit, industry
    bonus, and target-employer bonus. Higher score = better match.

    Returns -1 if the job should be hard-excluded, or 0 if it doesn't meet
    the minimum skill-relevance bar (location/industry/employer bonuses
    alone are never enough to qualify a job).
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
        if pattern in title_lower:
            skill_score += 6  # Strong bonus for title match

    if skill_score < MIN_SKILL_SCORE:
        return 0  # Not enough real skill overlap - reject regardless of bonuses

    score = skill_score

    # Industry vertical bonus (mentioned in posting text)
    for keyword, weight in INDUSTRY_KEYWORDS.items():
        if keyword in text:
            score += weight

    # Target-employer bonus (matched by company name)
    for employer in TARGET_EMPLOYERS:
        if employer in company_lower:
            score += 8
            break

    # Target-metro location bonus (or remote, always viable)
    if location and is_target_metro(location):
        score += 5

    return score
