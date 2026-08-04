"""
job_hunter/resume_intake.py

Turns a raw resume file (PDF, DOCX, or plain text) into the structured
candidate profile that drives everything else in Job Hunter - skill
weights, exclude lists, target employers, minimum score, and metro
locations. An OpenAI model does the extraction; the result is persisted to
data/profile.json, fully replacing whatever profile was active before.

This is the dynamic search-criteria pipeline: run `update_resume.py` any
time you have a new/updated resume, and every downstream search parameter
(job_hunter/config.py) and scoring rule (job_hunter/profile.py) updates to
match it automatically - no manual editing required.
"""

import datetime
import json
import os

from openai import OpenAI

from job_hunter.paths import data_dir

DATA_DIR = data_dir()
PROFILE_PATH = os.path.join(DATA_DIR, "profile.json")

# Fields the AI response must include for the profile to be usable.
REQUIRED_FIELDS = [
    "candidate",
    "skill_weights",
    "target_employers",
    "exclude_keywords",
    "exclude_title_keywords",
    "metro_locations",
    "min_skill_score",
]

_SYSTEM_PROMPT = """\
You are a resume-parsing assistant for a personal job-search tool. Given the \
full text of someone's resume, extract a structured JSON profile that will \
be used to score job postings for relevance to THIS specific person. Adapt \
everything to the candidate's actual field/seniority - do not assume IT/tech \
unless the resume is actually IT/tech.

Return ONLY a single valid JSON object (no markdown, no commentary) matching \
exactly this schema:

{
  "candidate": {
    "name": string,
    "location": string,               // candidate's current home location, if stated
    "target_location": string,        // best-guess target job-search metro/region; "Remote" if unclear
    "current_employer": string,       // lowercase current employer name, or "" if unknown - used to avoid self-searches
    "clearance": [string]             // security clearances held, or [] if none
  },
  "skill_weights": {
    // 15-40 entries: "lowercase skill or specialization keyword": integer 1-10.
    // Weight by how central/specific/rare the skill is to this resume. Core,
    // named specializations and rare high-value qualifiers (e.g. a security
    // clearance, a rare certification, a specific product/platform they are
    // clearly an expert in) should score 7-10. Everyday/common skills should
    // score 1-3. Include multi-word phrases where natural (e.g. "exchange online").
  },
  "certifications": [string],         // lowercase certification abbreviations/names held
  "target_title_patterns": [string],  // lowercase job-title phrases that indicate a strong fit for THIS person
  "exclude_keywords": [
    // lowercase terms that, if found ANYWHERE in a job posting's text, mean
    // it is almost certainly the WRONG field entirely for this candidate.
    // Base this on what this candidate is clearly NOT (e.g. if they are a
    // software engineer, exclude unrelated fields like "registered nurse",
    // "truck driver", "hvac technician" - adapt the list to what would
    // realistically create false-positive keyword overlap for THIS resume).
  ],
  "exclude_title_keywords": [
    // lowercase terms to reject based on the job TITLE alone - role types
    // that would be a downgrade/mismatch for this candidate's seniority or
    // specialty (e.g. "help desk" or "desk support" if the candidate is a
    // senior engineer; "consult" if they want direct employment, etc.)
    // Only include this if there's a clear signal in the resume; otherwise
    // leave conservative/short.
  ],
  "target_employers": [
    // lowercase company names: (a) real employers/clients name-checked in
    // the resume, plus (b) companies whose product/tech stack or industry
    // closely matches this candidate's specialization (vendors, industry
    // peers, direct competitors of past employers, etc.) - 10-25 entries.
  ],
  "metro_locations": [
    // lowercase city/metro name variants near target_location (include
    // common abbreviations, e.g. "dfw" for Dallas-Fort Worth) plus "remote"
    // (always include "remote" since remote roles are viable regardless).
  ],
  "industry_keywords": {
    // OPTIONAL, may be {}. If the resume shows a clear industry vertical
    // advantage (e.g. healthcare, energy/oil & gas, finance, defense),
    // include a small set of "lowercase industry term": integer 1-6 bonus
    // keywords for that vertical. Leave {} if no clear vertical applies.
  },
  "min_skill_score": integer
  // Recommended minimum total skill_weights match (summed) a posting must
  // clear before it counts as a real match, BEFORE any location/employer/
  // industry bonus. Set higher (8-12) if the candidate has many highly
  // specific/rare skills; lower (4-7) if their skill set is broader/more
  // generalist, to avoid excluding legitimate matches.
}
"""


def extract_text(path: str) -> str:
    """Extract plain text from a resume file. Supports .pdf, .docx, .txt, .md."""
    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if ext == ".docx":
        import docx

        doc = docx.Document(path)
        return "\n".join(p.text for p in doc.paragraphs)

    if ext in (".txt", ".md"):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    raise ValueError(
        f"Unsupported resume file type: {ext!r}. Use .pdf, .docx, .txt, or .md."
    )


def _validate_profile(profile: dict):
    missing = [f for f in REQUIRED_FIELDS if f not in profile]
    if missing:
        raise ValueError(
            f"AI response is missing required field(s): {missing}. "
            "Try again, or check the model output for malformed JSON."
        )
    if not isinstance(profile.get("skill_weights"), dict) or not profile["skill_weights"]:
        raise ValueError("AI response did not include any skill_weights - can't score jobs without them.")


def parse_resume_to_profile(resume_text: str, model: str = None) -> dict:
    """
    Send resume text to an OpenAI model and get back a structured profile
    dict matching the schema in _SYSTEM_PROMPT. Raises if the API key is
    missing or the response doesn't match the required schema.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your .env file - "
            "get a key at https://platform.openai.com/api-keys"
        )

    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        temperature=0.2,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Resume text:\n\n{resume_text}"},
        ],
    )

    raw = response.choices[0].message.content
    try:
        profile = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI response was not valid JSON: {e}\n\nRaw response:\n{raw}")

    _validate_profile(profile)
    return profile


def save_profile(profile: dict):
    """Persist the profile to data/profile.json, replacing any prior profile."""
    os.makedirs(DATA_DIR, exist_ok=True)
    profile = dict(profile)  # don't mutate caller's dict
    profile["_generated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)


def load_profile() -> dict:
    """Load the currently active profile, or None if none has been generated yet."""
    if not os.path.exists(PROFILE_PATH):
        return None
    with open(PROFILE_PATH, "r") as f:
        return json.load(f)
