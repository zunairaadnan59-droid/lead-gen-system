# Local Lead Finder

**Find hundreds of local business leads for any US city with one command - powered by Claude Code.**

You run one slash command (`/find-leads austin 200`) and get a clean CSV of local businesses with
their phone numbers, websites, and locations. Ask for a number and there aren't that many in the
city? It tells you straight, instead of padding the list with junk. Then a second command
(`/enrich-owners`) has Claude read each business's website and fill in the **owner's name and
email** - the part only a real reader can get right.

Everything runs on **free, public data**. No paid API is required. No accounts to buy. The one
optional add-on (Yelp) uses Yelp's own free API key.

```
company                     owner            phone           website               email                 location       source
Blue Fin Media              Sarah Coleman    +15125550142    bluefinmedia.com      sarah@bluefinmedia.com Austin, TX     designrush
Hill Country Marketing      (blank)          +15125550188    hillcountry.co                              Austin, TX     yellowpages
Lone Star Digital           Marcus Webb      +17375550110    lonestardigital.io    hello@lonestar.io      Austin, TX     designrush
```

---

## Contents

- [How it works](#how-it-works)
- [What you need](#what-you-need)
- [Install](#install)
- [Quick start](#quick-start)
- [The two commands](#the-two-commands)
- [Configure it for your niche and cities](#configure-it-for-your-niche-and-cities)
- [The output CSV](#the-output-csv)
- [Optional: turn on Yelp](#optional-turn-on-yelp)
- [Using it without Claude Code](#using-it-without-claude-code)
- [Responsible use (read this)](#responsible-use-read-this)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## How it works

For a given city, the tool sweeps several public sources in order until it has the number of
leads you asked for:

1. **DesignRush** - a human-reviewed agency directory. High quality. Reads each listing's profile
   page for its real phone and keeps only numbers in the city's area codes.
2. **YellowPages** - broad local coverage for any business type, searched across several keywords.
3. **Yelp** - only if you add a free API key (Yelp blocks scraping, so this uses their official API).
4. **OpenStreetMap** - a free, open map database. No key, works everywhere, a good backstop.

Every lead is **local-matched** (its phone is in one of the city's area codes), **de-duplicated**
across all sources, and remembered so the **next run gives you fresh leads**, not repeats.

Then, optionally, **Claude Code reads the business websites** and adds the owner's name, title,
and email. This is the clever part: your own Claude Code session is the extraction engine, so it
costs nothing extra and it is smart enough to tell a real founder from a client testimonial.

## What you need

- **Python 3.10 or newer** - <https://www.python.org/downloads/> (during install on Windows, tick
  "Add Python to PATH").
- **Claude Code** - the CLI/IDE agent this tool is built around. Install guide:
  <https://docs.claude.com/en/docs/claude-code>. (You can also run it as a plain script without
  Claude Code - see [that section](#using-it-without-claude-code).)
- **git** - to clone the repo. <https://git-scm.com/downloads>
- **curl** - used to reach DesignRush and YellowPages. It already ships with Windows 10 (1803+),
  macOS, and Linux, so you almost certainly have it. OpenStreetMap works even without it.

## Install

```bash
# 1. Clone the repo
git clone https://github.com/zainsaeeed/claude-lead-finder.git
cd claude-lead-finder

# 2. (Recommended) create a virtual environment
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# 3. Install the dependencies
pip install -r requirements.txt

# 4. (Optional) set up the .env file for Yelp - skip if you don't want Yelp
cp .env.example .env      # Windows: copy .env.example .env
```

That's it. There is nothing to configure to get started.

## Quick start

Open the folder in **Claude Code**:

```bash
claude
```

Then type:

```
/find-leads austin 200
```

Claude runs the pipeline and reports how many leads it found, the path to the CSV
(`data/leads/austin_<date>.csv`), and whether Austin had at least 200. Open that CSV in Excel /
Google Sheets / your CRM and start calling.

Want owner names too? Follow up with:

```
/enrich-owners austin
```

Claude reads each business's website and fills in the owner column, then re-exports the CSV.

## The two commands

### `/find-leads <city> [count]`

Discovers and exports. Fast and free.

- `city` - a city key from `config.yaml` (e.g. `austin`, `miami`, `losangeles`, `chicago`).
- `count` - how many leads you want. Defaults to 100.

Examples:

```
/find-leads miami            # up to 100 Miami leads
/find-leads losangeles 300   # up to 300 Los Angeles leads
/find-leads chicago 500      # up to 500 Chicago leads
```

If a city genuinely has fewer businesses than you asked for, the command says so and stops -
no filler.

### `/enrich-owners [city] [limit]`

Has Claude read the discovered businesses' websites and add owner name, title, email, and a
fit score. Run it after `/find-leads`.

- `city` - which city to re-export when done (optional).
- `limit` - cap how many sites to read this pass (optional; handy for very large batches).

Note: this only adds owner names to leads that **have a website** (DesignRush results usually do;
YellowPages/Yelp results often don't). Those without a website stay as company + phone, which is
still perfectly callable.

## Configure it for your niche and cities

Everything lives in **`config.yaml`**. The two things you'll actually change:

**1. Your niche.** Edit `icp.keywords` to whatever business you sell to:

```yaml
icp:
  keywords:
    - "roofing company"
    - "roof repair"
    - "roofing contractor"
```

**2. Your cities.** The repo ships with ~29 major US metros. To add one, copy a block under
`cities:` and fill in the metro's area codes:

```yaml
cities:
  boise: { state: ID, area_codes: [208, 986], display: "Boise" }
```

- `area_codes` is what makes a lead "local" - you can find them on Wikipedia's "Area codes in
  <state>" page in a minute.
- `dr_slug` (optional) is the DesignRush URL path, `state-name/city-name`
  (e.g. `idaho/boise`). Add it for DesignRush coverage; without it, the other three sources still
  work off the city name alone.
- `display` is only needed if the city key isn't already a clean name.

## The output CSV

Written to `data/leads/<city>_<date>.csv` with these columns:

| column | what it is |
|---|---|
| `company` | business name |
| `owner` | owner/founder name (blank until you run `/enrich-owners`) |
| `phone` | local phone, in `+1XXXXXXXXXX` format |
| `website` | the business's site (blank for some directory sources) |
| `email` | best contact email (added by `/enrich-owners`) |
| `location` | `City, ST` |
| `source` | which platform it came from |

Runs remember what they've handed out (in the local database), so running `/find-leads austin 200`
again next week gives you **200 new** Austin leads, not the same ones.

## Optional: turn on Yelp

Yelp blocks scraping, so this tool uses Yelp's **official free Fusion API**:

1. Go to <https://docs.developer.yelp.com/>, sign in, and create an app to get an API key
   (free tier allows a few hundred calls/day).
2. Put it in your `.env`:
   ```
   YELP_API_KEY=your-key-here
   ```

The Yelp source now activates automatically. Without a key it's simply skipped.

## Using it without Claude Code

Claude Code makes it one command and adds the owner-name reading, but the discovery engine is a
plain Python program you can run yourself:

```bash
python run.py find --city austin --count 200   # discover + write the CSV
python run.py status                           # what's in the database
python run.py export --city austin             # re-write the CSV from the DB
```

The `/enrich-owners` owner-name step is the one part that needs Claude (something has to read the
websites and make a judgment call), but everything else runs standalone.

## Responsible use (read this)

This tool collects information that is already public - the same things you'd see browsing these
directories in a normal web browser. Use it like a good citizen:

- **Keep the polite pacing.** The delays in `config.yaml` are there on purpose. Don't remove them
  or add proxies to hammer a site.
- **Respect each site's Terms of Service.** YellowPages and Yelp restrict scraping; that's why
  Yelp goes through its official API here. Read their terms and stay within them.
- **Calling and emailing is regulated.** In the US that's TCPA and CAN-SPAM; in the EU, GDPR/PECR;
  other countries have their own rules. **You are responsible** for complying with the laws that
  apply to you - checking numbers against Do-Not-Call registries, honouring opt-outs, and keeping
  proper consent where required.
- **Use the suppression list.** Copy `data/suppress.example.txt` to `data/suppress.txt` and add any
  number that opts out or that you don't want contacted again. Those numbers are excluded from
  every export.

This project is provided as-is under the MIT License, for legitimate business outreach. What you
do with the data is on you.

## Troubleshooting

- **"Unknown city."** The city isn't in `config.yaml`. Add a block for it (see
  [Configure](#configure-it-for-your-niche-and-cities)), or run `python run.py status` after using
  one of the built-in cities.
- **Every source returned 0 / "curl not found."** DesignRush and YellowPages need `curl`. It ships
  with Windows 10+, macOS, and Linux; if it's missing, install it or rely on OpenStreetMap. A
  directory may also be briefly rate-limiting after heavy use - wait a minute and re-run.
- **Fewer leads than expected.** Smaller metros simply have fewer businesses in your niche.
  Broaden `icp.keywords`, add nearby cities, or turn on Yelp for extra coverage.
- **`ModuleNotFoundError`.** Activate your virtual environment and re-run
  `pip install -r requirements.txt`.

## FAQ

**Does this cost anything?** No. The default sources are free public data. Yelp is optional and
uses Yelp's free API tier.

**Do I need an Anthropic/OpenAI API key?** No. The owner-reading step uses your own Claude Code
session, not a metered API.

**Is the data accurate?** Phones and companies come straight from the directories. Owner names are
Claude's best read of each website - it's told to leave a name blank rather than guess, but always
sanity-check before an important call.

**Can it do countries other than the US?** The local-matching and phone handling are built for US
area codes today. OpenStreetMap and the keyword search are worldwide, but you'd need to adapt the
phone/area-code logic for other countries.

---

Built to be simple, honest, and free. If it helped you, pass it on.
