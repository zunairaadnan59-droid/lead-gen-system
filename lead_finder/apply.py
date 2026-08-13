"""Merge the Claude Code extraction pass results into the database.

The Claude pass (see .claude/commands/enrich-owners.md) reads data/work/needs_claude.jsonl,
opens each page's text, and writes data/work/claude_results.jsonl with one JSON object per line:
  {"business_id": 12, "owner_name": "...", "owner_title": "...", "email": "...",
   "direct_phone": "...", "fit_score": 4, "notes": "..."}
This script applies those results to the contacts table.
"""
from __future__ import annotations

import json

from lead_finder.common import get_db, normalize_phone, now_stamp, WORK_DIR


def run(results_path: str | None = None) -> int:
    path = results_path or (WORK_DIR / "claude_results.jsonl")
    try:
        lines = open(path, "r", encoding="utf-8").read().splitlines()
    except FileNotFoundError:
        raise SystemExit(f"No results at {path}. Run the /enrich-owners Claude pass first.")

    conn = get_db()
    applied = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            print(f"[apply] skipping malformed line: {line[:80]}")
            continue
        bid = r.get("business_id")
        if not bid:
            continue
        conn.execute(
            """UPDATE contacts SET
                 owner_name   = COALESCE(?, owner_name),
                 owner_title  = COALESCE(?, owner_title),
                 email        = COALESCE(?, email),
                 email_source = CASE WHEN ? IS NOT NULL THEN 'site' ELSE email_source END,
                 direct_phone = COALESCE(?, direct_phone),
                 fit_score    = COALESCE(?, fit_score),
                 method       = 'claude',
                 needs_claude = 0,
                 notes        = ?
               WHERE business_id = ?""",
            (r.get("owner_name"), r.get("owner_title"), r.get("email"), r.get("email"),
             normalize_phone(r.get("direct_phone")), r.get("fit_score"), r.get("notes"), bid),
        )
        applied += 1
    conn.commit()
    conn.close()
    print(f"[apply] applied {applied} extraction results - {now_stamp()}")
    return applied
