"""Canonical registry of every console tracked by console-tally.

Scrapers reference these slugs when emitting facts. The normalizer uses this
registry as the source of truth for console metadata (display name, generation,
launch date, family membership). Per-variant facts point at a `variant` slug
that is a member of `variants`.

Keep this file boring and explicit — it is the most-linked-to code in the repo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Generation = Literal["last", "current", "pre_last"]
FormFactor = Literal["home", "hybrid", "handheld", "pc_handheld"]


@dataclass(frozen=True)
class Console:
    slug: str
    display_name: str
    manufacturer: str
    generation: Generation
    form_factor: FormFactor
    launch_date: str  # YYYY-MM-DD (earliest-region launch)
    variants: tuple[str, ...]  # variant slugs; the base slug is usually included
    notes: str = ""
    wikipedia_article: str = ""  # title used by Wikipedia REST API


@dataclass(frozen=True)
class Region:
    slug: str
    display_name: str
    description: str = ""


REGIONS: tuple[Region, ...] = (
    Region("global", "Global", "Worldwide cumulative."),
    Region("japan", "Japan", "Manufacturer-reported or Famitsu weekly."),
    Region("americas", "Americas", "Manufacturer regional breakdown or Circana (NPD) press releases."),
    Region("emea", "Europe, Middle East & Africa", "Manufacturer regional breakdown or GfK/Ampere press releases."),
    Region("apac_ex_jp", "Asia-Pacific (ex. Japan)", "Sparse; mostly manufacturer regional breakdowns."),
)

VALID_REGIONS: frozenset[str] = frozenset(r.slug for r in REGIONS)


CONSOLES: tuple[Console, ...] = (
    # ---------------- Current gen ----------------
    Console(
        slug="ps5",
        display_name="PlayStation 5",
        manufacturer="Sony",
        generation="current",
        form_factor="home",
        launch_date="2020-11-12",
        variants=("ps5", "ps5-digital", "ps5-slim", "ps5-pro"),
        wikipedia_article="PlayStation_5",
    ),
    Console(
        slug="xbox-series",
        display_name="Xbox Series X|S",
        manufacturer="Microsoft",
        generation="current",
        form_factor="home",
        launch_date="2020-11-10",
        variants=("xbox-series", "xbox-series-x", "xbox-series-s"),
        notes="Microsoft stopped reporting unit sales in 2015. Unit totals are analyst estimates; most coverage does not split Series X vs. Series S so we track a 'xbox-series' rollup variant alongside the individual SKUs.",
        wikipedia_article="Xbox_Series_X_and_Series_S",
    ),
    Console(
        slug="switch-2",
        display_name="Nintendo Switch 2",
        manufacturer="Nintendo",
        generation="current",
        form_factor="hybrid",
        launch_date="2025-06-05",
        variants=("switch-2",),
        wikipedia_article="Nintendo_Switch_2",
    ),
    # ---------------- Last gen (still being sold in some cases) ----------------
    Console(
        slug="switch",
        display_name="Nintendo Switch",
        manufacturer="Nintendo",
        generation="last",
        form_factor="hybrid",
        launch_date="2017-03-03",
        variants=("switch", "switch-oled", "switch-lite"),
        notes="Mid-gen variants (OLED, Lite) are tracked as part of the Switch family.",
        wikipedia_article="Nintendo_Switch",
    ),
    Console(
        slug="ps4",
        display_name="PlayStation 4",
        manufacturer="Sony",
        generation="last",
        form_factor="home",
        launch_date="2013-11-15",
        variants=("ps4", "ps4-slim", "ps4-pro"),
        wikipedia_article="PlayStation_4",
    ),
    Console(
        slug="xbox-one",
        display_name="Xbox One",
        manufacturer="Microsoft",
        generation="last",
        form_factor="home",
        launch_date="2013-11-22",
        variants=("xbox-one", "xbox-one-s", "xbox-one-x"),
        notes="Last official Xbox One sales figure disclosed by Microsoft: ~2015. Later figures are estimates.",
        wikipedia_article="Xbox_One",
    ),
    Console(
        slug="3ds",
        display_name="Nintendo 3DS family",
        manufacturer="Nintendo",
        generation="pre_last",
        form_factor="handheld",
        launch_date="2011-02-26",
        variants=("3ds", "3ds-xl", "2ds", "new-3ds", "new-3ds-xl", "new-2ds-xl"),
        wikipedia_article="Nintendo_3DS",
    ),
    Console(
        slug="wii-u",
        display_name="Wii U",
        manufacturer="Nintendo",
        generation="pre_last",
        form_factor="home",
        launch_date="2012-11-18",
        variants=("wii-u",),
        wikipedia_article="Wii_U",
    ),
    Console(
        slug="ps-vita",
        display_name="PlayStation Vita",
        manufacturer="Sony",
        generation="pre_last",
        form_factor="handheld",
        launch_date="2011-12-17",
        variants=("ps-vita",),
        notes="Sony never disclosed a final lifetime figure. ~15M is the widely-cited analyst estimate.",
        wikipedia_article="PlayStation_Vita",
    ),
    # ---------------- PC handhelds ----------------
    Console(
        slug="steam-deck",
        display_name="Steam Deck",
        manufacturer="Valve",
        generation="current",
        form_factor="pc_handheld",
        launch_date="2022-02-25",
        variants=("steam-deck-lcd", "steam-deck-oled"),
        notes="Valve does not publicly disclose unit sales. Figures come from press leaks and analyst estimates.",
        wikipedia_article="Steam_Deck",
    ),
    Console(
        slug="rog-ally",
        display_name="ASUS ROG Ally",
        manufacturer="ASUS",
        generation="current",
        form_factor="pc_handheld",
        launch_date="2023-06-13",
        variants=("rog-ally", "rog-ally-x"),
        notes="ASUS does not break out Ally unit sales. Estimates only.",
        wikipedia_article="ASUS_ROG_Ally",
    ),
    Console(
        slug="legion-go",
        display_name="Lenovo Legion Go",
        manufacturer="Lenovo",
        generation="current",
        form_factor="pc_handheld",
        launch_date="2023-10-31",
        variants=("legion-go", "legion-go-s"),
        notes="Lenovo does not break out Legion Go unit sales. Estimates only.",
        wikipedia_article="Lenovo_Legion_Go",
    ),
    Console(
        slug="msi-claw",
        display_name="MSI Claw",
        manufacturer="MSI",
        generation="current",
        form_factor="pc_handheld",
        launch_date="2024-03-05",
        variants=("msi-claw-a1m", "msi-claw-8-ai"),
        notes="MSI does not break out Claw unit sales. Estimates only.",
        wikipedia_article="MSI_Claw",
    ),
    Console(
        slug="ayaneo",
        display_name="AYANEO family",
        manufacturer="AYANEO",
        generation="current",
        form_factor="pc_handheld",
        launch_date="2021-03-26",
        variants=("ayaneo",),
        notes="Private company; no disclosed sales figures. Estimates only.",
        wikipedia_article="",
    ),
    Console(
        slug="gpd-win",
        display_name="GPD Win family",
        manufacturer="GPD",
        generation="current",
        form_factor="pc_handheld",
        launch_date="2016-10-20",
        variants=("gpd-win",),
        notes="Private company; no disclosed sales figures. Estimates only.",
        wikipedia_article="GPD_Win",
    ),
    Console(
        slug="onexplayer",
        display_name="OneXPlayer family",
        manufacturer="One-Netbook",
        generation="current",
        form_factor="pc_handheld",
        launch_date="2021-07-01",
        variants=("onexplayer",),
        notes="Private company; no disclosed sales figures. Estimates only.",
        wikipedia_article="",
    ),
)

CONSOLES_BY_SLUG: dict[str, Console] = {c.slug: c for c in CONSOLES}
VARIANT_TO_CONSOLE: dict[str, str] = {
    v: c.slug for c in CONSOLES for v in c.variants
}
VALID_CONFIDENCE: frozenset[str] = frozenset(
    {"official", "analyst_estimate", "press_leak", "derived"}
)


def resolve_console(variant_or_slug: str) -> Console | None:
    """Given a variant slug or console slug, return the parent console (or None)."""
    if variant_or_slug in CONSOLES_BY_SLUG:
        return CONSOLES_BY_SLUG[variant_or_slug]
    parent = VARIANT_TO_CONSOLE.get(variant_or_slug)
    return CONSOLES_BY_SLUG.get(parent) if parent else None
