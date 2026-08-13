"""Regex pre-extraction (free) + build the Claude Code extraction queue.

Pulls the easy wins (emails, phones) from saved page text. Owner identity is a judgment call,
so instead of guessing it with brittle regex, every business with page text is queued to
data/work/needs_claude.jsonl for the Claude Code pass (see /enrich-owners) to read and decide.
"""
from __future__ import annotations

import json

from lead_finder.common import (
    find_emails, find_phones, get_db, load_config, now_stamp, WORK_DIR,
)


def _read_pages(conn, business_id: int) -> str:
    chunks = []
    for r in conn.execute("SELECT content_path FROM pages WHERE business_id=?", (business_id,)):
        try:
            chunks.append(open(r["content_path"], "r", encoding="utf-8").read())
        except Exception:
            pass
    return "\n\n".join(chunks)


def run() -> tuple[int, int]:
    load_config()
    conn = get_db()
    businesses = conn.execute("SELECT * FROM businesses WHERE status='fetched'").fetchall()
    print(f"[extract] {len(businesses)} businesses - {now_stamp()}")

    resolved, needs, queue = 0, 0, []
    for b in businesses:
        text = _read_pages(conn, b["id"])
        emails = find_emails(text, prefer_domain=b["domain"]) if text else []
        phones = find_phones(text) if text else []
        email = emails[0] if emails else None
        needs_claude = 1 if text else 0        # only worth a Claude read if we have page text

        conn.execute(
            """INSERT INTO contacts (business_id, email, email_source, direct_phone, method, needs_claude)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(business_id) DO UPDATE SET
                 email=COALESCE(contacts.email, excluded.email),
                 direct_phone=COALESCE(contacts.direct_phone, excluded.direct_phone),
                 needs_claude=excluded.needs_claude""",
            (b["id"], email, "regex" if email else None,
             phones[0] if phones else None, "regex", needs_claude),
        )
        conn.execute("UPDATE businesses SET status='extracted' WHERE id=?", (b["id"],))

        if needs_claude:
            needs += 1
            paths = [r["content_path"] for r in conn.execute(
                "SELECT content_path FROM pages WHERE business_id=?", (b["id"],))]
            queue.append({
                "business_id": b["id"], "name": b["name"], "website": b["website"],
                "city": b["city"], "state": b["state"], "text_paths": paths,
                "regex_email": email, "regex_phone": phones[0] if phones else None,
            })
        else:
            resolved += 1
    conn.commit()
    conn.close()

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    qpath = WORK_DIR / "needs_claude.jsonl"
    with open(qpath, "w", encoding="utf-8") as f:
        for item in queue:
            f.write(json.dumps(item) + "\n")

    print(f"[extract] resolved by regex: {resolved} | queued for Claude: {needs}")
    print(f"[extract] queue -> {qpath}")
    return resolved, needs
