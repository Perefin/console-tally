"""Unit tests for normalize's fact-merging precedence rules."""

from __future__ import annotations

from scrapers.normalize import CONFIDENCE_RANK, _fact_precedence


def test_confidence_ranking_is_strict():
    assert (
        CONFIDENCE_RANK["official"]
        > CONFIDENCE_RANK["press_leak"]
        > CONFIDENCE_RANK["analyst_estimate"]
        > CONFIDENCE_RANK["derived"]
    )


def test_fact_precedence_prefers_official_over_estimate():
    official = {"confidence": "official", "fetched_at": "2020-01-01T00:00:00Z"}
    estimate = {"confidence": "analyst_estimate", "fetched_at": "2026-01-01T00:00:00Z"}
    assert _fact_precedence(official) > _fact_precedence(estimate)


def test_fact_precedence_breaks_ties_by_fetched_at():
    older = {"confidence": "official", "fetched_at": "2025-01-01T00:00:00Z"}
    newer = {"confidence": "official", "fetched_at": "2026-01-01T00:00:00Z"}
    assert _fact_precedence(newer) > _fact_precedence(older)
