"""
job_hunter/config.py

Search parameters, derived dynamically from the active candidate profile
(job_hunter/profile.py -> data/profile.json). There's nothing person-
specific hardcoded here anymore - run `python update_resume.py <resume>`
to change what gets searched for; this file will pick up the new profile
automatically the next time main.py runs.

The only things you may still want to hand-edit here are workday_companies
(direct company career-feed connections - these require real tenant/site
slugs that can't be inferred from a resume) and include_usajobs (off by
default).
"""

from job_hunter.profile import ADZUNA_SEARCH_EMPLOYERS, CANDIDATE, SKILL_WEIGHTS

# Clearance/qualifier terms often carry the highest skill_weight (they're
# rare, high-value signals for scoring) but make useless job-board search
# phrases - you can't search a job board for "Yankee White". Filter these
# out of search-term selection specifically; they still count normally
# toward score_job()'s skill_score via SKILL_WEIGHTS.
_CLEARANCE_DENYLIST = {"cleared", "clearance", "security clearance", "top secret", "secret clearance"}


def _is_clearance_term(term: str) -> bool:
    t = term.lower()
    if t in _CLEARANCE_DENYLIST:
        return True
    for held in CANDIDATE.get("clearance", []):
        held_lower = held.lower()
        if held_lower and (held_lower in t or t in held_lower):
            return True
    return False


def _top_search_terms(n: int = 6):
    """Pick the N highest-weighted, search-friendly skills as free-text search terms."""
    ranked = sorted(SKILL_WEIGHTS.items(), key=lambda kv: kv[1], reverse=True)
    filtered = [keyword for keyword, _weight in ranked if not _is_clearance_term(keyword)]
    terms = [keyword.title() for keyword in filtered[:n]]
    return terms or ["software engineer"]


_search_terms = _top_search_terms()
_target_location = CANDIDATE.get("target_location") or "Remote"

SEARCH_CONFIG = {
    # Adzuna: primary source - aggregates real private-sector employer
    # postings. Searches your target metro first.
    # NOTE: Adzuna's `what` param is a literal phrase match, not boolean
    # OR - so we pass a list of terms and query each separately.
    "adzuna_what": _search_terms,
    "adzuna_where": _target_location,
    "adzuna_distance": 50,

    # Also run every Adzuna term as a nationwide "<term> remote" search,
    # since fully-remote postings aren't reliably geo-indexed to any one
    # metro. Set to False to restrict results to the metro area only.
    "include_remote": True,

    # Remotive free-text search (remote jobs only, nationwide by nature).
    "remotive_search": _search_terms[0] if _search_terms else "software engineer",

    # RemoteOK tag filter (single tag; leave blank for a general feed).
    "remoteok_tag": "",

    # Direct employer searches - ensures coverage for specific target
    # companies even if their postings wouldn't otherwise surface from
    # generic keyword search. Searched nationwide (not metro-only) since
    # several may be strong remote-friendly fits regardless of location.
    "target_employers": ADZUNA_SEARCH_EMPLOYERS,

    # Jooble: second broad aggregator (free key, similar coverage to
    # Adzuna). Skipped automatically if JOOBLE_API_KEY isn't set in .env.
    # Get a free key at https://jooble.org/api/about
    "jooble_keywords": _search_terms,
    "jooble_location": _target_location,
    "jooble_radius": 50,

    # Direct Workday career-site feeds - no API key needed, but each entry
    # requires the company's real tenant/instance/site slugs (found in
    # their Workday careers URL, e.g.
    # https://crowdstrike.wd5.myworkdayjobs.com/crowdstrikecareers ->
    # tenant="crowdstrike", instance="wd5", site="crowdstrikecareers").
    # Empty by default since these can't be inferred from a resume - add
    # entries manually for companies you've confirmed run on Workday. See
    # README.md for the "Adding a Workday direct-company feed" guide.
    "workday_companies": [],

    # USAJobs (government/federal) - off by default. Set to True + add
    # USAJOBS_API_KEY/EMAIL to .env to include federal/cleared postings.
    "include_usajobs": False,
    "usajobs_keywords": " OR ".join(_search_terms[:3]),
    "usajobs_location": _target_location,
    "usajobs_radius": 60,
}
