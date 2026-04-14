"""Merge data/raw/ + data/manual/ into the canonical dataset consumed by the site.

Output artifacts (all written to data/normalized/ and mirrored into
site/public/data/ so Astro serves them from the built site):

- consoles.json  — per-console metadata + every fact
- regions.json   — per-region leaderboard (best fact per console in each region)
- meta.json      — source inventory, last-seen timestamps, schema_version
- consoles.sqlite (written to data/consoles.sqlite + mirrored)

Precedence (when multiple facts share variant+region+period_end):
  confidence tier: official > press_leak > analyst_estimate > derived
  then most recent fetched_at wins.

Leaderboard selection (per console, per region):
  most recent period_end; ties broken by confidence tier; then fetched_at.
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from scrapers.base import configure_logging, now_iso
from scrapers.console_registry import (
    CONSOLES,
    CONSOLES_BY_SLUG,
    REGIONS,
    VALID_CONFIDENCE,
    VALID_REGIONS,
    VARIANT_TO_CONSOLE,
)
from scrapers.paths import (
    MANUAL_DIR,
    NORMALIZED_DIR,
    RAW_DIR,
    SITE_PUBLIC_DATA,
    SQLITE_PATH,
    ensure_dirs,
)

log = logging.getLogger(__name__)

CONFIDENCE_RANK = {
    "official": 4,
    "press_leak": 3,
    "analyst_estimate": 2,
    "derived": 1,
}

SCHEMA_VERSION = "1"


# ---------------- Fact loading ----------------


def _iter_manual_facts() -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    if not MANUAL_DIR.exists():
        return facts
    for path in sorted(MANUAL_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        for f in data.get("facts", []):
            facts.append({**f, "_origin_file": path.name})
    return facts


def _iter_raw_facts() -> list[dict[str, Any]]:
    """Use only the latest snapshot per source. Raw directories contain YYYY-MM-DD.json files."""
    facts: list[dict[str, Any]] = []
    if not RAW_DIR.exists():
        return facts
    for source_dir in sorted(RAW_DIR.iterdir()):
        if not source_dir.is_dir():
            continue
        snapshots = sorted(source_dir.glob("*.json"))
        if not snapshots:
            continue
        latest = snapshots[-1]
        try:
            data = json.loads(latest.read_text())
        except json.JSONDecodeError as e:
            log.warning("skipping malformed %s: %s", latest, e)
            continue
        for f in data.get("facts", []):
            facts.append({**f, "_origin_file": f"{source_dir.name}/{latest.name}"})
    return facts


def _validate_fact(fact: dict[str, Any]) -> bool:
    if fact.get("variant") not in VARIANT_TO_CONSOLE and fact.get("variant") not in CONSOLES_BY_SLUG:
        log.warning("dropping fact with unknown variant %r (%s)", fact.get("variant"), fact.get("_origin_file"))
        return False
    if fact.get("region") not in VALID_REGIONS:
        log.warning("dropping fact with unknown region %r (%s)", fact.get("region"), fact.get("_origin_file"))
        return False
    if fact.get("confidence") not in VALID_CONFIDENCE:
        log.warning("dropping fact with unknown confidence %r (%s)", fact.get("confidence"), fact.get("_origin_file"))
        return False
    if fact.get("units_cumulative") is None and fact.get("units_period") is None:
        log.warning("dropping fact with no units (%s)", fact.get("_origin_file"))
        return False
    if not fact.get("period_end"):
        log.warning("dropping fact with no period_end (%s)", fact.get("_origin_file"))
        return False
    return True


def _dedup_key(fact: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        fact["variant"],
        fact["region"],
        fact.get("source_key", ""),
        fact["period_end"],
    )


def _fact_precedence(fact: dict[str, Any]) -> tuple[int, str]:
    return (CONFIDENCE_RANK.get(fact["confidence"], 0), fact.get("fetched_at", ""))


def _strip_internal(fact: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in fact.items() if not k.startswith("_")}


# ---------------- Builders ----------------


def build_consoles_payload() -> dict[str, Any]:
    all_facts = _iter_raw_facts() + _iter_manual_facts()
    valid = [f for f in all_facts if _validate_fact(f)]

    # Dedup: keep the most-precedent fact per (variant, region, source_key, period_end).
    by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for fact in valid:
        k = _dedup_key(fact)
        existing = by_key.get(k)
        if existing is None or _fact_precedence(fact) > _fact_precedence(existing):
            by_key[k] = fact

    # Group by parent console slug.
    facts_by_console: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in by_key.values():
        variant = fact["variant"]
        parent = variant if variant in CONSOLES_BY_SLUG else VARIANT_TO_CONSOLE[variant]
        facts_by_console[parent].append(_strip_internal(fact))

    # Sort facts within each console: period_end desc, confidence desc.
    for slug in facts_by_console:
        facts_by_console[slug].sort(
            key=lambda f: (f["period_end"], CONFIDENCE_RANK.get(f["confidence"], 0)),
            reverse=True,
        )

    consoles_out = []
    for console in CONSOLES:
        consoles_out.append(
            {
                "slug": console.slug,
                "display_name": console.display_name,
                "manufacturer": console.manufacturer,
                "generation": console.generation,
                "form_factor": console.form_factor,
                "launch_date": console.launch_date,
                "variants": list(console.variants),
                "notes": console.notes,
                "wikipedia_article": console.wikipedia_article,
                "facts": facts_by_console.get(console.slug, []),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "consoles": consoles_out,
    }


def build_regions_payload(consoles_payload: dict[str, Any]) -> dict[str, Any]:
    regions_out = []
    for region in REGIONS:
        leaderboard = []
        for console in consoles_payload["consoles"]:
            best: dict[str, Any] | None = None
            # Sum across all variants of this console for the chosen region,
            # picking the newest (period_end, confidence) fact per variant.
            per_variant_best: dict[str, dict[str, Any]] = {}
            for fact in console["facts"]:
                if fact["region"] != region.slug:
                    continue
                if fact.get("units_cumulative") is None:
                    continue
                key = fact["variant"]
                prev = per_variant_best.get(key)
                if (
                    prev is None
                    or fact["period_end"] > prev["period_end"]
                    or (
                        fact["period_end"] == prev["period_end"]
                        and CONFIDENCE_RANK.get(fact["confidence"], 0)
                        > CONFIDENCE_RANK.get(prev["confidence"], 0)
                    )
                ):
                    per_variant_best[key] = fact
            if not per_variant_best:
                continue
            total = sum(f["units_cumulative"] for f in per_variant_best.values())
            # Pick the representative source = the most authoritative fact used.
            rep = max(per_variant_best.values(), key=_fact_precedence)
            best = {
                "console_slug": console["slug"],
                "display_name": console["display_name"],
                "manufacturer": console["manufacturer"],
                "units_cumulative": total,
                "period_end": rep["period_end"],
                "source_key": rep["source_key"],
                "source_url": rep["source_url"],
                "confidence": rep["confidence"],
            }
            leaderboard.append(best)
        leaderboard.sort(key=lambda x: x["units_cumulative"], reverse=True)
        regions_out.append(
            {
                "slug": region.slug,
                "display_name": region.display_name,
                "description": region.description,
                "leaderboard": leaderboard,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "regions": regions_out,
    }


def build_meta_payload(consoles_payload: dict[str, Any]) -> dict[str, Any]:
    # Find the latest fetched_at per source_key.
    latest_per_source: dict[str, str] = {}
    total_facts = 0
    for console in consoles_payload["consoles"]:
        for fact in console["facts"]:
            total_facts += 1
            sk = fact["source_key"]
            prev = latest_per_source.get(sk, "")
            if fact["fetched_at"] > prev:
                latest_per_source[sk] = fact["fetched_at"]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "total_consoles": len(consoles_payload["consoles"]),
        "total_facts": total_facts,
        "sources": [
            {"source_key": k, "last_fetched_at": v}
            for k, v in sorted(latest_per_source.items())
        ],
    }


def write_sqlite(consoles_payload: dict[str, Any], path: Path) -> None:
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE consoles (
                slug TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                manufacturer TEXT NOT NULL,
                generation TEXT NOT NULL,
                form_factor TEXT NOT NULL,
                launch_date TEXT NOT NULL,
                notes TEXT
            );
            CREATE TABLE facts (
                console_slug TEXT NOT NULL REFERENCES consoles(slug),
                variant TEXT NOT NULL,
                region TEXT NOT NULL,
                units_cumulative INTEGER,
                units_period INTEGER,
                period_start TEXT,
                period_end TEXT NOT NULL,
                source_key TEXT NOT NULL,
                source_url TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                confidence TEXT NOT NULL,
                note TEXT
            );
            CREATE INDEX idx_facts_console ON facts(console_slug);
            CREATE INDEX idx_facts_region ON facts(region);
            CREATE INDEX idx_facts_period ON facts(period_end);
            """
        )
        for console in consoles_payload["consoles"]:
            cur.execute(
                "INSERT INTO consoles VALUES (?,?,?,?,?,?,?)",
                (
                    console["slug"],
                    console["display_name"],
                    console["manufacturer"],
                    console["generation"],
                    console["form_factor"],
                    console["launch_date"],
                    console.get("notes", ""),
                ),
            )
            for fact in console["facts"]:
                cur.execute(
                    "INSERT INTO facts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        console["slug"],
                        fact["variant"],
                        fact["region"],
                        fact.get("units_cumulative"),
                        fact.get("units_period"),
                        fact.get("period_start"),
                        fact["period_end"],
                        fact["source_key"],
                        fact["source_url"],
                        fact["fetched_at"],
                        fact["confidence"],
                        fact.get("note", ""),
                    ),
                )
        conn.commit()
    finally:
        conn.close()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n")


def mirror_to_site(files: list[Path]) -> None:
    SITE_PUBLIC_DATA.mkdir(parents=True, exist_ok=True)
    for src in files:
        shutil.copy2(src, SITE_PUBLIC_DATA / src.name)


def main() -> int:
    configure_logging()
    ensure_dirs()

    consoles_payload = build_consoles_payload()
    regions_payload = build_regions_payload(consoles_payload)
    meta_payload = build_meta_payload(consoles_payload)

    consoles_path = NORMALIZED_DIR / "consoles.json"
    regions_path = NORMALIZED_DIR / "regions.json"
    meta_path = NORMALIZED_DIR / "meta.json"
    _write_json(consoles_path, consoles_payload)
    _write_json(regions_path, regions_payload)
    _write_json(meta_path, meta_payload)

    write_sqlite(consoles_payload, SQLITE_PATH)

    mirror_to_site([consoles_path, regions_path, meta_path, SQLITE_PATH])

    log.info(
        "normalize: %d consoles, %d facts, %d sources; wrote JSON + SQLite and mirrored to site/",
        meta_payload["total_consoles"],
        meta_payload["total_facts"],
        len(meta_payload["sources"]),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
