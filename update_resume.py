#!/usr/bin/env python3
"""
update_resume.py
=================

Parse a resume (PDF, DOCX, or plain text) with an OpenAI model and replace
the active search-criteria profile used by Job Hunter. This WIPES whatever
profile was previously active - run it again any time you have an updated
resume, and every downstream search term/scoring rule updates automatically.

Usage:
    python update_resume.py path/to/resume.pdf

Setup:
    Add OPENAI_API_KEY to your .env file (get one at
    https://platform.openai.com/api-keys). Optionally set OPENAI_MODEL
    (defaults to gpt-4o-mini).
"""

import sys

from dotenv import load_dotenv

from job_hunter.resume_intake import extract_text, parse_resume_to_profile, save_profile

load_dotenv()


def main():
    if len(sys.argv) != 2:
        print("Usage: python update_resume.py <path-to-resume.pdf|.docx|.txt>")
        sys.exit(1)

    path = sys.argv[1]

    print(f"Reading resume: {path}")
    text = extract_text(path)
    if not text.strip():
        print("Error: no text could be extracted from that file.")
        sys.exit(1)

    print("Sending resume to AI for parsing (this will replace any existing profile)...")
    try:
        profile = parse_resume_to_profile(text)
    except Exception as e:
        print(f"Error parsing resume: {e}")
        sys.exit(1)

    save_profile(profile)

    candidate = profile.get("candidate", {})
    print("\nProfile updated. New active search criteria:")
    print(f"  Candidate:        {candidate.get('name', '(unnamed)')}")
    print(f"  Target location:  {candidate.get('target_location', '(not set)')}")
    top_skills = list(profile.get("skill_weights", {}))[:8]
    print(f"  Top skills:       {', '.join(top_skills) if top_skills else '(none)'}")
    employers = profile.get("target_employers", [])[:8]
    print(f"  Target employers: {', '.join(employers) if employers else '(none)'}")
    print(f"  Min skill score:  {profile.get('min_skill_score')}")
    print("\nRun `python main.py` to search with the new criteria.")


if __name__ == "__main__":
    main()
