"""Plausibility checks. These run in CI; failures should open an issue.

The assertions are intentionally conservative. A fail here means a human should
eyeball the data before the site deploys.
"""

from __future__ import annotations

import json
from collections import defaultdict

import pytest

from scrapers.paths import NORMALIZED_DIR

# Sanity-cap per variant (in units). Anything above this is almost certainly
# bad units/scale parsing. Pick very loose upper bounds.
MAX_PLAUSIBLE_UNITS = 300_000_000  # no single console has sold more


@pytest.fixture(scope="module")
def consoles_payload():
    path = NORMALIZED_DIR / "consoles.json"
    if not path.exists():
        pytest.skip("consoles.json not yet generated — run scrapers.normalize first")
    return json.loads(path.read_text())


def test_units_are_within_plausible_bounds(consoles_payload):
    bad: list[str] = []
    for console in consoles_payload["consoles"]:
        for fact in console["facts"]:
            if fact.get("units_cumulative") and fact["units_cumulative"] > MAX_PLAUSIBLE_UNITS:
                bad.append(f"{console['slug']} {fact['variant']} {fact['period_end']}: {fact['units_cumulative']}")
    assert not bad, f"Implausibly large unit counts: {bad}"


def test_cumulative_monotonic_per_variant_region(consoles_payload):
    """Within a single (variant, region), cumulative units should be non-decreasing
    over time. A rare >5% regression across a newer period_end is suspicious."""
    series: dict[tuple[str, str], list[tuple[str, int, str]]] = defaultdict(list)
    for console in consoles_payload["consoles"]:
        for fact in console["facts"]:
            if fact.get("units_cumulative") is None:
                continue
            key = (fact["variant"], fact["region"])
            series[key].append((fact["period_end"], fact["units_cumulative"], fact["confidence"]))

    regressions: list[str] = []
    for key, entries in series.items():
        entries.sort(key=lambda e: e[0])
        prev_val: int | None = None
        for period_end, val, conf in entries:
            if prev_val is not None and val < prev_val * 0.95:
                regressions.append(
                    f"{key[0]}@{key[1]} dropped from {prev_val} to {val} by {period_end} ({conf})"
                )
            if prev_val is None or val > prev_val:
                prev_val = val
    assert not regressions, f"Cumulative units regressed >5% in some series: {regressions}"


# Consoles where the manufacturer publishes figures regularly (first-party IR).
# If any of these loses all facts, something upstream is broken and we want to know.
MUST_HAVE_FACTS = frozenset({"switch", "ps5", "ps4", "3ds", "wii-u"})


def test_first_party_reported_consoles_have_facts(consoles_payload):
    """Consoles with consistent first-party reporting must always carry at least one fact.

    PC handhelds and Xbox are intentionally excluded — their manufacturers don't publish unit
    counts, so 'no facts' is an expected state, not a regression.
    """
    missing: list[str] = []
    for console in consoles_payload["consoles"]:
        if console["slug"] not in MUST_HAVE_FACTS:
            continue
        if not console["facts"]:
            missing.append(console["slug"])
    assert not missing, f"First-party-reported consoles with no facts: {missing}"
