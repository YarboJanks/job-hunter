"""
sources.py

Connectors for job data sources. Each function returns a list of normalized
job dicts:
    {
        "source": str,
        "title": str,
        "company": str,
        "location": str,
        "description": str,
        "url": str,
        "posted": str,
    }

All sources used here are accessed via their official public APIs, under
each provider's documented fair-use terms (attribution + reasonable request
rates). No authenticated scraping or ToS-violating access is performed.
"""

import os
import time

import requests

USER_AGENT = "job-search-personal-tool/1.0 (personal use, not redistributed)"


def fetch_adzuna(search_terms, where: str, app_id: str, app_key: str,
                  results_per_page: int = 50, max_pages: int = 2,
                  distance_miles: int = 50):
    """
    Adzuna job search API (https://developer.adzuna.com).
    Aggregates real private-sector employer postings (not government-only).
    Requires a free app_id + app_key from https://developer.adzuna.com/signup.
    Fair use: personal/low-volume querying, results not resold/redistributed.

    search_terms: a single phrase, or a list of phrases. Adzuna's `what`
    param treats input as one literal phrase (it does NOT support boolean
    OR syntax), so multi-term searches are run as separate queries and
    merged/deduped by the caller.
    """
    if not app_id or not app_key:
        print("  [Adzuna] Skipped: no API credentials configured (see README).")
        return []

    if isinstance(search_terms, str):
        search_terms = [search_terms]

    jobs = []
    for term in search_terms:
        for page in range(1, max_pages + 1):
            url = f"https://api.adzuna.com/v1/api/jobs/us/search/{page}"
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "what": term,
                "where": where,
                "distance": distance_miles,
                "results_per_page": results_per_page,
                "content-type": "application/json",
            }
            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            if not results:
                break

            for job in results:
                jobs.append(
                    {
                        "source": "Adzuna",
                        "title": job.get("title", ""),
                        "company": job.get("company", {}).get("display_name", ""),
                        "location": job.get("location", {}).get("display_name", ""),
                        "description": job.get("description", ""),
                        "url": job.get("redirect_url", ""),
                        "posted": job.get("created", ""),
                    }
                )
            time.sleep(0.5)

    return jobs


def fetch_adzuna_by_employer(employer: str, app_id: str, app_key: str,
                              results_per_page: int = 50, max_pages: int = 1,
                              nationwide: bool = True, where: str = ""):
    """
    Search Adzuna for postings AT a specific target employer (not just jobs
    that mention the employer's name as a skill/tool keyword).

    Adzuna's API has no dedicated "company=" filter, so this searches the
    employer name via `what` and then filters results to keep only jobs
    where the returned company display_name actually matches the target
    employer - discarding "mentions" noise (e.g. a SOC Analyst job that
    lists "CrowdStrike" as a required tool, at an unrelated company).
    """
    if not app_id or not app_key:
        return []

    jobs = []
    for page in range(1, max_pages + 1):
        url = f"https://api.adzuna.com/v1/api/jobs/us/search/{page}"
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "what": employer,
            "results_per_page": results_per_page,
            "content-type": "application/json",
        }
        if not nationwide and where:
            params["where"] = where

        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        if not results:
            break

        for job in results:
            company_name = job.get("company", {}).get("display_name", "")
            if employer.lower() not in company_name.lower():
                continue  # skip "mentions" noise - not actually posted by this employer

            jobs.append(
                {
                    "source": "Adzuna",
                    "title": job.get("title", ""),
                    "company": company_name,
                    "location": job.get("location", {}).get("display_name", ""),
                    "description": job.get("description", ""),
                    "url": job.get("redirect_url", ""),
                    "posted": job.get("created", ""),
                }
            )
        time.sleep(0.5)

    return jobs


def fetch_usajobs(keywords: str, api_key: str, email: str, results_per_page=50,
                   location: str = "", radius_miles: int = 50):
    """
    USAJOBS official API (https://developer.usajobs.gov).
    Requires a free API key registered to your email.
    Terms: data is for the registrant's own use only, not redistribution.

    location: e.g. "Dallas, Texas" - USAJobs also returns remote/telework
    postings regardless of location, so this narrows on-site results without
    excluding remote opportunities.
    """
    if not api_key or not email:
        print("  [USAJobs] Skipped: no API key configured (see README).")
        return []

    url = "https://data.usajobs.gov/api/search"
    headers = {
        "Host": "data.usajobs.gov",
        "User-Agent": email,
        "Authorization-Key": api_key,
    }
    params = {
        "Keyword": keywords,
        "ResultsPerPage": results_per_page,
    }
    if location:
        params["LocationName"] = location
        params["Radius"] = radius_miles

    resp = requests.get(url, headers=headers, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for item in data.get("SearchResult", {}).get("SearchResultItems", []):
        d = item.get("MatchedObjectDescriptor", {})
        jobs.append(
            {
                "source": "USAJobs",
                "title": d.get("PositionTitle", ""),
                "company": d.get("OrganizationName", ""),
                "location": ", ".join(
                    loc.get("LocationName", "")
                    for loc in d.get("PositionLocation", [])
                ) or "See listing",
                "description": d.get("UserArea", {})
                .get("Details", {})
                .get("JobSummary", ""),
                "url": d.get("PositionURI", ""),
                "posted": d.get("PublicationStartDate", ""),
            }
        )
    return jobs


def fetch_remotive(search: str):
    """
    Remotive public API (https://remotive.com/api-documentation).
    Fair use: attribute Remotive as source, avoid excessive polling
    (their docs recommend max ~4 requests/day).
    """
    url = "https://remotive.com/api/remote-jobs"
    params = {"search": search}
    resp = requests.get(
        url, params=params, headers={"User-Agent": USER_AGENT}, timeout=20
    )
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for job in data.get("jobs", []):
        jobs.append(
            {
                "source": "Remotive",
                "title": job.get("title", ""),
                "company": job.get("company_name", ""),
                "location": job.get("candidate_required_location", "Remote"),
                "description": job.get("description", ""),
                "url": job.get("url", ""),
                "posted": job.get("publication_date", ""),
            }
        )
    return jobs


def fetch_remoteok(tag: str = ""):
    """
    RemoteOK public API (https://remoteok.com/api).
    Fair use: attribute RemoteOK as source, don't use their logo without
    permission.
    """
    url = f"https://remoteok.com/api?tags={tag}" if tag else "https://remoteok.com/api"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for job in data:
        if "id" not in job:
            continue  # first item is a legal notice, not a job
        jobs.append(
            {
                "source": "RemoteOK",
                "title": job.get("position", ""),
                "company": job.get("company", ""),
                "location": job.get("location", "Remote"),
                "description": job.get("description", ""),
                "url": job.get("url", ""),
                "posted": job.get("date", ""),
            }
        )
    return jobs


def fetch_workday_company(company_label: str, tenant: str, instance: str, site: str,
                           search_terms=None, max_postings: int = 60,
                           fetch_descriptions: bool = True):
    """
    Generic connector for a company's public Workday career site (CxS API).
    No API key required - this is Workday's public job-board search/detail
    endpoint used by the company's own careers page.

    tenant/instance/site come from the company's Workday URL, e.g. for
    https://crowdstrike.wd5.myworkdayjobs.com/crowdstrikecareers
        tenant="crowdstrike", instance="wd5", site="crowdstrikecareers"

    Workday's own `searchText` matching is unreliable for multi-term/boolean
    queries (similar to the Adzuna quirk), so this fetches a batch of recent
    postings per search term and lets our own score_job() do the real
    relevance filtering. Since the list endpoint doesn't include the full
    description, this optionally fetches the detail page for each posting
    (bounded by max_postings) so scoring has real text to work with.
    """
    base = f"https://{tenant}.{instance}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"
    terms = search_terms or [""]
    if isinstance(terms, str):
        terms = [terms]

    seen_paths = set()
    postings = []
    for term in terms:
        resp = requests.post(
            f"{base}/jobs",
            json={"limit": 20, "offset": 0, "searchText": term},
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        for jp in data.get("jobPostings", []):
            path = jp.get("externalPath", "")
            if not path or path in seen_paths:
                continue
            seen_paths.add(path)
            postings.append(jp)
            if len(postings) >= max_postings:
                break
        if len(postings) >= max_postings:
            break

    jobs = []
    for jp in postings:
        description = ""
        if fetch_descriptions:
            try:
                detail = requests.get(
                    f"{base}/job{jp['externalPath']}",
                    headers={"User-Agent": USER_AGENT},
                    timeout=20,
                )
                detail.raise_for_status()
                description = detail.json().get("jobPostingInfo", {}).get("jobDescription", "")
            except Exception:
                pass  # fall back to title-only scoring for this posting

        jobs.append(
            {
                "source": f"Workday:{company_label}",
                "title": jp.get("title", ""),
                "company": company_label,
                "location": jp.get("locationsText", ""),
                "description": description,
                "url": f"https://{tenant}.{instance}.myworkdayjobs.com/{site}{jp.get('externalPath', '')}",
                "posted": jp.get("postedOn", ""),
            }
        )
    return jobs


def fetch_jooble(keywords, api_key: str, location: str = "Dallas, TX",
                  results_per_page: int = 50, radius_miles: int = 50):
    """
    Jooble public API (https://jooble.org/api/about) - free aggregator,
    similar coverage/behavior to Adzuna. Requires a free API key from
    https://jooble.org/api/about.

    Like Adzuna, Jooble's `keywords` param does NOT support boolean "OR"
    syntax - it's treated as a literal search string, so "A OR B" can match
    unrelated postings that merely contain the literal word "OR" (e.g. state
    abbreviation "OR", or "Underwriter OR Underwriting Specialist" titles).
    Accepts a list of terms and queries each separately, merging results.
    """
    if not api_key:
        return []

    if isinstance(keywords, str):
        keywords = [keywords]

    url = f"https://jooble.org/api/{api_key}"
    seen_links = set()
    jobs = []
    for term in keywords:
        payload = {
            "keywords": term,
            "location": location,
            "radius": str(radius_miles),
        }
        resp = requests.post(url, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        for job in data.get("jobs", [])[:results_per_page]:
            link = job.get("link", "")
            if link and link in seen_links:
                continue
            seen_links.add(link)
            jobs.append(
                {
                    "source": "Jooble",
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "location": job.get("location", ""),
                    "description": job.get("snippet", ""),
                    "url": link,
                    "posted": job.get("updated", ""),
                }
            )
    return jobs


def fetch_all(config: dict):
    """Fetch from all configured sources, being polite between calls."""
    all_jobs = []

    print("Fetching Adzuna (private-sector, Dallas-Fort Worth metro)...")
    try:
        all_jobs += fetch_adzuna(
            search_terms=config["adzuna_what"],
            where=config.get("adzuna_where", "Dallas, TX"),
            app_id=os.getenv("ADZUNA_APP_ID", ""),
            app_key=os.getenv("ADZUNA_APP_KEY", ""),
            distance_miles=config.get("adzuna_distance", 50),
        )
    except Exception as e:
        print(f"  [Adzuna] Error: {e}")
    time.sleep(1)

    if config.get("include_remote", True):
        print("Fetching Adzuna (nationwide full-remote roles)...")
        try:
            remote_terms = [f"{term} remote" for term in config["adzuna_what"]]
            all_jobs += fetch_adzuna(
                search_terms=remote_terms,
                where="",  # nationwide - remote roles aren't tied to one metro
                app_id=os.getenv("ADZUNA_APP_ID", ""),
                app_key=os.getenv("ADZUNA_APP_KEY", ""),
            )
        except Exception as e:
            print(f"  [Adzuna-remote] Error: {e}")
        time.sleep(1)

    print("Fetching Remotive...")
    try:
        all_jobs += fetch_remotive(config["remotive_search"])
    except Exception as e:
        print(f"  [Remotive] Error: {e}")
    time.sleep(1)

    print("Fetching RemoteOK...")
    try:
        all_jobs += fetch_remoteok(config.get("remoteok_tag", ""))
    except Exception as e:
        print(f"  [RemoteOK] Error: {e}")
    time.sleep(1)

    target_employers = config.get("target_employers", [])
    if target_employers:
        print(f"Fetching Adzuna direct-employer searches ({len(target_employers)} companies)...")
        adzuna_app_id = os.getenv("ADZUNA_APP_ID", "")
        adzuna_app_key = os.getenv("ADZUNA_APP_KEY", "")
        for employer in target_employers:
            try:
                hits = fetch_adzuna_by_employer(
                    employer=employer,
                    app_id=adzuna_app_id,
                    app_key=adzuna_app_key,
                    nationwide=True,
                )
                if hits:
                    print(f"  [{employer}] {len(hits)} posting(s) found")
                all_jobs += hits
            except Exception as e:
                print(f"  [{employer}] Error: {e}")
            time.sleep(0.5)

    jooble_key = os.getenv("JOOBLE_API_KEY", "")
    if jooble_key:
        print("Fetching Jooble (private-sector aggregator)...")
        try:
            all_jobs += fetch_jooble(
                keywords=config.get("jooble_keywords", config["remotive_search"]),
                api_key=jooble_key,
                location=config.get("jooble_location", "Dallas, TX"),
                radius_miles=config.get("jooble_radius", 50),
            )
        except Exception as e:
            print(f"  [Jooble] Error: {e}")
        time.sleep(1)

        if config.get("include_remote", True):
            print("Fetching Jooble (nationwide full-remote roles)...")
            try:
                all_jobs += fetch_jooble(
                    keywords=config.get("jooble_keywords", config["remotive_search"]),
                    api_key=jooble_key,
                    location="Remote",
                    radius_miles=0,
                )
            except Exception as e:
                print(f"  [Jooble-remote] Error: {e}")
            time.sleep(1)
    else:
        print("Skipping Jooble (no JOOBLE_API_KEY set - get a free key at https://jooble.org/api/about).")

    workday_companies = config.get("workday_companies", [])
    if workday_companies:
        print(f"Fetching Workday direct-company feeds ({len(workday_companies)} companies)...")
        for wc in workday_companies:
            try:
                hits = fetch_workday_company(
                    company_label=wc["label"],
                    tenant=wc["tenant"],
                    instance=wc["instance"],
                    site=wc["site"],
                    search_terms=wc.get("search_terms"),
                    max_postings=wc.get("max_postings", 60),
                )
                if hits:
                    print(f"  [{wc['label']}] {len(hits)} posting(s) found")
                all_jobs += hits
            except Exception as e:
                print(f"  [{wc['label']}] Error: {e}")
            time.sleep(0.5)

    if config.get("include_usajobs", False):
        api_key = os.getenv("USAJOBS_API_KEY", "")
        email = os.getenv("USAJOBS_EMAIL", "")

        print("Fetching USAJobs (Dallas-Fort Worth metro)...")
        try:
            all_jobs += fetch_usajobs(
                keywords=config["usajobs_keywords"],
                api_key=api_key,
                email=email,
                location=config.get("usajobs_location", "Dallas, Texas"),
                radius_miles=config.get("usajobs_radius", 60),
            )
        except Exception as e:
            print(f"  [USAJobs] Error: {e}")
        time.sleep(1)
    else:
        print("Skipping USAJobs (government roles de-prioritized per current focus).")

    return all_jobs
