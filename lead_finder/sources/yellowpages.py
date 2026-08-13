"""YellowPages - indexed by physical location, so nearly every listing is a genuine local
business with a local phone. Each search keyword surfaces a different set, so we sweep the
keywords from config and dedupe by phone.

Public data, polite pacing. YellowPages restricts scraping in its Terms and soft-rate-limits
after a burst of requests, so we throttle between pages and stop cleanly when a page returns
nothing. Be considerate: keep the pacing, and read their Terms before heavy use.
"""
from __future__ import annotations

import time
from urllib.parse import quote_plus

from lead_finder.common import (
    area_code, curl_get, insert_business, normalize_phone, now_stamp,
)
from lead_finder.sources.base import city_display, jsonld_local_businesses


def _card_websites(html: str) -> dict[str, str]:
    """Best-effort business name -> external website, from YP's result-card markup.

    The JSON-LD blocks (used for name/phone) don't carry the outbound site link; that only
    lives in each result card's "Website" button. Keyed by name so it can be joined against
    the JSON-LD list; returns {} (not an error) if the page layout doesn't match, so a site
    markup change degrades to phone-only leads instead of breaking discovery.
    """
    out = {}
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        for card in soup.select("div.result"):
            name_el = card.select_one("a.business-name")
            site_el = card.select_one("a.track-visit-website")
            href = site_el.get("href") if site_el else None
            if name_el and href:
                out[name_el.get_text(strip=True)] = href
    except Exception:
        pass
    return out


def discover_city(conn, cfg, city_key: str, existing: set, target: int) -> int:
    meta = (cfg.get("cities") or {}).get(city_key) or {}
    state = meta.get("state")
    codes = {str(a) for a in meta.get("area_codes", [])}
    display = city_display(city_key, cfg)
    dcfg = cfg.get("discover", {})
    keywords = cfg.get("icp", {}).get("keywords") or ["marketing agency"]
    max_pages = int(dcfg.get("yp_max_pages_per_keyword", 8))
    delay = dcfg.get("page_delay_seconds", 2)

    print(f"[yellowpages] {city_key} ({display}, {state}) local {sorted(codes)}, "
          f"{len(keywords)} keywords, target {target} - {now_stamp()}")
    added = 0
    for kw in keywords:
        if added >= target:
            break
        for page in range(1, max_pages + 1):
            if added >= target:
                break
            geo = quote_plus(f"{display}, {state}")
            url = (f"https://www.yellowpages.com/search?search_terms={quote_plus(kw)}"
                   f"&geo_location_terms={geo}" + (f"&page={page}" if page > 1 else ""))
            html = curl_get(url) or ""
            biz = jsonld_local_businesses(html)
            if not biz:
                break                          # blocked or end of results for this keyword
            sites = _card_websites(html)
            kept = 0
            for name, tel in biz:
                ph = normalize_phone(tel)
                if not ph or ph in existing:
                    continue
                if codes and area_code(ph) not in codes:
                    continue
                existing.add(ph)
                row = {"name": name, "phone": ph, "website": sites.get(name)}
                if insert_business(conn, row, city_key, state, "yellowpages"):
                    added += 1
                    kept += 1
                if added >= target:
                    break
            conn.commit()
            print(f"  . '{kw}' p{page}: {len(biz)} listed, +{kept} new local (total {added})")
            time.sleep(delay)
    print(f"[yellowpages] {city_key}: +{added} unique local leads")
    return added
