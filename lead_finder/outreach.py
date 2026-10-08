"""Send the cold email sequence from a normal mailbox (SMTP) and stop it when people reply (IMAP).

Built for a small, personal-volume send from one business mailbox (Hostinger by default):
- Day 1 email and subject come from the outreach CSV (one row per prospect).
- Follow-ups come from data/outreach/followups.json and go out as replies in the same thread.
- Before sending, the inbox is checked: anyone who replied, or whose address bounced, is stopped.
- A daily cap counts everything already sent today, so re-running the same day never exceeds it.

Dry-run is the default. Nothing is sent without --send. Credentials come only from the
environment (OUTREACH_EMAIL / OUTREACH_PASSWORD); without them a live run is refused cleanly.
"""
from __future__ import annotations

import csv
import imaplib
import json
import os
import random
import re
import smtplib
import ssl
import time
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import format_datetime, formataddr, make_msgid

from lead_finder.common import ROOT

OUTREACH_DIR = ROOT / "data" / "outreach"
STATE_PATH = OUTREACH_DIR / "state.json"
FOLLOWUPS_PATH = OUTREACH_DIR / "followups.json"
DEFAULT_CSV = ROOT / "data" / "leads" / "outreach_2026-10-07.csv"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def _save_state(state: dict) -> None:
    OUTREACH_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def load_prospects(csv_path=DEFAULT_CSV) -> list[dict]:
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    out = []
    for r in rows:
        body = r["Email (Day 1)"]
        first_line = body.splitlines()[0] if body else ""
        m = re.match(r"Hi ([^,]+),", first_line)
        out.append({
            "email": r["Email"].strip().lower(),
            # Follow-ups greet the same way Day 1 did ("there" when no name was known).
            "first_name": m.group(1).strip() if m else "there",
            "company": re.sub(r"\s*\(.*?\)", "", r["Company"]).strip(),
            "subject": r["Subject"].strip(),
            "body": body,
        })
    return out


def _sent_today(state: dict, today) -> int:
    n = 0
    for rec in state.values():
        for s in rec.get("steps", {}).values():
            if datetime.fromisoformat(s["sent_at"]).date() == today:
                n += 1
    return n


def plan(prospects: list[dict], state: dict, followups: list[dict], cap: int, now=None) -> list[dict]:
    """Return the emails due now: follow-ups first, then new Day 1 sends, within today's cap."""
    now = now or _now()
    budget = cap - _sent_today(state, now.date())
    if budget <= 0:
        return []
    due = []
    by_step = {f["step"]: f for f in followups}
    for p in prospects:
        rec = state.get(p["email"])
        if not rec or rec.get("status") != "active":
            continue
        first = rec["steps"].get("1")
        sent_steps = sorted(int(k) for k in rec["steps"])
        nxt = sent_steps[-1] + 1
        f = by_step.get(nxt)
        if f and now >= datetime.fromisoformat(first["sent_at"]) + timedelta(days=f["day"]):
            body = f["body"].format(first_name=p["first_name"], company=p["company"])
            due.append({"prospect": p, "step": nxt, "subject": "Re: " + p["subject"],
                        "body": body, "reply_to_id": first["message_id"]})
    for p in prospects:
        if p["email"] not in state:
            due.append({"prospect": p, "step": 1, "subject": p["subject"],
                        "body": p["body"], "reply_to_id": None})
    return due[:budget]


def build_message(item: dict, sender: str, sender_name: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = formataddr((sender_name, sender))
    msg["To"] = item["prospect"]["email"]
    msg["Subject"] = item["subject"]
    msg["Date"] = format_datetime(_now())
    msg["Message-ID"] = make_msgid(domain=sender.split("@")[-1])
    if item["reply_to_id"]:
        msg["In-Reply-To"] = item["reply_to_id"]
        msg["References"] = item["reply_to_id"]
    msg.set_content(item["body"])
    return msg


def check_inbox(imap, state: dict) -> dict:
    """Stop the sequence for anyone who replied or bounced. Returns {email: new_status}."""
    changes = {}
    imap.select("INBOX", readonly=True)
    active = {e: r for e, r in state.items() if r.get("status") == "active"}
    if not active:
        return changes
    for email, rec in active.items():
        since = datetime.fromisoformat(rec["steps"]["1"]["sent_at"]).strftime("%d-%b-%Y")
        typ, data = imap.search(None, "FROM", f'"{email}"', "SINCE", since)
        if typ == "OK" and data and data[0].split():
            changes[email] = "replied"
    earliest = min(datetime.fromisoformat(r["steps"]["1"]["sent_at"]) for r in active.values())
    typ, data = imap.search(None, "FROM", '"mailer-daemon"', "SINCE", earliest.strftime("%d-%b-%Y"))
    for num in (data[0].split() if typ == "OK" and data and data[0] else []):
        typ, msg = imap.fetch(num, "(BODY.PEEK[TEXT])")
        text = b"".join(part[1] for part in msg if isinstance(part, tuple)).decode("utf-8", "ignore").lower()
        for email in active:
            if email in text and email not in changes:
                changes[email] = "bounced"
    for email, status in changes.items():
        state[email]["status"] = status
    return changes


def _sent_folder(imap) -> str | None:
    typ, folders = imap.list()
    for f in folders or []:
        line = f.decode("utf-8", "ignore")
        if "\\Sent" in line or line.rstrip('"').lower().endswith("sent"):
            return line.split(' "." ')[-1].split(' "/" ')[-1].strip().strip('"')
    return None


def run(send: bool = False, cap: int = 20, delay: tuple[int, int] = (45, 90),
        csv_path=DEFAULT_CSV, smtp_factory=None, imap_factory=None) -> dict:
    sender = os.environ.get("OUTREACH_EMAIL", "zunaira@quixifymedia.com")
    sender_name = os.environ.get("OUTREACH_FROM_NAME", "Zunaira | Quixify Media")
    password = os.environ.get("OUTREACH_PASSWORD")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.hostinger.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    imap_host = os.environ.get("IMAP_HOST", "imap.hostinger.com")
    imap_port = int(os.environ.get("IMAP_PORT", "993"))

    if send and not password:
        raise SystemExit("[outreach] OUTREACH_PASSWORD is not set. Refusing to send. "
                         "Add it as a secret (never in code or chat).")

    prospects = load_prospects(csv_path)
    followups = json.loads(FOLLOWUPS_PATH.read_text(encoding="utf-8"))["steps"]
    state = _load_state()
    last_step = max(f["step"] for f in followups)

    imap = None
    if password:
        ctx = ssl.create_default_context()
        imap = (imap_factory or (lambda: imaplib.IMAP4_SSL(imap_host, imap_port, ssl_context=ctx)))()
        imap.login(sender, password)
        changes = check_inbox(imap, state)
        for email, status in changes.items():
            print(f"[outreach] stopped {email}: {status}")
        if send:
            _save_state(state)

    due = plan(prospects, state, followups, cap)
    mode = "SEND" if send else "DRY-RUN"
    print(f"[outreach] {mode}: {len(due)} email(s) due (cap {cap}/day, "
          f"{_sent_today(state, _now().date())} already sent today)")

    smtp = None
    sent_folder = _sent_folder(imap) if (send and imap) else None
    try:
        for i, item in enumerate(due):
            p = item["prospect"]
            print(f"  step {item['step']} -> {p['email']} | {item['subject']}")
            if not send:
                continue
            if smtp is None:
                smtp = (smtp_factory or (lambda: smtplib.SMTP_SSL(
                    smtp_host, smtp_port, context=ssl.create_default_context())))()
                smtp.login(sender, password)
            msg = build_message(item, sender, sender_name)
            smtp.send_message(msg)
            rec = state.setdefault(p["email"], {"company": p["company"], "status": "active", "steps": {}})
            rec["steps"][str(item["step"])] = {"sent_at": _now().isoformat(), "message_id": msg["Message-ID"]}
            if item["step"] == last_step:
                rec["status"] = "done"
            _save_state(state)          # after every send, so a crash never re-sends
            if imap and sent_folder:
                try:   # keep a copy in Sent so the thread is visible in the mailbox
                    imap.append(sent_folder, "\\Seen", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
                except Exception:
                    pass
            if i < len(due) - 1 and delay[1] > 0:
                time.sleep(random.randint(*delay))
    finally:
        if smtp:
            smtp.quit()
        if imap:
            try:
                imap.logout()
            except Exception:
                pass

    counts = {}
    for rec in state.values():
        counts[rec["status"]] = counts.get(rec["status"], 0) + 1
    print(f"[outreach] status: {counts or 'nothing sent yet'} | not started: "
          f"{sum(1 for p in prospects if p['email'] not in state)}")
    return {"due": len(due), "counts": counts}
