"""Shared helpers for the discovery sources: HTML/JSON-LD parsing and reference data."""
from __future__ import annotations

import json
import re

from lead_finder.common import domain_of

# Full lowercase US state names, for building directory URL paths.
STATE_NAMES = {
    "AL": "alabama", "AK": "alaska", "AZ": "arizona", "AR": "arkansas", "CA": "california",
    "CO": "colorado", "CT": "connecticut", "DE": "delaware", "FL": "florida", "GA": "georgia",
    "HI": "hawaii", "ID": "idaho", "IL": "illinois", "IN": "indiana", "IA": "iowa",
    "KS": "kansas", "KY": "kentucky", "LA": "louisiana", "ME": "maine", "MD": "maryland",
    "MA": "massachusetts", "MI": "michigan", "MN": "minnesota", "MS": "mississippi",
    "MO": "missouri", "MT": "montana", "NE": "nebraska", "NV": "nevada", "NH": "new-hampshire",
    "NJ": "new-jersey", "NM": "new-mexico", "NY": "new-york", "NC": "north-carolina",
    "ND": "north-dakota", "OH": "ohio", "OK": "oklahoma", "OR": "oregon", "PA": "pennsylvania",
    "RI": "rhode-island", "SC": "south-carolina", "SD": "south-dakota", "TN": "tennessee",
    "TX": "texas", "UT": "utah", "VT": "vermont", "VA": "virginia", "WA": "washington",
    "WV": "west-virginia", "WI": "wisconsin", "WY": "wyoming",
}

# Social / platform / publisher domains that show up as outbound links in page chrome but are
# NOT the local business we want. Never admit these as leads.
NON_BUSINESS_DOMAINS = {
    "x.com", "twitter.com", "linkedin.com", "youtube.com", "facebook.com", "instagram.com",
    "tiktok.com", "pinterest.com", "threads.net", "reddit.com", "medium.com", "google.com",
    "apple.com", "yelp.com", "clutch.co", "goodfirms.co", "sortlist.com", "upcity.com",
    "trustpilot.com", "glassdoor.com", "crunchbase.com", "designrush.com", "yellowpages.com",
    "wa.me", "whatsapp.com", "t.me",
}

_PAIR_RE = re.compile(
    r'href="(https?://[^"]+)"[^>]*rel="[^"]*nofollow[^"]*"[^>]*>([^<]{1,90})</a>'
)


def city_display(city_key: str, cfg: dict | None = None) -> str:
    """Human city name for a config key. Uses `display` from config if set, else Title Case."""
    if cfg:
        meta = (cfg.get("cities") or {}).get(city_key) or {}
        if meta.get("display"):
            return meta["display"]
    return city_key.replace("-", " ").title()


def parse_nofollow_pairs(html: str) -> list[dict]:
    """Return [{name, website}] from a directory listing's outbound nofollow links.

    BeautifulSoup is order- and nesting-independent, so a markup tweak does not silently
    zero us out; the regex is only a fallback if the DOM parse finds nothing.
    """
    pairs = []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        for a in soup.select('a[href][rel~="nofollow"]'):
            href = a.get("href") or ""
            if href.startswith("http"):
                pairs.append((href, a.get_text(" ", strip=True)))
    except Exception:
        pairs = []
    if not pairs:
        pairs = _PAIR_RE.findall(html)

    rows, seen = [], set()
    for href, name in pairs:
        dom = domain_of(href.split("?")[0])
        name = (name or "").strip()[:90]
        if not dom or dom in NON_BUSINESS_DOMAINS or dom in seen or not name:
            continue
        seen.add(dom)
        rows.append({"name": name, "website": f"https://{dom}/"})
    return rows


def jsonld_blocks(html: str) -> list:
    """Yield every parsed JSON-LD object embedded in the page."""
    out = []
    for block in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S):
        try:
            data = json.loads(block)
        except Exception:
            continue
        out.append(data)
    return out


def jsonld_local_businesses(html: str) -> list[tuple[str, str]]:
    """Return (name, telephone) pairs from LocalBusiness-style JSON-LD nodes."""
    out = []
    for data in jsonld_blocks(html):
        nodes = data if isinstance(data, list) else [data]
        for o in nodes:
            if isinstance(o, dict) and o.get("telephone") and o.get("name"):
                out.append((str(o["name"]).strip(), str(o["telephone"])))
    return out
