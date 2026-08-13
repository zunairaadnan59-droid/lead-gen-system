"""Export the finished call sheet: dedupe, optional local-area-code filter, drop anything
already delivered on a previous run, apply an optional suppression list, and write a clean CSV.

Columns: company, owner, phone, website, email, location, source.
"""
from __future__ import annotations

import csv
import re

from lead_finder.common import (
    area_code, get_db, load_config, normalize_phone, now_stamp, ROOT, today,
)
from lead_finder.sources.base import city_display

COLUMNS = ["company", "owner", "phone", "website", "email", "location", "source"]


def _load_suppress() -> set[str]:
    """Optional data/suppress.txt - phone numbers you never want exported (one per line)."""
    out = set()
    path = ROOT / "data" / "suppress.txt"
    if path.exists():
        for line in open(path, "r", encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#"):
                n = normalize_phone(line)
                if n:
                    out.add(n)
    return out


def _domain_of_row(d: dict) -> str:
    return re.sub(r"^https?://(www\.)?", "", (d.get("website") or "")).split("/")[0].lower()


def _row(d: dict, cfg: dict) -> dict:
    raw_city = (d.get("city") or "")
    city = city_display(raw_city, cfg) if raw_city else ""
    state = (d.get("state") or "").upper()
    return {
        "company": d.get("name"),
        "owner": d.get("owner_name"),
        "phone": d.get("direct_phone") or d.get("business_phone"),
        "website": d.get("website"),
        "email": d.get("email"),
        "location": ", ".join(p for p in (city, state) if p),
        "source": d.get("source"),
    }


def run(city: str | None = None, count: int | None = None, local: bool = True,
        record_delivered: bool = True) -> dict:
    cfg = load_config()
    conn = get_db()
    city = city.lower().replace(" ", "") if city else None
    fit_min = cfg.get("icp", {}).get("fit_min_score", 0)
    suppress = _load_suppress()
    codes = None
    if local and city:
        codes = {str(a) for a in (cfg.get("cities", {}).get(city, {}) or {}).get("area_codes", [])} or None

    where, params = "WHERE 1=1", []
    if city:
        where += " AND b.city=?"
        params.append(city)
    rows = conn.execute(
        f"""SELECT b.id AS business_id, b.name, b.city, b.state, b.website,
                   b.phone AS business_phone, b.source,
                   c.owner_name, c.email, c.direct_phone, c.fit_score
            FROM businesses b LEFT JOIN contacts c ON c.business_id=b.id
            {where}""",
        params,
    ).fetchall()

    delivered = {r[0] for r in conn.execute("SELECT domain FROM delivered WHERE domain IS NOT NULL")}
    delivered_ph = {r[0] for r in conn.execute("SELECT phone FROM delivered WHERE phone IS NOT NULL")}

    out, seen = [], set()
    dropped = {"fit": 0, "no_phone": 0, "non_local": 0, "suppressed": 0, "dupe": 0, "delivered": 0}
    for r in rows:
        d = dict(r)
        if d["fit_score"] is not None and d["fit_score"] < fit_min:
            dropped["fit"] += 1
            continue
        phone = normalize_phone(d.get("direct_phone") or d.get("business_phone"))
        if not phone:
            dropped["no_phone"] += 1
            continue
        if codes and area_code(phone) not in codes:
            dropped["non_local"] += 1
            continue
        if phone in suppress:
            dropped["suppressed"] += 1
            continue
        domain = _domain_of_row(d)
        if (domain and domain in delivered) or phone in delivered_ph:
            dropped["delivered"] += 1
            continue
        key = (domain, "" if domain else phone)
        if key in seen:
            dropped["dupe"] += 1
            continue
        seen.add(key)
        d["direct_phone"] = phone
        out.append(d)

    # best-fit first, then businesses that already have an owner name
    out.sort(key=lambda d: (-(d.get("fit_score") or 0), 0 if d.get("owner_name") else 1))
    if count:
        out = out[:count]

    export = [_row(d, cfg) for d in out]
    out_dir = ROOT / "data" / "leads"
    out_dir.mkdir(parents=True, exist_ok=True)
    fpath = out_dir / f"{(city or 'all')}_{today()}.csv"
    with open(fpath, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(export)

    if record_delivered:
        for d in out:
            conn.execute(
                "INSERT OR IGNORE INTO delivered (business_id, domain, phone, delivered_at) VALUES (?,?,?,?)",
                (d.get("business_id"), _domain_of_row(d), d.get("direct_phone"), now_stamp()))
        conn.commit()
    conn.close()

    drops = ", ".join(f"{k}={v}" for k, v in dropped.items() if v)
    print(f"[export] {len(out)} leads -> {fpath}")
    print(f"[export] dropped: {drops}" if drops else "[export] nothing dropped")
    return {"count": len(out), "path": str(fpath)}
