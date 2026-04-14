"""RSS watchers — flag press-release items that look like new sales figures.

This doesn't emit facts. It produces a lightweight 'recent mentions' file that
the site shows on /sources to surface likely sources of new estimates.
Maintainers review these and add structured facts to data/manual/*.json via PR.

Output: data/raw/rss_watchers/YYYY-MM-DD.json
"""

from __future__ import annotations

import logging
import sys

import feedparser

from scrapers.base import configure_logging, now_iso, write_raw

log = logging.getLogger(__name__)

FEEDS = [
    # (label, url) — keep this list short; each must be publicly crawlable.
    ("GamesIndustry.biz", "https://www.gamesindustry.biz/feed/news"),
    ("Nintendo Life hardware", "https://www.nintendolife.com/feeds/news"),
]

KEYWORDS = (
    "units",
    "sales",
    "lifetime",
    "million",
    "shipped",
    "sold",
    "install base",
    "estimate",
)


def _matches(text: str) -> bool:
    lower = text.lower()
    return any(k in lower for k in KEYWORDS)


def main() -> int:
    configure_logging()
    matches: list[dict] = []
    for label, url in FEEDS:
        try:
            d = feedparser.parse(url)
        except Exception as e:  # feedparser is resilient; keep a belt
            log.warning("rss_watchers: %s failed: %s", url, e)
            continue
        for entry in d.entries[:25]:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            if _matches(title) or _matches(summary):
                matches.append(
                    {
                        "feed": label,
                        "title": title,
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "summary": summary[:400],
                    }
                )

    write_raw(
        "rss_watchers",
        {
            "source_key": "rss_watchers",
            "fetched_at": now_iso(),
            "feeds": [{"label": f[0], "url": f[1]} for f in FEEDS],
            "matches": matches,
            "note": "Items flagged for manual review. No automatic fact emission.",
        },
    )
    log.info("rss_watchers: %d items flagged across %d feeds", len(matches), len(FEEDS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
