"""Sony IR supplementary data (quarterly PDF).

Sony publishes quarterly supplementary data PDFs containing hardware unit
sales for PlayStation platforms. PDFs live under:

    https://www.sony.com/en/SonyInfo/IR/library/presen/er/archive.html

Filename pattern (as of 2025): ``{yy}q{q}_supplement.pdf``. We fetch the
archive page, find the latest supplementary PDF link, download it, and use
pdfplumber to extract the PlayStation hardware row.

Like the Nintendo scraper, this is intentionally tolerant: if the PDF layout
drifts, we log a warning, emit zero facts, and return 0.

Output: data/raw/sony_ir/YYYY-MM-DD.json
"""

from __future__ import annotations

import io
import logging
import re
import sys

from bs4 import BeautifulSoup

from scrapers.base import ScrapeError, configure_logging, fetch, now_iso, write_raw

log = logging.getLogger(__name__)

ARCHIVE_URL = "https://www.sony.com/en/SonyInfo/IR/library/presen/er/archive.html"


def _find_latest_supplement_url(html: str) -> str | None:
    """Pick the most recent supplementary-data PDF link from the archive page."""
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"q\d_supplement(?:\w+)?\.pdf$", href, re.IGNORECASE):
            label = a.get_text(" ", strip=True)
            candidates.append((label, href))
    if not candidates:
        return None

    def _sort_key(item: tuple[str, str]) -> tuple[int, int]:
        m = re.search(r"(\d{2})q(\d)_supplement", item[1], re.IGNORECASE)
        if not m:
            return (0, 0)
        return (int(m.group(1)), int(m.group(2)))

    candidates.sort(key=_sort_key, reverse=True)
    url = candidates[0][1]
    if url.startswith("/"):
        url = "https://www.sony.com" + url
    return url


def _extract_ps_facts_from_pdf(pdf_bytes: bytes) -> list[dict]:
    try:
        import pdfplumber  # lazy — only needed in this path
    except ImportError as e:
        log.error("pdfplumber not installed: %s", e)
        return []

    facts: list[dict] = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                # Look for a PS5 lifetime line like:
                # "PS5 hardware sales (cumulative)  X.X million units"
                for pattern in (
                    r"PS5[^\n]{0,80}?(\d+\.\d+)\s*million",
                    r"PlayStation\s*5[^\n]{0,80}?(\d+\.\d+)\s*million",
                ):
                    m = re.search(pattern, text)
                    if m:
                        units = int(round(float(m.group(1)) * 1_000_000))
                        facts.append(
                            {
                                "variant": "ps5",
                                "region": "global",
                                "units_cumulative": units,
                            }
                        )
                        break
    except Exception as e:
        log.warning("pdfplumber failed to parse Sony supplement: %s", e)
        return []
    return facts


def main() -> int:
    configure_logging()
    try:
        archive = fetch(ARCHIVE_URL, headers={"Accept": "text/html"})
    except ScrapeError as e:
        log.error("Sony archive fetch failed: %s", e)
        return 0

    pdf_url = _find_latest_supplement_url(archive.text)
    if not pdf_url:
        log.warning("Sony IR: no supplement PDF link found on archive page")
        payload = {
            "source_key": "sony_ir_supplement",
            "source_url": ARCHIVE_URL,
            "fetched_at": now_iso(),
            "facts": [],
            "note": "No supplementary PDF link found.",
        }
        write_raw("sony_ir", payload)
        return 0

    try:
        pdf_resp = fetch(pdf_url, headers={"Accept": "application/pdf"})
    except ScrapeError as e:
        log.error("Sony IR PDF fetch failed: %s", e)
        return 0

    facts = _extract_ps_facts_from_pdf(pdf_resp.content)
    payload = {
        "source_key": "sony_ir_supplement",
        "source_url": pdf_url,
        "fetched_at": now_iso(),
        "facts": [
            {
                **f,
                "period_end": now_iso()[:10],  # Replace with parsed fiscal-quarter end when reliable
                "source_key": "sony_ir_supplement",
                "source_url": pdf_url,
                "fetched_at": now_iso(),
                "confidence": "official",
            }
            for f in facts
        ],
    }
    write_raw("sony_ir", payload)
    log.info("Sony IR: captured %d facts", len(facts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
