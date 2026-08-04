"""
job_hunter/env_setup.py

Registry of every environment variable Job Hunter uses, plus interactive
helpers to detect what's missing and either capture it right at the
terminal (saved straight into .env) or point the user at .env.example to
copy/edit by hand.

Nothing here reads real API keys - it only inspects whether a value is
present and offers to write user-provided values to the local .env file.
"""

import os
import shutil

from dotenv import load_dotenv, set_key

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_HERE)
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
ENV_EXAMPLE_PATH = os.path.join(PROJECT_ROOT, ".env.example")

# Every env var Job Hunter looks for, in the order they should be presented.
ENV_VARS = [
    {
        "key": "OPENAI_API_KEY",
        "label": "OpenAI API Key",
        "required": True,
        "used_for": "Parsing your resume into search criteria (update_resume.py)",
        "signup_url": "https://platform.openai.com/api-keys",
    },
    {
        "key": "ADZUNA_APP_ID",
        "label": "Adzuna App ID",
        "required": True,
        "used_for": "Primary job source (private-sector postings)",
        "signup_url": "https://developer.adzuna.com/signup",
    },
    {
        "key": "ADZUNA_APP_KEY",
        "label": "Adzuna App Key",
        "required": True,
        "used_for": "Primary job source (private-sector postings)",
        "signup_url": "https://developer.adzuna.com/signup",
    },
    {
        "key": "JOOBLE_API_KEY",
        "label": "Jooble API Key",
        "required": False,
        "used_for": "Second job aggregator (optional but recommended)",
        "signup_url": "https://jooble.org/api/about",
    },
    {
        "key": "BRIGHTDATA_API_KEY",
        "label": "Bright Data API Key",
        "required": False,
        "used_for": "LinkedIn job listings via Bright Data's dataset API (optional, paid)",
        "signup_url": "https://brightdata.com/",
    },
    {
        "key": "USAJOBS_API_KEY",
        "label": "USAJobs API Key",
        "required": False,
        "used_for": "Federal/cleared roles (off by default)",
        "signup_url": "https://developer.usajobs.gov/APIRequest/Index",
    },
    {
        "key": "USAJOBS_EMAIL",
        "label": "USAJobs Registered Email",
        "required": False,
        "used_for": "Required alongside USAJOBS_API_KEY (off by default)",
        "signup_url": "https://developer.usajobs.gov/APIRequest/Index",
    },
]


def refresh():
    """Reload .env into the current process's environment."""
    load_dotenv(ENV_PATH, override=True)


def status():
    """Return ENV_VARS annotated with whether each is currently set."""
    refresh()
    rows = []
    for var in ENV_VARS:
        value = os.getenv(var["key"], "")
        rows.append({**var, "is_set": bool(value.strip())})
    return rows


def missing_required():
    return [r for r in status() if r["required"] and not r["is_set"]]


def ensure_env_file():
    """Create .env from .env.example if it doesn't exist yet (no real keys copied)."""
    if os.path.exists(ENV_PATH):
        return
    if os.path.exists(ENV_EXAMPLE_PATH):
        shutil.copy(ENV_EXAMPLE_PATH, ENV_PATH)
    else:
        open(ENV_PATH, "a").close()


def set_var(key: str, value: str):
    """Persist a single value to .env (creating it from the example template
    if needed) and load it into the current process immediately."""
    ensure_env_file()
    set_key(ENV_PATH, key, value)
    os.environ[key] = value


def prompt_for_var(var: dict) -> bool:
    """
    Interactively prompt for one env var: show what it's for and where to
    get it, then either save a typed-in value to .env or let the user skip
    and edit .env.example by hand later. Returns True if a value ended up set.
    """
    print(f"\n{var['label']} ({var['key']})")
    print(f"  Used for:   {var['used_for']}")
    print(f"  Get one at: {var['signup_url']}")
    print(f"  (Or skip here, copy .env.example to .env, and paste it in manually.)")
    value = input("  Enter the value now to save it to .env, or press Enter to skip: ").strip()
    if value:
        set_var(var["key"], value)
        print(f"  Saved {var['key']} to .env.")
        return True
    print("  Skipped.")
    return False


def interactive_check(vars_needed=None) -> bool:
    """
    Walk through the given var keys (or all required vars if vars_needed is
    None), prompting for any that are currently missing. Returns True if
    every requested var ended up set (either already, or just now).
    """
    rows = status()
    if vars_needed is not None:
        rows = [r for r in rows if r["key"] in vars_needed]
    else:
        rows = [r for r in rows if r["required"]]

    all_set = True
    for row in rows:
        if row["is_set"]:
            continue
        ok = prompt_for_var(row)
        all_set = all_set and ok
    return all_set
