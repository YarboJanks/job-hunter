# Job Hunter

A personal job-search aggregator that pulls postings from **compliant public
APIs only** (no Terms-of-Service-violating scraping), scores them against
your own resume, and outputs a ranked shortlist of the roles worth your
time.

Search criteria are **dynamic**: upload a resume once, and an AI model
(OpenAI/ChatGPT) parses it into a structured profile — skills, target
employers, exclude lists, minimum score, target metro — that drives every
search and scoring decision. Upload a new resume any time and the old
criteria are fully wiped and replaced; no manual keyword-list editing
required.

## How it works

1. **Parse** — `python update_resume.py <resume.pdf>` extracts the resume
   text and sends it to an OpenAI model, which returns a structured profile
   (skills/weights, target employers, exclude lists, min score, metro
   locations). This is saved to `data/profile.json`, replacing whatever was
   there before.
2. **Fetch** — `python main.py` pulls postings from several sources in
   parallel (see table below), including direct per-employer searches and
   direct company career feeds — all derived from the active profile.
3. **Dedupe** — merges results across sources, dropping duplicate
   title+company pairs.
4. **Score** — each posting is scored against the active profile:
   - Hard-excluded if it matches an exclude keyword/title (e.g. unrelated
     fields, unwanted role types)
   - A `skill_score` is computed from keyword/certification/title-pattern
     overlap
   - Postings must clear `min_skill_score` on skill relevance alone —
     location/industry/employer bonuses are only added *after* that gate,
     so a job can never qualify purely by being in the right city
5. **Output** — ranked CSV in `runs/`, plus a console top-15 preview.

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
> job-alert emails instead as a manual supplement — see below.

## Setup

```bash
git clone <this-repo>
cd job-hunter
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

That's it — no need to manually create `.env` or look up API keys by hand.
Launch the menu and it'll walk you through the rest:

```bash
python jobhunter.py
```

## The menu (`jobhunter.py`)

A retro, DOS-style numbered menu is the recommended way to use Job Hunter.
Run `python jobhunter.py` and you'll get:

```
╔════════════════════════════════════════════════════════════════════╗
                             JOB HUNTER
            Compliant Multi-Source Job Search Aggregator
╠════════════════════════════════════════════════════════════════════╣
  [1] Run Job Search
  [2] Update Resume / Refresh Search Criteria
  [3] View Last Results
  [4] Configure API Keys
  [5] View Active Profile Summary
  [6] Set Target Location (City/State)
  [7] Edit Skills / Weights / Min Score / Employers
  [0] Exit
╠════════════════════════════════════════════════════════════════════╣
  OpenAI:OK  AdzunaID:OK  AdzunaKey:OK
  Jooble:OK  USAJobs:--  USAJobsEmail:--
╚════════════════════════════════════════════════════════════════════╝
```

- **[1] Run Job Search** — checks that Adzuna/Jooble keys are present
  (prompting for any missing ones first), then runs `main.py`.
- **[2] Update Resume / Refresh Search Criteria** — checks for an OpenAI
  key, asks for a path to your resume, then runs `update_resume.py`.
- **[3] View Last Results** — prints the most recent `runs/matches_*.csv`
  right in the terminal.
- **[4] Configure API Keys** — lists every key Job Hunter uses, shows
  SET/missing status, and lets you type a value in to save it.
- **[5] View Active Profile Summary** — shows the candidate info, top
  skills, and target employers currently driving your searches.
- **[6] Set Target Location (City/State)** — update the metro/target
  location your searches are anchored to (e.g. "Austin, TX") without
  re-parsing your whole resume.
- **[7] Edit Skills / Weights / Min Score / Employers** — a submenu to
  directly manage the profile's search criteria without touching a resume:
  view/add/update/remove individual skill weights, change the minimum
  skill score gate, and view/add/remove target employers.

**Missing an API key?** Whenever the menu detects one is required for the
option you picked, it shows you what the key is for and a signup URL, then
offers two ways to provide it:
1. Type the value right there — it's saved straight into `.env` for you
   (nothing is ever printed back out or logged).
2. Skip it, and instead copy `.env.example` (checked into the repo with no
   real keys) to `.env` and paste values in yourself with a text editor.

Keys you'll likely want:
- **OpenAI** (required for resume parsing): https://platform.openai.com/api-keys
- **Adzuna** (required, primary job source): https://developer.adzuna.com/signup
- **Jooble** (optional, second aggregator): https://jooble.org/api/about

## Updating your search criteria

Use menu option `[2]`, or run `update_resume.py` directly with a new/updated
resume — the old profile in `data/profile.json` is completely overwritten:

```bash
python update_resume.py path/to/new_resume.pdf   # .docx and .txt also supported
```

The command prints a summary of what changed (top skills, target
employers, target location, minimum score) so you can sanity-check the
extraction before your next search.

`data/profile.json` is gitignored — it's derived from your personal resume
and never gets committed. If you ever want to hand-tune something after
generation (add one more excluded keyword, tweak a weight, etc.), it's a
plain JSON file you can edit directly; it'll be overwritten on your next
`update_resume.py` run.

## Running things directly (without the menu)

The menu is just a friendly wrapper — every option maps to a plain script
you can still run or script yourself:

```bash
cp .env.example .env                         # then fill in your keys by hand
python update_resume.py path/to/resume.pdf
python main.py
```

## Output

- Console: top 15 ranked matches
- CSV: `runs/matches_<timestamp>.csv` — every match, ranked by score

## How the dynamic profile drives search (`job_hunter/config.py`)

`job_hunter/config.py` has no hardcoded search terms — it derives everything
from the active profile at import time:

- `adzuna_what` / `jooble_keywords` — the 6 highest-weighted, search-friendly
  skills from `skill_weights` (clearance/qualifier terms like "Top Secret"
  are automatically excluded from search phrases — they're not something you
  can search a job board for, but they still count normally toward scoring)
- `adzuna_where` / `jooble_location` — the candidate's `target_location`
- `target_employers` — the profile's `target_employers`, minus the
  candidate's own `current_employer` (avoids pointless self-searches)
- `include_remote` — always on; also runs every term as a nationwide
  "remote" search, since fully-remote postings aren't reliably geo-tagged
  to one metro
- `workday_companies` — empty by default; these require real tenant/site
  slugs that can't be inferred from a resume (see below to add one)
- `include_usajobs` — off by default; federal/cleared roles

If you want to override any of these without touching code, edit
`data/profile.json` directly (see above) — `config.py` will pick up the
change automatically.

### Adding a Workday direct-company feed

Many companies run their careers site on Workday, which exposes a public
JSON job-search API (no key needed) at:
`https://<tenant>.<instance>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs`

To add one:
1. Find the company's real Workday careers URL (their careers page usually
   redirects there, or check the URL bar when browsing their job listings).
2. Pull out `tenant`, `instance` (e.g. `wd1`, `wd5`), and `site` from that URL.
3. Add an entry to `workday_companies` in `job_hunter/config.py`, e.g.:

```python
SEARCH_CONFIG["workday_companies"].append({
    "label": "CrowdStrike",
    "tenant": "crowdstrike",
    "instance": "wd5",
    "site": "crowdstrikecareers",
    "search_terms": ["systems engineer", "Microsoft 365", "compliance"],
    "max_postings": 60,
})
```

Not every company is on Workday, and tenant/site names aren't guessable from
the company name alone — this only works for companies you've confirmed.

## Manual supplement (recommended)

Since LinkedIn, Indeed, and ClearanceJobs can't be scraped, set up **saved
search job alerts** on those sites directly for your target roles and
companies — many post there before (or in addition to) general job boards.
