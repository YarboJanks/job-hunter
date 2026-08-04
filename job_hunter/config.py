"""
job_hunter/config.py

All the search parameters you'd actually want to tune live here, separate
from the fetching/scoring logic in sources.py and profile.py. Edit this file
to change search terms, target location, or which companies get direct
coverage - no need to touch the connector code itself.
"""

from job_hunter.profile import ADZUNA_SEARCH_EMPLOYERS

SEARCH_CONFIG = {
    # Adzuna: primary source - aggregates real private-sector employer
    # postings (not government). Searches your target metro first.
    # NOTE: Adzuna's `what` param is a literal phrase match, not boolean
    # OR - so we pass a list of terms and query each separately.
    "adzuna_what": [
        "Microsoft 365",
        "Exchange Online",
        "Messaging Engineer",
        "Collaboration Engineer",
        "Teams Administrator",
        "Microsoft Purview",
    ],
    "adzuna_where": "Dallas, TX",
    "adzuna_distance": 50,

    # Also run every Adzuna term as a nationwide "<term> remote" search,
    # since fully-remote postings aren't reliably geo-indexed to any one
    # metro. Set to False to restrict results to the metro area only.
    "include_remote": True,

    # Remotive free-text search (remote jobs only, nationwide by nature).
    "remotive_search": "Microsoft 365",

    # RemoteOK tag filter (single tag; leave blank for a general feed).
    "remoteok_tag": "sysadmin",

    # Direct employer searches - ensures coverage for specific target
    # companies even if their postings wouldn't otherwise surface from
    # generic keyword search. Searched nationwide (not metro-only) since
    # several are strong remote-friendly fits regardless of location.
    "target_employers": ADZUNA_SEARCH_EMPLOYERS,

    # Jooble: second broad aggregator (free key, similar coverage to
    # Adzuna). Skipped automatically if JOOBLE_API_KEY isn't set in .env.
    # Get a free key at https://jooble.org/api/about
    "jooble_keywords": [
        "Microsoft 365",
        "Exchange Online",
        "Teams Administrator",
        "Messaging Engineer",
    ],
    "jooble_location": "Dallas, TX",
    "jooble_radius": 50,

    # Direct Workday career-site feeds - no API key needed, but each entry
    # requires the company's real tenant/instance/site slugs (found in
    # their Workday careers URL, e.g.
    # https://crowdstrike.wd5.myworkdayjobs.com/crowdstrikecareers ->
    # tenant="crowdstrike", instance="wd5", site="crowdstrikecareers").
    # Add more entries here as you confirm them for other companies.
    "workday_companies": [
        {
            "label": "CrowdStrike",
            "tenant": "crowdstrike",
            "instance": "wd5",
            "site": "crowdstrikecareers",
            "search_terms": [
                "systems engineer", "Microsoft 365", "Exchange",
                "Teams", "SharePoint", "compliance", "governance",
                "identity", "M365",
            ],
            "max_postings": 60,
        },
    ],

    # USAJobs (government/federal) - off by default for a private-sector
    # focus. Set to True + add USAJOBS_API_KEY/EMAIL to .env to include
    # federal/cleared postings again.
    "include_usajobs": False,
    "usajobs_keywords": "Exchange Online OR Microsoft 365 OR Messaging Engineer",
    "usajobs_location": "Dallas, Texas",
    "usajobs_radius": 60,
}
