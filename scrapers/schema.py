"""JSON Schema for the normalized dataset. Shared by the normalizer and tests."""

from __future__ import annotations

from typing import Any

CONSOLES_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "console-tally consoles",
    "type": "object",
    "required": ["schema_version", "generated_at", "consoles"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "string", "const": "1"},
        "generated_at": {"type": "string", "format": "date-time"},
        "consoles": {
            "type": "array",
            "items": {"$ref": "#/$defs/Console"},
        },
    },
    "$defs": {
        "Console": {
            "type": "object",
            "required": [
                "slug",
                "display_name",
                "manufacturer",
                "generation",
                "form_factor",
                "launch_date",
                "variants",
                "facts",
            ],
            "additionalProperties": False,
            "properties": {
                "slug": {"type": "string", "pattern": "^[a-z0-9-]+$"},
                "display_name": {"type": "string"},
                "manufacturer": {"type": "string"},
                "generation": {"enum": ["last", "current", "pre_last"]},
                "form_factor": {"enum": ["home", "hybrid", "handheld", "pc_handheld"]},
                "launch_date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                "variants": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string", "pattern": "^[a-z0-9-]+$"},
                },
                "notes": {"type": "string"},
                "wikipedia_article": {"type": "string"},
                "facts": {"type": "array", "items": {"$ref": "#/$defs/Fact"}},
            },
        },
        "Fact": {
            "type": "object",
            "required": [
                "variant",
                "region",
                "source_key",
                "source_url",
                "fetched_at",
                "confidence",
            ],
            "additionalProperties": False,
            "properties": {
                "variant": {"type": "string", "pattern": "^[a-z0-9-]+$"},
                "region": {
                    "enum": ["global", "japan", "americas", "emea", "apac_ex_jp"],
                },
                "units_cumulative": {"type": ["integer", "null"], "minimum": 0},
                "units_period": {"type": ["integer", "null"], "minimum": 0},
                "period_start": {
                    "type": ["string", "null"],
                    "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                },
                "period_end": {
                    "type": "string",
                    "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                },
                "source_key": {"type": "string"},
                "source_url": {"type": "string", "format": "uri"},
                "fetched_at": {"type": "string", "format": "date-time"},
                "confidence": {
                    "enum": ["official", "analyst_estimate", "press_leak", "derived"],
                },
                "note": {"type": "string"},
            },
            "anyOf": [
                {"required": ["units_cumulative"]},
                {"required": ["units_period"]},
            ],
        },
    },
}


REGIONS_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["schema_version", "generated_at", "regions"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "string", "const": "1"},
        "generated_at": {"type": "string", "format": "date-time"},
        "regions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["slug", "display_name", "leaderboard"],
                "additionalProperties": False,
                "properties": {
                    "slug": {"type": "string"},
                    "display_name": {"type": "string"},
                    "description": {"type": "string"},
                    "leaderboard": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["console_slug", "units_cumulative", "source_url"],
                            "additionalProperties": False,
                            "properties": {
                                "console_slug": {"type": "string"},
                                "display_name": {"type": "string"},
                                "manufacturer": {"type": "string"},
                                "units_cumulative": {"type": "integer"},
                                "period_end": {"type": "string"},
                                "source_key": {"type": "string"},
                                "source_url": {"type": "string"},
                                "confidence": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    },
}
