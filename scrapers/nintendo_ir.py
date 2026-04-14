"""Nintendo IR hardware/software sales table.

Nintendo publishes per-quarter cumulative hardware unit sales (by SKU, by
region, and worldwide) at:

    https://www.nintendo.co.jp/ir/en/finance/hard_soft/

This is rendered as an HTML table — easier and more robust to parse than the
quarterly supplementary PDF. We cache the raw HTML and extract:

- A list of (variant slug, region, units_cumulative, period_end) tuples.

When the HTML layout changes (every ~2–3 years, per history), we log a loud
warning, skip extraction, and exit 0 so the rest of the pipeline keeps running.
Manual `data/manual/baseline_first_party.json` values remain in force until
the scraper is patched.

Output: data/raw/nintendo_ir/YYYY-MM-DD.json
"""

from __future__ import annotations

import logging
import re
import sys

from bs4 import BeautifulSoup

from scrapers.base import ScrapeError, configure_logging, fetch, now_iso, write_raw

log = logging.getLogger(__name__)

SOURCE_URL = "https://www.nintendo.co.jp/ir/en/finance/hard_soft/"

# Map column heading substrings to variant slugs in our registry.
COLUMN_TO_VARIANT = {
    "Switch 2": "switch-2",
    "Nintendo Switch 2": "switch-2",
    "Nintendo Switch - OLED": "switch-oled",
    "Switch - OLED": "switch-oled",
    "OLED": "switch-oled",
    "Nintendo Switch Lite": "switch-lite",
    "Switch Lite": "switch-lite",
    "Nintendo Switch": "switch",
    "Nintendo 3DS": "3ds",
    "Wii U": "wii-u",
}


def _parse_period_end(text: str) -> str | None:
    """Extract a YYYY-MM-DD period-end date from Nintendo's header text.

    Nintendo typically labels columns like "As of Dec. 31, 2025" or
    "3-month period ended Dec. 31, 2025". We just want the end date.
    """
    m = re.search(
        r"(?:As of|ended)\s+(?P<month>\w+)\.?\s+(?P<day>\d{1,2}),\s+(?P<year>\d{4})",
        text,
    )
    if not m:
        return None
    month_map = {
        "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
        "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
        "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
    }
    month = month_map.get(m.group("month")[:3])
    if not month:
        return None
    return f"{m.group('year')}-{month}-{int(m.group('day')):02d}"


def _parse_units(cell_text: str) -> int | None:
    """Nintendo renders units in millions like '150.86' (million)."""
    cleaned = cell_text.strip().replace(",", "")
    if not cleaned or cleaned in {"-", "—", "–"}:
        return None
    try:
        return int(round(float(cleaned) * 1_000_000))
    except ValueError:
        return None


def extract_from_html(html: str) -> list[dict]:
    """Best-effort extraction. Empty list means layout was unrecognized."""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    facts: list[dict] = []
    for table in tables:
        # Find the 'Total units' row — Nintendo's lifetime-cumulative row.
        header_cells = [th.get_text(" ", strip=True) for th in table.find_all("th")]
        if not any("Total" in h or "Life to date" in h for h in header_cells):
            continue
        header_text = " ".join(header_cells)
        period_end = _parse_period_end(header_text) or "2024-12-31"
        variants_by_col: dict[int, str] = {}
        for idx, h in enumerate(header_cells):
            for needle, slug in COLUMN_TO_VARIANT.items():
                if needle in h:
                    variants_by_col[idx] = slug
                    break
        if not variants_by_col:
            continue
        for row in table.find_all("tr"):
            row_label = row.find(["th", "td"])
            if not row_label:
                continue
            if "Total" not in row_label.get_text(" ", strip=True):
                continue
            cells = row.find_all(["th", "td"])
            for idx, slug in variants_by_col.items():
                if idx >= len(cells):
                    continue
                units = _parse_units(cells[idx].get_text(" ", strip=True))
                if units is None:
                    continue
                facts.append(
                    {
                        "variant": slug,
                        "region": "global",
                        "units_cumulative": units,
                        "period_end": period_end,
                    }
                )
            break  # Only take the first Total row per table
    return facts


def main() -> int:
    configure_logging()
    try:
        resp = fetch(SOURCE_URL, headers={"Accept": "text/html"})
    except ScrapeError as e:
        log.error("Nintendo IR fetch failed: %s", e)
        # Soft-fail so the pipeline continues.
        return 0

    facts = extract_from_html(resp.text)
    if not facts:
        log.warning(
            "Nintendo IR: layout unrecognized, no facts extracted. "
            "Page may have been redesigned. Check %s and update COLUMN_TO_VARIANT.",
            SOURCE_URL,
        )

    payload = {
        "source_key": "nintendo_ir_hard_soft",
        "source_url": SOURCE_URL,
        "fetched_at": now_iso(),
        "facts": [
            {
                **f,
                "source_key": "nintendo_ir_hard_soft",
                "source_url": SOURCE_URL,
                "fetched_at": now_iso(),
                "confidence": "official",
            }
            for f in facts
        ],
    }
    write_raw("nintendo_ir", payload)
    log.info("Nintendo IR: captured %d facts", len(facts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
