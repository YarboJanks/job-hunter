# Job Hunter

A personal job-search aggregator that pulls postings from **compliant public
APIs only** (no Terms-of-Service-violating scraping), scores them against
your own resume profile, and outputs a ranked shortlist of the roles worth
your time.

Originally built to match Joseph Ink's resume (Senior M365
Messaging/Collaboration Engineer, TS/SCI + Yankee White clearance) against
private-sector IT roles in the Dallas-Fort Worth metro, with an Oil & Gas
industry bonus and direct coverage for a curated list of target employers.
The scoring engine is fully tunable for a different resume/target
role/location - see [Tuning](#tuning) below.

## How it works

1. **Fetch** - pulls postings from several sources in parallel (see table
   below), including direct per-employer searches and direct company career
   feeds.
2. **Dedupe** - merges results across sources, dropping duplicate
   title+company pairs.
3. **Score** - each posting is scored against your resume profile:
   - Hard-excluded if it matches an exclude keyword/title (e.g. unrelated
     fields, unwanted role types)
   - A `skill_score` is computed from keyword/certification/title-pattern
     overlap
   - Postings must clear `MIN_SKILL_SCORE` on skill relevance alone -
     location/industry/employer bonuses are only added *after* that gate,
     so a job can never qualify purely by being in the right city
4. **Output** - ranked CSV in `runs/`, plus a console top-15 preview.

## Sources (all compliant, no ToS-violating scraping)

| Source | What it covers | Setup required |
|---|---|---|
| Adzuna | Aggregated private-sector employer postings (primary source), plus per-employer direct search for your target companies | Free API key (instant signup) |
| Jooble | Second broad aggregator, similar coverage to Adzuna | Free API key |
| Remotive | General remote tech jobs | None |
| RemoteOK | General remote sysadmin/IT jobs | None |
| Workday (direct) | Per-company direct career-site feeds, for companies confirmed to run on Workday | None (needs the company's real tenant/instance/site slugs, see below) |
| USAJobs | Federal/cleared roles (off by default) | Free API key |

> **Why not LinkedIn/Indeed/ClearanceJobs?** Their `robots.txt` and Terms of
> Service explicitly disallow automated scraping of job listings, and none
> offer a self-serve public API for this use case. Set up their official
> job-alert emails instead as a manual supplement - see below.

## Setup

```bash
git clone <this-repo>
cd job-hunter
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Get a free Adzuna key (primary source):
- https://developer.adzuna.com/signup - instant `app_id` + `app_key`

Optionally get a free Jooble key (second aggregator):
- https://jooble.org/api/about

Add both to `.env`, then run:

```bash
python main.py
```

## Output

- Console: top 15 ranked matches
- CSV: `runs/matches_<timestamp>.csv` - every match, ranked by score

## Tuning

**`job_hunter/profile.py`** - your resume profile and scoring rules:
- `CANDIDATE` - name/location/clearance metadata
- `SKILL_WEIGHTS` - core keyword weights (your primary skills, weighted higher)
- `CERTIFICATIONS` / `TARGET_TITLE_PATTERNS` - extra relevance signals
- `EXCLUDE_KEYWORDS` / `EXCLUDE_TITLE_KEYWORDS` - hard excludes (unrelated
  fields, unwanted role types like "Help Desk" or "Consulting")
- `MIN_SKILL_SCORE` - the relevance bar a job must clear on skill match
  alone, before any location/industry/employer bonus is applied
- `DALLAS_METRO_LOCATIONS` / `OIL_GAS_KEYWORDS` / `TARGET_EMPLOYERS` /
  `ADZUNA_SEARCH_EMPLOYERS` - location, industry, and target-employer bonus
  lists (rename/replace for your own target metro and companies)

**`job_hunter/config.py`** - search parameters (no need to touch fetch/score
logic to change these):
- `adzuna_what` / `adzuna_where` / `adzuna_distance` - Adzuna search terms & radius
- `include_remote` - also run every term as a nationwide "remote" search
- `jooble_keywords` / `jooble_location` / `jooble_radius` - same, for Jooble
- `remotive_search` / `remoteok_tag` - Remotive/RemoteOK search terms
- `target_employers` - list of employer names for direct Adzuna searches
- `workday_companies` - direct Workday career-feed entries (see below)
- `include_usajobs` - set `True` (+ add `USAJOBS_API_KEY`/`USAJOBS_EMAIL` to
  `.env`) to re-enable federal/cleared postings

### Adding a Workday direct-company feed

Many companies run their careers site on Workday, which exposes a public
JSON job-search API (no key needed) at:
`https://<tenant>.<instance>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs`

To add one:
1. Find the company's real Workday careers URL (their careers page usually
   redirects there, or check the URL bar when browsing their job listings).
2. Pull out `tenant`, `instance` (e.g. `wd1`, `wd5`), and `site` from that URL.
3. Add an entry to `workday_companies` in `job_hunter/config.py`.

Not every company is on Workday, and tenant/site names aren't guessable from
the company name alone - this only works for companies you've confirmed.

## Manual supplement (recommended)

Since LinkedIn, Indeed, and ClearanceJobs can't be scraped, set up **saved
search job alerts** on those sites directly for your target roles and
companies - many post there before (or in addition to) general job boards.
