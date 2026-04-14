# Contributing

## Updating a manual estimate

Manual estimates live in `data/manual/*.json`. Each fact must include a public source URL.

Example: you see a news article citing "Ampere Analysis: Xbox Series X|S at 29M units through 2025". To add it:

1. Edit `data/manual/xbox_estimates.json`.
2. Append a new entry:

```json
{
  "variant": "xbox-series",
  "region": "global",
  "units_cumulative": 29000000,
  "period_end": "2025-12-31",
  "source_key": "ampere_2026_03_12",
  "source_url": "https://www.ampereanalysis.com/insights/example",
  "fetched_at": "2026-03-12T00:00:00Z",
  "confidence": "analyst_estimate",
  "note": "From Ampere Analysis press release, cited by GamesIndustry.biz"
}
```

3. Run `python -m scrapers.normalize` to regenerate derived files.
4. Run `pytest` — schema + canary tests must pass.
5. Open a PR.

## Adding a new source

1. Add a scraper in `scrapers/your_source.py` following the shape of `scrapers/sec_edgar.py`.
2. Register it in the appropriate workflow (`daily.yml` or `weekly.yml`).
3. Extend the sources page (`site/src/pages/sources.astro`) with a description + methodology.
4. Add a test that exercises a cached fixture response.

## Running locally

```bash
# Python scrapers
uv sync
uv run python -m scrapers.sec_edgar
uv run python -m scrapers.wikipedia
uv run python -m scrapers.normalize

# Tests
uv run pytest

# Site
cd site && npm install && npm run build
npm run preview   # http://localhost:4321/console-tally/
```
