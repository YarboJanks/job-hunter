"""
job_hunter/paths.py

Central place to resolve where Job Hunter reads/writes its data (the
active profile) and output (search results, tailored resumes).

When running from source, this is the repo root (parent of job_hunter/).
When running as a PyInstaller-frozen executable, `__file__`-based paths
point into a temporary extraction directory instead of the real install
location, so we anchor to the directory containing the executable itself
(`sys.executable`) so data/runs persist next to the app across launches.
"""

import os
import sys


def base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_dir() -> str:
    path = os.path.join(base_dir(), "data")
    os.makedirs(path, exist_ok=True)
    return path


def runs_dir() -> str:
    path = os.path.join(base_dir(), "runs")
    os.makedirs(path, exist_ok=True)
    return path
