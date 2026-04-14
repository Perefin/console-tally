# console-tally

A public, automatically-updated dataset and dashboard of video game console unit sales — covering current gen, last gen, mid-gen refreshes, and PC handhelds, with regional drill-down where data exists.

**Live site:** https://perefin.github.io/console-tally/
**Data:** [`data/normalized/consoles.json`](data/normalized/consoles.json) • [`data/consoles.sqlite`](data/consoles.sqlite)
**Sources:** see [`/sources`](https://perefin.github.io/console-tally/sources) on the live site.

## What this is

- First-party numbers (Nintendo, Sony) pulled from quarterly IR filings.
- Microsoft Xbox segment revenue from the SEC EDGAR JSON API (Microsoft no longer reports Xbox units).
- Analyst estimates and press-cited figures for platforms where first-party numbers don't exist (Xbox unit estimates, Steam Deck, PC handhelds).
- Every datapoint is stored with its source URL, fetched-at timestamp, and a confidence tier (`official` / `analyst_estimate` / `press_leak` / `derived`).

## What this is NOT

- A real-time tracker. Most sources update quarterly.
- Authoritative for Xbox / Steam Deck / PC handhelds — those figures are estimates, labeled as such.

## Architecture

- `scrapers/` — Python 3.11+ scrapers for each source, written with `pdfplumber`, `requests`, `feedparser`.
- `data/raw/` — append-only raw captures per source, per day.
- `data/manual/` — hand-curated estimate snapshots for sources without a live feed. Contribute via PR.
- `data/normalized/` — canonical JSON read by the site.
- `site/` — Astro static site with Chart.js.
- `.github/workflows/` — daily + weekly + canary + deploy.

## Maintenance expectations

Realistically ~1 hour/month. Dependabot handles version bumps; a weekly canary workflow opens an issue if any source returns implausible data. Scraper breakage (source-site redesign) is rare but happens ~1–2×/year per source.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — especially for adding / updating manual estimate snapshots.

## License

MIT for the code. Sales figures are attributed inline to their original sources. See `LICENSE`.
