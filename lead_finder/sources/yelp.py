"""Yelp - via the official Yelp Fusion API (optional).

Yelp blocks page scraping, so the legitimate way to use it is their free Fusion API. This
source activates only if you set YELP_API_KEY in .env (free key from
https://docs.developer.yelp.com/ - the free tier allows a few hundred calls/day). Without a
key this source is skipped and the other three still run.

Returns name + local phone per business (the search endpoint does not expose the business's
own website, so `/enrich-owners` cannot add owner names to Yelp-only rows - they stay
company + phone + city, which is still dialable).
"""
from __future__ import annotations

import os
import time

from lead_finder.common import area_code, http_client, insert_business, normalize_phone, now_stamp
from lead_finder.sources.base import city_display

_ENDPOINT = "https://api.yelp.com/v3/businesses/search"
_PAGE = 50  # Fusion API max limit per call


def discover_city(conn, cfg, city_key: str, existing: set, target: int) -> int:
    key = os.getenv("YELP_API_KEY")
    if not key:
        return 0                       # optional source; no key -> silently skipped
    meta = (cfg.get("cities") or {}).get(city_key) or {}
    state = meta.get("state")
    codes = {str(a) for a in meta.get("area_codes", [])}
    location = f"{city_display(city_key, cfg)}, {state}"
    dcfg = cfg.get("discover", {})
    keywords = cfg.get("icp", {}).get("keywords") or ["marketing agency"]
    delay = dcfg.get("page_delay_seconds", 2)

    print(f"[yelp] {city_key} ({location}) local {sorted(codes)}, api - {now_stamp()}")
    client = http_client(cfg)
    client.headers.update({"Authorization": f"Bearer {key}"})
    added = 0
    try:
        for kw in keywords:
            if added >= target:
                break
            for offset in range(0, 240, _PAGE):    # Fusion caps offset+limit at ~240 on free tier
                if added >= target:
                    break
                try:
                    resp = client.get(_ENDPOINT, params={
                        "term": kw, "location": location, "limit": _PAGE, "offset": offset})
                    if resp.status_code != 200:
                        break
                    businesses = resp.json().get("businesses", [])
                except Exception:
                    break
                if not businesses:
                    break
                kept = 0
                for b in businesses:
                    ph = normalize_phone(b.get("phone") or b.get("display_phone"))
                    if not ph or ph in existing:
                        continue
                    if codes and area_code(ph) not in codes:
                        continue
                    existing.add(ph)
                    if insert_business(conn, {"name": (b.get("name") or "").strip(), "phone": ph},
                                       city_key, state, "yelp"):
                        added += 1
                        kept += 1
                    if added >= target:
                        break
                conn.commit()
                print(f"  . '{kw}' offset {offset}: {len(businesses)} listed, +{kept} new local (total {added})")
                time.sleep(delay)
    finally:
        client.close()
    print(f"[yelp] {city_key}: +{added} unique local leads")
    return added
