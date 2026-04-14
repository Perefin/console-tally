"""Shared paths for scrapers and normalizer."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
MANUAL_DIR = DATA_DIR / "manual"
NORMALIZED_DIR = DATA_DIR / "normalized"
SQLITE_PATH = DATA_DIR / "consoles.sqlite"
SITE_PUBLIC_DATA = REPO_ROOT / "site" / "public" / "data"


def ensure_dirs() -> None:
    for p in (RAW_DIR, MANUAL_DIR, NORMALIZED_DIR, SITE_PUBLIC_DATA):
        p.mkdir(parents=True, exist_ok=True)
