#!/usr/bin/env python3
"""
tailor_resume.py
================

Tailor an existing resume to a specific job listing. Paste in the full text
of a job listing (from Adzuna, Jooble, LinkedIn, Indeed, a company careers
page - anywhere), and an OpenAI model rewrites your resume's summary, skill
order, and experience bullets to better match that role, without inventing
experience you don't have. Outputs both a .docx and a .pdf.

Usage:
    python tailor_resume.py path/to/resume.pdf

Setup:
    Add OPENAI_API_KEY to your .env file (get one at
    https://platform.openai.com/api-keys). Optionally set OPENAI_MODEL
    (defaults to gpt-4o-mini).
"""

import datetime
import os
import re
import sys

from dotenv import load_dotenv

from job_hunter.resume_intake import extract_text
from job_hunter.resume_tailor import tailor_resume, render_docx, render_pdf

load_dotenv()

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs", "tailored_resumes")


def _read_job_listing_from_stdin() -> str:
    print(
        "Paste the FULL text of the job listing below.\n"
        "When done, enter a blank line, then type END on its own line and press Enter.\n"
    )
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def _slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "resume"


def main():
    if len(sys.argv) != 2:
        print("Usage: python tailor_resume.py <path-to-resume.pdf|.docx|.txt>")
        sys.exit(1)

    path = sys.argv[1]

    print(f"Reading resume: {path}")
    resume_text = extract_text(path)
    if not resume_text.strip():
        print("Error: no text could be extracted from that file.")
        sys.exit(1)

    job_listing_text = _read_job_listing_from_stdin()
    if not job_listing_text.strip():
        print("Error: no job listing text was entered.")
        sys.exit(1)

    print("\nSending resume + job listing to AI for tailoring...")
    try:
        tailored = tailor_resume(resume_text, job_listing_text)
    except Exception as e:
        print(f"Error tailoring resume: {e}")
        sys.exit(1)

    company = tailored.get("target_company") or "company"
    role = tailored.get("target_role") or "role"
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{_slugify(company)}_{_slugify(role)}_{stamp}"

    docx_path = os.path.join(OUT_DIR, f"{base_name}.docx")
    pdf_path = os.path.join(OUT_DIR, f"{base_name}.pdf")

    render_docx(tailored, docx_path)
    render_pdf(tailored, pdf_path)

    print(f"\nTailored resume for: {role} @ {company}")
    print(f"  DOCX: {docx_path}")
    print(f"  PDF:  {pdf_path}")

    notes = tailored.get("candidate_notes") or []
    if notes:
        print("\nThings to consider addressing in your cover letter:")
        for n in notes:
            print(f"  - {n}")


if __name__ == "__main__":
    main()
