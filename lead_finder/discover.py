"""Discovery orchestrator - sweep every enabled source for one city until we hit the target
count of unique, locally-matched businesses, or the sources run dry.

This is what powers "give me N leads from <city>, and tell me if there aren't that many."
"""
from __future__ import annotations

from lead_finder.common import (
    existing_domains, existing_phones, get_db, load_config, now_stamp,
)
from lead_finder.sources import REGISTRY

DEFAULT_ORDER = ["designrush", "yellowpages", "yelp", "openstreetmap"]


def run(city_key: str, target: int, sources: list[str] | None = None) -> dict:
    """Returns {added, target, enough, per_source, city}."""
    cfg = load_config()
    city_key = city_key.lower().replace(" ", "")
    cities = cfg.get("cities") or {}
    if city_key not in cities:
        known = ", ".join(sorted(cities))
        raise SystemExit(f"Unknown city '{city_key}'. Add it to config.yaml, or use one of: {known}")

    order = sources or cfg.get("discover", {}).get("sources", DEFAULT_ORDER)
    conn = get_db()
    # One shared "seen" set (domains AND phones) so no source re-adds what another found,
    # and so we never re-surface something already in the DB from a previous run.
    existing = existing_domains(conn) | existing_phones(conn)

    print("=" * 64)
    print(f"DISCOVER  city={city_key}  target={target}  sources={order}  - {now_stamp()}")
    print("=" * 64)

    per_source, added = {}, 0
    for name in order:
        if added >= target:
            break
        mod = REGISTRY.get(name)
        if not mod:
            print(f"  ! unknown source '{name}' in config - skipping")
            continue
        try:
            got = mod.discover_city(conn, cfg, city_key, existing, target - added)
        except Exception as e:
            print(f"  ! source '{name}' errored ({e}) - continuing with the rest")
            got = 0
        per_source[name] = got
        added += got

    conn.close()
    enough = added >= target
    print("-" * 64)
    print(f"DISCOVER DONE: +{added} unique local leads for {city_key}  "
          f"({'target met' if enough else 'sources exhausted'})")
    for name, n in per_source.items():
        print(f"    {name:>14}: +{n}")
    if not enough:
        print(f"  NOTE: only {added} available for {city_key} (you asked for {target}). "
              f"All configured public sources are exhausted for this city.")
    print("-" * 64)
    return {"city": city_key, "added": added, "target": target,
            "enough": enough, "per_source": per_source}
