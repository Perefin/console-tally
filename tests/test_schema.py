"""Validate the normalized dataset against the JSON Schema."""

from __future__ import annotations

import json

import jsonschema
import pytest

from scrapers.paths import NORMALIZED_DIR
from scrapers.schema import CONSOLES_SCHEMA, REGIONS_SCHEMA


@pytest.fixture(scope="module")
def consoles_payload():
    path = NORMALIZED_DIR / "consoles.json"
    if not path.exists():
        pytest.skip("consoles.json not yet generated — run scrapers.normalize first")
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def regions_payload():
    path = NORMALIZED_DIR / "regions.json"
    if not path.exists():
        pytest.skip("regions.json not yet generated")
    return json.loads(path.read_text())


def test_consoles_matches_schema(consoles_payload):
    jsonschema.validate(instance=consoles_payload, schema=CONSOLES_SCHEMA)


def test_regions_matches_schema(regions_payload):
    jsonschema.validate(instance=regions_payload, schema=REGIONS_SCHEMA)


def test_every_console_slug_is_unique(consoles_payload):
    slugs = [c["slug"] for c in consoles_payload["consoles"]]
    assert len(slugs) == len(set(slugs))


def test_facts_reference_valid_variants(consoles_payload):
    for console in consoles_payload["consoles"]:
        variants = set(console["variants"])
        for fact in console["facts"]:
            assert fact["variant"] in variants, (
                f"fact variant {fact['variant']!r} not in {console['slug']} variants {variants}"
            )
