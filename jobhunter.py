#!/usr/bin/env python3
"""
jobhunter.py
============

Retro DOS-style menu front door for Job Hunter. Run this instead of calling
main.py / update_resume.py directly - it wraps them in an old-school
numbered menu, checks for missing API keys up front (offering the signup
URL plus a way to type the value straight into the terminal), and gives
quick access to your last results and active search-criteria profile.

Usage:
    python jobhunter.py
"""

import csv
import glob
import os
import subprocess
import sys

from dotenv import load_dotenv

from job_hunter import env_setup
from job_hunter.resume_intake import load_profile, save_profile

load_dotenv()

WIDTH = 68


def _rgb_fg(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"


def _rgb_bg(r, g, b):
    return f"\033[48;2;{r};{g};{b}m"


# "Outrun" synthwave palette - deep space-purple night sky with neon accents.
BG = _rgb_bg(13, 2, 33)         # #0D0221 - near-black midnight purple
FG = _rgb_fg(255, 255, 255)    # #FFFFFF - white body text
FG_HI = _rgb_fg(45, 226, 230)  # #2DE2E6 - neon cyan (borders/headers/prompts)
FG_TITLE = _rgb_fg(246, 1, 157)   # #F6019D - hot magenta (title)
FG_ACCENT = _rgb_fg(249, 200, 14)  # #F9C80E - neon yellow (menu numbers/OK status)
FG_WARN = _rgb_fg(255, 108, 17)   # #FF6C11 - neon orange (warnings)
FG_MISSING = _rgb_fg(253, 29, 83)  # #FD1D53 - hot pink/red (missing status)
RESET = "\033[0m"


def _clear():
    print("\033[2J\033[H", end="")


def _row(text: str = "", align: str = "left") -> str:
    text = text[:WIDTH]
    if align == "center":
        return text.center(WIDTH)
    if align == "right":
        return text.rjust(WIDTH)
    return text.ljust(WIDTH)


def _line(text: str = "", color: str = FG, align: str = "left"):
    print(f"{BG}{color}{_row(text, align)}{RESET}")


def _border(left: str, mid: str, right: str):
    print(f"{BG}{FG_HI}{left}{mid * WIDTH}{right}{RESET}")


def _pause():
    input(f"\n{FG_HI}Press Enter to return to the menu...{RESET}")


def _header():
    profile = load_profile()
    _clear()
    _border("\u2554", "\u2550", "\u2557")
    _line("JOB HUNTER", FG_TITLE, "center")
    _line("Compliant Multi-Source Job Search Aggregator", FG_HI, "center")
    _border("\u2560", "\u2550", "\u2563")
    if profile:
        candidate = profile.get("candidate", {})
        _line(f"Candidate: {candidate.get('name', '(unnamed)')}", FG)
        _line(f"Target:    {candidate.get('target_location', '(not set)')}", FG)
        _line(f"Updated:   {profile.get('_generated_at', 'unknown')}", FG)
    else:
        _line("No resume parsed yet - using a generic SAMPLE profile.", FG_WARN)
        _line("Choose [2] to parse your resume and unlock real results.", FG_WARN)
    _border("\u2560", "\u2550", "\u2563")


def _menu_options():
    _line("  [1] Run Job Search", FG)
    _line("  [2] Update Resume / Refresh Search Criteria", FG)
    _line("  [3] View Last Results", FG)
    _line("  [4] Configure API Keys", FG)
    _line("  [5] View Active Profile Summary", FG)
    _line("  [6] Set Target Location (City/State)", FG)
    _line("  [0] Exit", FG_ACCENT)
    _border("\u2560", "\u2550", "\u2563")


_FOOTER_LABELS = {
    "OPENAI_API_KEY": "OpenAI",
    "ADZUNA_APP_ID": "AdzunaID",
    "ADZUNA_APP_KEY": "AdzunaKey",
    "JOOBLE_API_KEY": "Jooble",
    "USAJOBS_API_KEY": "USAJobs",
    "USAJOBS_EMAIL": "USAJobsEmail",
}


def _key_status_footer():
    parts = [
        f"{_FOOTER_LABELS.get(row['key'], row['key'])}:{'OK' if row['is_set'] else '--'}"
        for row in env_setup.status()
    ]
    line1 = "  " + "  ".join(parts[:3])
    line2 = "  " + "  ".join(parts[3:])
    _line(line1, FG_ACCENT)
    _line(line2, FG_ACCENT)
    _border("\u255a", "\u2550", "\u255d")


def render_menu():
    _header()
    _menu_options()
    _key_status_footer()


def run_job_search():
    _clear()
    print("Run Job Search\n")
    env_setup.interactive_check(vars_needed=["ADZUNA_APP_ID", "ADZUNA_APP_KEY", "JOOBLE_API_KEY"])
    print("\nRunning search (this may take a minute)...\n")
    subprocess.run([sys.executable, "main.py"])
    _pause()


def update_resume():
    _clear()
    print("Update Resume / Refresh Search Criteria\n")
    env_setup.interactive_check(vars_needed=["OPENAI_API_KEY"])
    path = input("\nPath to your resume (.pdf, .docx, or .txt): ").strip()
    if not path:
        print("No path entered - cancelled.")
        _pause()
        return
    if not os.path.exists(path):
        print(f"File not found: {path}")
        _pause()
        return
    subprocess.run([sys.executable, "update_resume.py", path])
    _pause()


def view_last_results():
    _clear()
    files = sorted(glob.glob(os.path.join("runs", "matches_*.csv")))
    if not files:
        print("No results yet - run a job search first (option 1).")
        _pause()
        return

    latest = files[-1]
    print(f"Showing: {latest}\n")
    with open(latest, newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("(empty results file)")
    for row in rows[:20]:
        print(f"[{row['score']:>3}] {row['title']} @ {row['company']} ({row['source']})")
        print(f"       {row['location']}  |  {row['url']}\n")
    print(f"{len(rows)} total matches in this run.")
    _pause()


def configure_api_keys():
    _clear()
    print("Configure API Keys\n")
    rows = env_setup.status()
    for i, row in enumerate(rows, 1):
        tag = f"{FG_ACCENT}SET{RESET}" if row["is_set"] else f"{FG_MISSING}missing{RESET}"
        print(f"  {i}. {row['label']} ({row['key']}) - {tag}")
    print("\n  0. Back to menu")

    choice = input("\nSelect a key to set/update (number), or 0 to go back: ").strip()
    if choice in ("", "0"):
        return

    try:
        var = rows[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice.")
        _pause()
        return

    env_setup.prompt_for_var(var)
    _pause()


def view_profile_summary():
    _clear()
    profile = load_profile()
    if not profile:
        print("No resume has been parsed yet - using a generic sample profile.")
        print("Choose option [2] from the menu to parse your resume.")
        _pause()
        return

    candidate = profile.get("candidate", {})
    print(f"Candidate:        {candidate.get('name', '(unnamed)')}")
    print(f"Location:         {candidate.get('location', '(not set)')}")
    print(f"Target location:  {candidate.get('target_location', '(not set)')}")
    print(f"Current employer: {candidate.get('current_employer', '(not set)')}")
    print(f"Clearance:        {', '.join(candidate.get('clearance', [])) or '(none)'}")
    print(f"Min skill score:  {profile.get('min_skill_score')}")
    print(f"Last updated:     {profile.get('_generated_at', 'unknown')}")

    skills = profile.get("skill_weights", {})
    print(f"\nSkill weights ({len(skills)} total, top 12 shown):")
    for keyword, weight in sorted(skills.items(), key=lambda kv: kv[1], reverse=True)[:12]:
        print(f"  {weight:>2}  {keyword}")

    employers = profile.get("target_employers", [])
    print(f"\nTarget employers ({len(employers)}):")
    print("  " + (", ".join(employers) if employers else "(none)"))
    _pause()


def set_target_location():
    _clear()
    print("Set Target Location (City/State)\n")
    profile = load_profile()
    if not profile:
        print("No resume has been parsed yet - using a generic sample profile.")
        print("Choose option [2] first to create a real profile, then set your target here.")
        _pause()
        return

    candidate = profile.setdefault("candidate", {})
    current = candidate.get("target_location", "(not set)")
    print(f"Current target location: {current}\n")
    new_value = input("Enter new target location (e.g. 'Dallas-Fort Worth, TX'), or press Enter to cancel: ").strip()
    if not new_value:
        print("Cancelled - no changes made.")
        _pause()
        return

    candidate["target_location"] = new_value
    save_profile(profile)
    print(f"\nTarget location updated to: {new_value}")
    print("This will be used the next time you run a job search.")
    _pause()


MENU_ACTIONS = {
    "1": run_job_search,
    "2": update_resume,
    "3": view_last_results,
    "4": configure_api_keys,
    "5": view_profile_summary,
    "6": set_target_location,
}


def main():
    while True:
        render_menu()
        choice = input(f"{FG_HI}> Select an option: {RESET}").strip()

        if choice == "0":
            _clear()
            print("Goodbye!")
            break

        action = MENU_ACTIONS.get(choice)
        if action:
            action()
        # any other input just redraws the menu


if __name__ == "__main__":
    main()
