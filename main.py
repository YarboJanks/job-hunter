#!/usr/bin/env python3
"""
Job Hunter
==========

Fetches jobs from compliant public APIs (Adzuna, Jooble, Remotive, RemoteOK,
Workday direct-company feeds, optional USAJobs), scores them against your
resume profile, and outputs a ranked shortlist of applicable roles.

Usage:
    python main.py

Setup:
    1. python3 -m venv venv && source venv/bin/activate
    2. pip install -r requirements.txt
    3. cp .env.example .env   # then fill in your API keys
    4. Edit job_hunter/profile.py with your own resume keywords/weights
    5. Edit job_hunter/config.py with your own search terms/location
    6. python main.py

See README.md for details on each source and how scoring works.
"""

import csv
import datetime
import os

from dotenv import load_dotenv

from job_hunter.config import SEARCH_CONFIG
from job_hunter.paths import runs_dir
from job_hunter.profile import score_job
from job_hunter.sources import fetch_all

load_dotenv()


def dedupe(jobs):
    """Drop duplicate postings (same title+company) across sources."""
    seen = set()
    unique = []
    for job in jobs:
        key = (job["title"].strip().lower(), job["company"].strip().lower())
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


def main():
    print("=" * 60)
    print("Job Hunter")
    print("=" * 60)

    jobs = fetch_all(SEARCH_CONFIG)
    jobs = dedupe(jobs)
    print(f"\nFetched {len(jobs)} unique jobs total.\n")

    scored = []
    for job in jobs:
        s = score_job(
            job["title"], job["description"], job["company"], job["location"]
        )
        if s > 0:
            scored.append((s, job))

    scored.sort(key=lambda x: x[0], reverse=True)

    print(f"{len(scored)} jobs matched your profile (score > 0).\n")

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = runs_dir()
    out_path = os.path.join(out_dir, f"matches_{ts}.csv")

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["score", "source", "title", "company", "location", "posted", "url"])
        for score, job in scored:
            writer.writerow(
                [score, job["source"], job["title"], job["company"],
                 job["location"], job["posted"], job["url"]]
            )

    print(f"Saved ranked results to: {out_path}\n")
    print("Top 15 matches:\n")
    for score, job in scored[:15]:
        print(f"[{score:3d}] {job['title']} @ {job['company']} ({job['source']})")
        print(f"       {job['location']}  |  {job['url']}\n")


if __name__ == "__main__":
    main()
