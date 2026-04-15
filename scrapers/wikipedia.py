"""Wikipedia REST API — per-console summary + citation-rich sales section scan.

The Wikipedia REST API serves content under CC BY-SA 4.0 and explicitly
permits automated access (with a good User-Agent). We use it for two things:

1. A short description and thumbnail URL per console (for the /console/<slug>
   page hero).
2. A pass over the article wikitext to extract any currently-cited lifetime
   sales figure and its citation URL, emitted as a `press_leak` or
   `analyst_estimate` fact if our manual files don't already have something
   more authoritative.

Docs:
- https://en.wikipedia.org/api/rest_v1/
- https://www.mediawiki.org/wiki/API:Main_page

Output shape (data/raw/wikipedia/YYYY-MM-DD.json):

    {
      "fetched_at": "...",
      "consoles": [
         {"slug": "...", "summary": "...", "thumbnail_url": "...",
          "article_url": "...", "extracted_figures": [...] }
      ]
    }
"""

from __future__ import annotations

import json
import logging
import re
import sys

from scrapers.base import ScrapeError, configure_logging, fetch, now_iso, write_raw
from scrapers.console_registry import CONSOLES

log = logging.getLogger(__name__)

SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
PARSE_URL = (
    "https://en.wikipedia.org/w/api.php?"
    "action=parse&format=json&prop=wikitext&redirects=1&page={title}"
)

# Captures "<number> million" style figures. e.g. "50 million", "75.9 million"
FIGURE_RE = re.compile(
    r"(?P<value>\d{1,3}(?:[,\.]\d{3})*(?:\.\d+)?)\s*million",
    re.IGNORECASE,
)


def _fetch_summary(title: str) -> dict | None:
    try:
        resp = fetch(SUMMARY_URL.format(title=title), headers={"Accept": "application/json"})
        data = json.loads(resp.text)
    except ScrapeError as e:
        log.warning("Wikipedia summary failed for %s: %s", title, e)
        return None
    return {
        "summary": data.get("extract", ""),
        "article_url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
        "thumbnail_url": data.get("thumbnail", {}).get("source", ""),
        "description": data.get("description", ""),
    }


def _fetch_wikitext(title: str) -> str | None:
    try:
        resp = fetch(PARSE_URL.format(title=title), headers={"Accept": "application/json"})
        data = json.loads(resp.text)
    except ScrapeError as e:
        log.warning("Wikipedia parse failed for %s: %s", title, e)
        return None
    wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
    return wikitext or None


_LIFETIME_PATTERNS = (
    # "|units_sold = 92.1 million (As of December 31, 2025)" infobox line
    r"\|\s*units[\s_]*sold\s*=\s*(?P<value>\d{1,3}(?:[,\.]\d{3})*(?:\.\d+)?)\s*million",
    # "Sold over 75 million", "shipped 150 million"
    r"(?:sold|ship(?:ped)?|sales of|total sales)[^\.\n]{0,80}?(?P<value>\d{1,3}(?:[,\.]\d{3})*(?:\.\d+)?)\s*million",
    # "As of December 31, 2025, 92.1 million"
    r"as of [A-Z][a-z]+ \d{1,2},? \d{4}[^\.\n]{0,40}?(?P<value>\d{1,3}(?:[,\.]\d{3})*(?:\.\d+)?)\s*million",
)


def _extract_lifetime_millions(wikitext: str) -> int | None:
    """Best-effort scan for a lifetime sales figure near the top of the article.

    Conservative: first match in opening section (before first ``==`` heading) wins.
    """
    head = wikitext.split("\n==", 1)[0]
    for pattern in _LIFETIME_PATTERNS:
        m = re.search(pattern, head, flags=re.IGNORECASE)
        if not m:
            continue
        raw = m.group("value").replace(",", "")
        try:
            return int(round(float(raw) * 1_000_000))
        except ValueError:
            continue
    return None


def main() -> int:
    configure_logging()
    out_consoles = []
    for console in CONSOLES:
        if not console.wikipedia_article:
            continue
        log.info("wikipedia: fetching %s", console.wikipedia_article)
        summary = _fetch_summary(console.wikipedia_article)
        if summary is None:
            continue
        wikitext = _fetch_wikitext(console.wikipedia_article)
        extracted: list[dict] = []
        if wikitext:
            value = _extract_lifetime_millions(wikitext)
            if value is not None:
                extracted.append(
                    {
                        "units_cumulative": value,
                        "note": "Parsed from Wikipedia article lede.",
                    }
                )
        out_consoles.append(
            {
                "slug": console.slug,
                "title": console.wikipedia_article,
                **summary,
                "extracted_figures": extracted,
            }
        )

    payload = {
        "source_key": "wikipedia_en",
        "source_url": "https://en.wikipedia.org/api/rest_v1/",
        "license": "CC BY-SA 4.0",
        "fetched_at": now_iso(),
        "consoles": out_consoles,
    }
    write_raw("wikipedia", payload)
    log.info("wikipedia: captured %d console summaries", len(out_consoles))
    return 0


if __name__ == "__main__":
    sys.exit(main())
