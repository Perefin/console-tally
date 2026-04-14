"""Shared HTTP client and helpers for all scrapers.

Goals:
- Identifying User-Agent so source sites can contact us if they object.
- Bounded retries with exponential backoff on 5xx / network errors.
- Respect robots.txt where applicable (HTML scrapers).
- Never swallow errors silently; callers decide whether to re-raise or degrade.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.robotparser
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from scrapers.paths import RAW_DIR, ensure_dirs

USER_AGENT = (
    "console-tally/0.1 (+https://github.com/Perefin/console-tally) "
    "contact: https://github.com/Perefin/console-tally/issues"
)

DEFAULT_TIMEOUT = 30
log = logging.getLogger("console-tally")


class ScrapeError(RuntimeError):
    """Recoverable scraper failure — caller may choose to degrade instead of crash."""


@dataclass
class FetchResult:
    status: int
    content: bytes
    headers: dict[str, str]

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")


def robots_allows(url: str, user_agent: str = USER_AGENT) -> bool:
    """Return True if robots.txt allows this UA to fetch this URL. Defaults to True on error."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception as e:
        log.warning("robots.txt check failed for %s: %s — assuming allowed", robots_url, e)
        return True


def fetch(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = 3,
    check_robots: bool = False,
    accept_statuses: tuple[int, ...] = (200,),
) -> FetchResult:
    """Fetch a URL with retries. Raises ScrapeError if all retries fail."""
    if check_robots and not robots_allows(url):
        raise ScrapeError(f"robots.txt disallows {url}")

    merged_headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
    if headers:
        merged_headers.update(headers)

    last_err: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.request(method, url, headers=merged_headers, timeout=timeout)
            if resp.status_code in accept_statuses:
                return FetchResult(resp.status_code, resp.content, dict(resp.headers))
            if 500 <= resp.status_code < 600 and attempt < max_retries:
                sleep_s = 2**attempt
                log.warning("5xx from %s; retrying in %ss (attempt %s)", url, sleep_s, attempt)
                time.sleep(sleep_s)
                continue
            raise ScrapeError(f"Unexpected status {resp.status_code} from {url}")
        except requests.RequestException as e:
            last_err = e
            if attempt < max_retries:
                sleep_s = 2**attempt
                log.warning("Network error on %s: %s; retrying in %ss", url, e, sleep_s)
                time.sleep(sleep_s)
            continue
    raise ScrapeError(f"All {max_retries} attempts failed for {url}: {last_err}")


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today_str() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def write_raw(source_key: str, payload: dict[str, Any]) -> Path:
    """Write a raw capture. Idempotent per-day: overwrites same-day file, appends to git history."""
    ensure_dirs()
    outdir = RAW_DIR / source_key
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{today_str()}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    log.info("wrote %s", path.relative_to(RAW_DIR.parent.parent))
    return path


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
