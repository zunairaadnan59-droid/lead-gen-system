"""OpenStreetMap (Overpass API) - fully free and open, no key, works for any city and uses
plain Python HTTP (no curl needed). Coverage is sparser than the directories but it is a great
universal fallback and adds businesses the directories miss.

Overpass rejects browser User-Agents (406), so this sends a plain client UA. It rate-limits
hard, so we back off on HTTP 429.
"""
from __future__ import annotations

import time

from lead_finder.common import area_code, http_client, insert_business, now_stamp
from lead_finder.sources.base import city_display


def _query(cfg, city_key: str, limit: int) -> list[dict]:
    city_name = city_display(city_key, cfg)
    client = http_client(cfg)
    # shop=* catches storefront retailers likely to also run an ecommerce/online store.
    query = (
        f'[out:json][timeout:60];'
        f'area["name"="{city_name}"]["admin_level"="8"]->.a;'
        f'(nwr["shop"~"clothes|fashion|boutique|shoes|jewelry|jewellery|gift|florist|'
        f'furniture|interior_decoration|houseware|electronics|computer|books|toys|art|'
        f'beauty|cosmetics|bag|leather|department_store|variety_store"](area.a););'
        f'out center {limit};'
    )
    rows = []
    try:
        resp = None
        for attempt in range(4):
            resp = client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                headers={"User-Agent": "local-lead-finder/1.0", "Accept": "application/json"},
            )
            if resp.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"  . OSM 429, backing off {wait}s ({attempt + 1}/4)")
                time.sleep(wait)
                continue
            break
        resp.raise_for_status()
        for el in resp.json().get("elements", []):
            t = el.get("tags", {})
            if not t.get("name"):
                continue
            rows.append({
                "name": t.get("name"),
                "website": t.get("website") or t.get("contact:website"),
                "phone": t.get("phone") or t.get("contact:phone"),
                "address": ", ".join(filter(None, [
                    t.get("addr:housenumber"), t.get("addr:street"), t.get("addr:city")])) or None,
            })
    except Exception as e:
        print(f"  ! OSM query failed: {e}")
    finally:
        client.close()
    return rows


def discover_city(conn, cfg, city_key: str, existing: set, target: int) -> int:
    meta = (cfg.get("cities") or {}).get(city_key) or {}
    state = meta.get("state")
    codes = {str(a) for a in meta.get("area_codes", [])}
    print(f"[openstreetmap] {city_key} ({city_display(city_key, cfg)}), target {target} - {now_stamp()}")
    added = 0
    for r in _query(cfg, city_key, max(target * 2, 100)):
        if added >= target:
            break
        ph = r.get("phone")
        # Keep rows with a local phone, or with a website (a later owner-extraction pass can
        # read the site for the phone). Skip non-local phones and contentless rows.
        if ph and codes and area_code(ph) not in codes:
            continue
        if not ph and not r.get("website"):
            continue
        if insert_business(conn, r, city_key, state, "openstreetmap"):
            added += 1
    conn.commit()
    print(f"[openstreetmap] {city_key}: +{added} businesses")
    return added
