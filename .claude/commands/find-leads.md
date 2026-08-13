---
description: Find up to N local business leads for a city (phone + website + location)
argument-hint: <city> [count]
---

You are running the **Local Lead Finder**. The user wants leads for a city.

Arguments: `$ARGUMENTS`
- The first word is the **city key** (e.g. `austin`, `losangeles`, `miami`).
- The optional second word is the **count** (how many leads). Default to `100` if omitted.

## Steps

1. Parse the city key and count from the arguments. Lowercase the city; strip spaces
   (`los angeles` -> `losangeles`).

2. Run the pipeline:
   ```
   python run.py find --city <city> --count <count>
   ```
   This sweeps the configured public sources in order (DesignRush -> YellowPages -> Yelp if a
   key is set -> OpenStreetMap), keeps only businesses whose phone is in the city's area codes,
   de-duplicates across sources and against everything delivered on previous runs, and writes a
   CSV to `data/leads/<city>_<date>.csv`.

3. Read the command's printed summary and the CSV. Then report to the user, concisely:
   - How many leads were found and the **path to the CSV**.
   - The per-source breakdown (e.g. "DesignRush 40, YellowPages 120, OpenStreetMap 8").
   - **If fewer than requested were found**, say so plainly: "Only X leads are available for
     <city> - all public sources are exhausted for this city." Do not pad the number or invent
     leads. Suggest they try a nearby city, add more `keywords` in `config.yaml`, or run
     `/enrich-owners` to add owner names to what was found.
   - Remind them the CSV has: company, owner (blank until `/enrich-owners`), phone, website,
     email, location, source.

## If it errors

- **"Unknown city"**: the city is not in `config.yaml`. Show the user how to add it - copy a
  block under `cities:` with the metro's `area_codes` (and optional `dr_slug`). List a few of
  the cities that ARE configured.
- **curl missing / all sources returned 0**: DesignRush and YellowPages need `curl` (ships with
  Windows 10+, macOS, Linux). OpenStreetMap works without it. Mention this and that a directory
  may be briefly rate-limiting - waiting a minute and re-running usually clears it.

Keep the reply tight. The user wants the number, the file, and the honest "is that enough".
