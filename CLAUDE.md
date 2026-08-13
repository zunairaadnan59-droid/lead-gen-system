# Local Lead Finder - project guide for Claude Code

This repository is a small, self-contained lead-generation tool. Claude Code is the engine:
slash commands orchestrate a Python pipeline, and Claude itself does the one part that needs
real reading - identifying the owner of each business from its website.

## What it does

Given a city and a count, it collects that many **local business leads** (company, phone,
website, location) from public sources, keeping only businesses whose phone sits in the city's
own area codes. Then, optionally, Claude reads each business's site to add the **owner's name
and email**. Output is a clean CSV.

## The two commands (this is the whole UX)

- **`/find-leads <city> [count]`** - discover + export. Fast, free, no reading. Runs
  `python run.py find`. Reports the count, the CSV path, and honestly whether the city had
  fewer leads than asked for.
- **`/enrich-owners [city] [limit]`** - the Claude-native pass. Fetches the discovered sites,
  then Claude reads them and writes owner name + title + email + a fit score per business.

Both are defined in `.claude/commands/`.

## Pipeline (all in `lead_finder/`)

```
discover.py   orchestrates the sources for one city until `count` unique local leads or dry
  sources/    one module per platform:
    designrush.py     human-reviewed agency directory (via curl; profile-page phone; local filter)
    yellowpages.py    broad local coverage, multi-keyword (via curl)
    yelp.py           official Yelp Fusion API - only if YELP_API_KEY is set
    openstreetmap.py  free & open, no key, Python HTTP (universal fallback)
fetch.py      downloads each site's key pages to data/raw/<id>/  (for the owner pass)
extract.py    regex emails/phones + builds data/work/needs_claude.jsonl for Claude to read
apply.py      merges Claude's data/work/claude_results.jsonl into the DB
export.py     dedupe + local filter + drop already-delivered + write data/leads/<city>_<date>.csv
```

Data model (SQLite at `data/leads.db`, schema in `lead_finder/db/schema.sql`): `businesses` ->
`contacts` (1:1) -> `pages`; plus a `delivered` table so repeat runs return fresh leads.

## When you extract owners, judge carefully

The value of these leads is a **correct** owner name. A wrong one burns a cold call. So:
- The owner is a real person who **leads this company** (founder/owner/CEO/principal).
- Reject client testimonials, quoted experts, blog authors, and non-decision staff.
- If you are not reasonably confident, write `null`. A null beats a wrong name.

## Use it responsibly (please keep this intact)

- Everything here reads **public data** a browser can see. Keep the polite pacing (the delays in
  `config.yaml`); do not remove them or add proxies to defeat rate limits.
- Respect each site's Terms of Service and `robots`. YellowPages and Yelp restrict scraping -
  that's why Yelp goes through its official API here; use YellowPages within its terms.
- Calling and emailing people is regulated (e.g. TCPA/CAN-SPAM in the US, GDPR/PECR in the EU).
  Whoever runs this is responsible for complying with the laws that apply to them, honouring
  do-not-call/opt-out requests, and using `data/suppress.txt` for numbers to exclude.

## Extending it

- **New city:** add a block under `cities:` in `config.yaml` with `area_codes` (and `dr_slug`
  for DesignRush coverage). YellowPages/Yelp/OpenStreetMap work off the city name alone.
- **Different niche:** edit `icp.keywords` (e.g. "roofing company", "dental clinic").
- **New source:** add `lead_finder/sources/<name>.py` exposing
  `discover_city(conn, cfg, city_key, existing, target) -> int`, then list it in `discover.sources`.

## House style

No em dashes. Keep comments to the non-obvious "why". Every paid/keyed feature must degrade to a
clean skip when its key is absent - the free path must always work with zero configuration.
