"""Microsoft 'More Personal Computing' / 'Gaming' segment revenue from SEC EDGAR.

SEC EDGAR exposes an officially-supported JSON API for XBRL company facts. No
scraping, no ToS concerns. We don't derive unit sales from this (Microsoft
stopped reporting Xbox units in 2015) — this feeds the /sources page with
up-to-date segment revenue context.

Docs: https://www.sec.gov/edgar/sec-api-documentation

Output shape written to data/raw/sec_edgar/YYYY-MM-DD.json:

    {
      "fetched_at": "...",
      "cik": "0000789019",
      "entity_name": "MICROSOFT CORPORATION",
      "quarterly_revenues": [
          {"period_end": "2025-03-31", "value_usd": 70066000000, "form": "10-Q"},
          ...
      ]
    }
"""

from __future__ import annotations

import logging
import sys

from scrapers.base import (
    ScrapeError,
    configure_logging,
    fetch,
    now_iso,
    write_raw,
)

log = logging.getLogger(__name__)

MICROSOFT_CIK = "0000789019"  # left-padded to 10 digits per EDGAR convention
COMPANY_FACTS_URL = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{MICROSOFT_CIK}.json"


def extract_quarterly_revenue(facts: dict) -> list[dict]:
    """Pull quarterly revenue datapoints (us-gaap:Revenues or RevenueFromContractWithCustomer).

    XBRL concept names vary by issuer/year. Microsoft reports revenue under
    `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`. We fall back
    to `us-gaap:Revenues` if the first isn't present.
    """
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    concept = (
        us_gaap.get("RevenueFromContractWithCustomerExcludingAssessedTax")
        or us_gaap.get("Revenues")
    )
    if not concept:
        raise ScrapeError("Neither RevenueFromContractWithCustomerExcludingAssessedTax nor Revenues present in company facts")

    usd = concept.get("units", {}).get("USD", [])
    quarterly = [
        {
            "period_start": item.get("start"),
            "period_end": item["end"],
            "value_usd": int(item["val"]),
            "form": item.get("form"),
            "fiscal_year": item.get("fy"),
            "fiscal_period": item.get("fp"),
        }
        for item in usd
        # Keep quarterly (10-Q) and annual (10-K) datapoints with start+end
        if item.get("start") and item.get("end") and item.get("form") in {"10-Q", "10-K", "10-Q/A", "10-K/A"}
    ]
    # Dedup on (period_start, period_end), prefer most-recently-amended form
    quarterly.sort(key=lambda q: (q["period_end"], q["period_start"], q["form"]))
    dedup: dict[tuple[str, str], dict] = {}
    for q in quarterly:
        dedup[(q["period_start"], q["period_end"])] = q
    out = sorted(dedup.values(), key=lambda q: q["period_end"])
    return out[-20:]  # last ~5 years of quarterly datapoints


def main() -> int:
    configure_logging()
    # SEC EDGAR requires a specific User-Agent format: "Name email" identifying the client.
    sec_ua = "console-tally/0.1 perefin-contact@users.noreply.github.com"
    try:
        resp = fetch(
            COMPANY_FACTS_URL,
            headers={"Accept": "application/json", "User-Agent": sec_ua},
        )
        facts = __import__("json").loads(resp.text)
    except ScrapeError as e:
        log.warning("SEC EDGAR fetch failed (soft-fail): %s", e)
        write_raw(
            "sec_edgar",
            {
                "source_key": "sec_edgar_microsoft",
                "source_url": COMPANY_FACTS_URL,
                "fetched_at": now_iso(),
                "status": "fetch_failed",
                "error": str(e),
                "quarterly_revenues": [],
            },
        )
        return 0

    try:
        quarterly = extract_quarterly_revenue(facts)
    except ScrapeError as e:
        log.warning("SEC EDGAR parse failed (soft-fail): %s", e)
        write_raw(
            "sec_edgar",
            {
                "source_key": "sec_edgar_microsoft",
                "source_url": COMPANY_FACTS_URL,
                "fetched_at": now_iso(),
                "status": "parse_failed",
                "error": str(e),
                "quarterly_revenues": [],
            },
        )
        return 0

    payload = {
        "source_key": "sec_edgar_microsoft",
        "source_url": COMPANY_FACTS_URL,
        "fetched_at": now_iso(),
        "cik": MICROSOFT_CIK,
        "entity_name": facts.get("entityName", "MICROSOFT CORPORATION"),
        "quarterly_revenues": quarterly,
        "note": (
            "Microsoft does not report Xbox unit sales. This file captures "
            "total quarterly revenue as context. Xbox-specific unit figures "
            "are analyst estimates stored in data/manual/xbox_estimates.json."
        ),
    }
    write_raw("sec_edgar", payload)
    log.info("SEC EDGAR: captured %d quarterly datapoints", len(quarterly))
    return 0


if __name__ == "__main__":
    sys.exit(main())
