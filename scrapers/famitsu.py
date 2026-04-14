"""Famitsu weekly Japanese hardware sales (best-effort).

Famitsu's weekly rankings live at https://www.famitsu.com/ranking/ . Their HTML
layout changes frequently and they sometimes 403 non-JP traffic. This scraper
treats the source as optional — it probes the ranking page, respects
robots.txt, and writes whatever article links + titles it can find into a
lightweight manifest for manual review. **Unit extraction is intentionally
not attempted** until we find a stable JSON source; relying on brittle HTML
parsing here creates more work than it saves.

Output: data/raw/famitsu/YYYY-MM-DD.json
"""

from __future__ import annotations

import logging
import sys

from bs4 import BeautifulSoup

from scrapers.base import (
    ScrapeError,
    configure_logging,
    fetch,
    now_iso,
    robots_allows,
    write_raw,
)

log = logging.getLogger(__name__)

RANKING_INDEX = "https://www.famitsu.com/ranking/"


def main() -> int:
    configure_logging()
    if not robots_allows(RANKING_INDEX):
        log.warning("famitsu: robots.txt disallows ranking page — skipping")
        write_raw(
            "famitsu",
            {
                "source_key": "famitsu_ranking",
                "source_url": RANKING_INDEX,
                "fetched_at": now_iso(),
                "status": "skipped_robots",
                "articles": [],
            },
        )
        return 0

    try:
        resp = fetch(RANKING_INDEX, headers={"Accept": "text/html"}, max_retries=2)
    except ScrapeError as e:
        log.warning("famitsu: fetch failed: %s", e)
        write_raw(
            "famitsu",
            {
                "source_key": "famitsu_ranking",
                "source_url": RANKING_INDEX,
                "fetched_at": now_iso(),
                "status": "fetch_failed",
                "error": str(e),
                "articles": [],
            },
        )
        return 0

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(" ", strip=True)
        if not title:
            continue
        if "hardware" in href.lower() or "ハード" in title:
            articles.append(
                {
                    "title": title,
                    "url": href if href.startswith("http") else f"https://www.famitsu.com{href}",
                }
            )

    write_raw(
        "famitsu",
        {
            "source_key": "famitsu_ranking",
            "source_url": RANKING_INDEX,
            "fetched_at": now_iso(),
            "status": "ok",
            "articles": articles[:20],
            "note": (
                "Hardware-related article links captured for manual review. "
                "Unit extraction is not attempted due to frequent HTML drift."
            ),
        },
    )
    log.info("famitsu: captured %d article links", len(articles))
    return 0


if __name__ == "__main__":
    sys.exit(main())
