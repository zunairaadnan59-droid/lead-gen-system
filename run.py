#!/usr/bin/env python
"""Local Lead Finder - command-line entrypoint.

Everyday use is through the Claude Code slash commands (/find-leads, /enrich-owners), which
call these subcommands for you. You can also run them directly:

  python run.py find --city austin --count 200      # discover + export a call sheet (fast, free)
  python run.py discover --city austin --count 200  # discovery only
  python run.py enrich-prep [--limit 100]           # fetch sites + queue them for the Claude pass
  python run.py apply                               # merge Claude's owner-extraction results
  python run.py export --city austin [--count 200]  # (re)write the CSV
  python run.py status                              # what's in the database
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lead_finder.common import get_db, load_env  # noqa: E402

load_env()


def cmd_find(args):
    from lead_finder import discover, export
    res = discover.run(args.city, args.count or 100)
    exp = export.run(city=args.city, count=args.count, local=not args.no_local,
                     record_delivered=not args.keep)
    print("=" * 64)
    print(f"DONE  ->  {exp['path']}  ({exp['count']} leads)")
    if not res["enough"]:
        print(f"NOTE: {args.city} yielded {res['added']} unique leads, fewer than the "
              f"{args.count or 100} requested - public sources exhausted for this city.")
    print("=" * 64)


def cmd_discover(args):
    from lead_finder import discover
    discover.run(args.city, args.count or 100)


def cmd_enrich_prep(args):
    from lead_finder import extract, fetch
    fetch.run(limit=args.limit)
    _resolved, needs = extract.run()
    print("=" * 64)
    print(f"{needs} businesses queued -> data/work/needs_claude.jsonl")
    print("Next: the /enrich-owners Claude pass reads each item's text_paths and appends one")
    print("      JSON line per business to data/work/claude_results.jsonl, then: python run.py apply")
    print("=" * 64)


def cmd_apply(args):
    from lead_finder import apply
    apply.run(args.results)


def cmd_export(args):
    from lead_finder import export
    export.run(city=args.city, count=args.count, local=not args.no_local,
               record_delivered=not args.keep)


def cmd_status(_):
    conn = get_db()
    print("Businesses by status:")
    for r in conn.execute("SELECT status, COUNT(*) n FROM businesses GROUP BY status"):
        print(f"  {r['status']:>12}: {r['n']}")
    for r in conn.execute("SELECT source, COUNT(*) n FROM businesses GROUP BY source ORDER BY n DESC"):
        print(f"  source {r['source']:>14}: {r['n']}")
    c = conn.execute(
        "SELECT COUNT(*) total, SUM(CASE WHEN owner_name IS NOT NULL THEN 1 ELSE 0 END) with_owner, "
        "SUM(CASE WHEN email IS NOT NULL THEN 1 ELSE 0 END) with_email FROM contacts").fetchone()
    print(f"Contacts: {c['total'] or 0} | with owner: {c['with_owner'] or 0} | with email: {c['with_email'] or 0}")
    print(f"Delivered (excluded from future runs): "
          f"{conn.execute('SELECT COUNT(*) FROM delivered').fetchone()[0]}")
    conn.close()


def main():
    p = argparse.ArgumentParser(prog="run.py", description="Local Lead Finder")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("find", help="discover + export a call sheet for one city")
    f.add_argument("--city", required=True)
    f.add_argument("--count", type=int, default=100)
    f.add_argument("--no-local", action="store_true", dest="no_local",
                   help="do not restrict to the city's area codes")
    f.add_argument("--keep", action="store_true", help="do NOT mark these as delivered (for testing)")

    d = sub.add_parser("discover", help="discovery only (no export)")
    d.add_argument("--city", required=True)
    d.add_argument("--count", type=int, default=100)

    ep = sub.add_parser("enrich-prep", help="fetch sites + queue them for the Claude owner pass")
    ep.add_argument("--limit", type=int)

    ap = sub.add_parser("apply", help="merge Claude owner-extraction results")
    ap.add_argument("--results")

    e = sub.add_parser("export", help="(re)write the CSV from the database")
    e.add_argument("--city")
    e.add_argument("--count", type=int)
    e.add_argument("--no-local", action="store_true", dest="no_local")
    e.add_argument("--keep", action="store_true")

    sub.add_parser("status", help="summarize the database")

    args = p.parse_args()
    {"find": cmd_find, "discover": cmd_discover, "enrich-prep": cmd_enrich_prep,
     "apply": cmd_apply, "export": cmd_export, "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    main()
