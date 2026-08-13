"""DesignRush directory - genuine, human-reviewed agencies (not map junk).

DesignRush city pages are padded with national agencies, so we read each listing's PROFILE
page for its real listed phone (JSON-LD `telephone`) and keep only numbers in the target
metro's area codes. That local-phone filter self-selects genuine local businesses. Different
service categories list different agencies, so we sweep several categories and dedupe by domain.

Public data, polite pacing, stops when a page returns nothing. If curl is unavailable or the
site blocks us, this returns 0 and the orchestrator falls back to the other sources.
"""
from __future__ import annotations

import time

from lead_finder.common import area_code, curl_get, domain_of, insert_business, now_stamp
from lead_finder.sources.base import jsonld_blocks, parse_nofollow_pairs


def _city_listing(html: str) -> list[dict]:
    """[{name, website, profile_url}] joining nofollow links (name->site) with the
    JSON-LD ItemList (name->DesignRush profile url)."""
    site_by_name = {r["name"].strip().lower(): r["website"] for r in parse_nofollow_pairs(html)}
    out = []
    for data in jsonld_blocks(html):
        graph = data.get("@graph", [data]) if isinstance(data, dict) else data
        for node in (graph if isinstance(graph, list) else [graph]):
            t = node.get("@type") if isinstance(node, dict) else None
            t = t if isinstance(t, list) else [t]
            if "ItemList" not in t:
                continue
            for e in node.get("itemListElement", []):
                org = e.get("item", e)
                name = (org.get("name") or "").strip()
                prof = org.get("url") or ""
                if name and "/agency/profile/" in prof:
                    out.append({"name": name, "website": site_by_name.get(name.lower()),
                                "profile_url": prof})
    return out


def _profile_phone(profile_url: str) -> str | None:
    url = ("https://www.designrush.com" + profile_url) if profile_url.startswith("/") else profile_url
    html = curl_get(url)
    if not html:
        return None
    for data in jsonld_blocks(html):
        for node in (data.get("@graph", [data]) if isinstance(data, dict) else data):
            if isinstance(node, dict) and node.get("telephone"):
                return node["telephone"]
    return None


def discover_city(conn, cfg, city_key: str, existing: set, target: int) -> int:
    meta = (cfg.get("cities") or {}).get(city_key) or {}
    slug = meta.get("dr_slug")
    if not slug:
        return 0                       # no DesignRush slug for this city; other sources cover it
    state = meta.get("state")
    codes = {str(a) for a in meta.get("area_codes", [])}
    dcfg = cfg.get("discover", {})
    categories = dcfg.get("dr_categories", ["digital-marketing"])
    max_pages = int(dcfg.get("dr_city_max_pages_per_category", 6))
    delay = dcfg.get("page_delay_seconds", 2)

    print(f"[designrush] {city_key} ({slug}) local {sorted(codes)}, "
          f"{len(categories)} categories, target {target} - {now_stamp()}")
    added, scanned = 0, 0
    for cat in categories:
        if added >= target:
            break
        page = 1
        while added < target and page <= max_pages:
            url = f"https://www.designrush.com/agency/{cat}/{slug}" + (f"?page={page}" if page > 1 else "")
            listing = _city_listing(curl_get(url) or "")
            if not listing:
                break
            kept = 0
            for a in listing:
                dom = domain_of(a["website"] or "")
                if not dom or dom in existing:
                    continue
                existing.add(dom)                       # remember either way, so no re-fetch
                phone = _profile_phone(a["profile_url"])
                scanned += 1
                if not codes or area_code(phone) in codes:
                    if insert_business(conn, {"name": a["name"], "website": a["website"],
                                              "phone": phone}, city_key, state, "designrush"):
                        added += 1
                        kept += 1
                time.sleep(0.3)
                if added >= target:
                    break
            conn.commit()
            print(f"  . {cat} p{page}: +{kept} local (running {added}, scanned {scanned})")
            page += 1
            time.sleep(delay)
    print(f"[designrush] {city_key}: +{added} local businesses")
    return added
