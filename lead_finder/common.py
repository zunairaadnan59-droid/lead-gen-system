"""Shared infrastructure: config, database, HTTP, and text/phone helpers.

Nothing here needs an API key. Everything is local files + public HTTP.
"""
from __future__ import annotations

import re
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "leads.db"
SCHEMA_PATH = ROOT / "lead_finder" / "db" / "schema.sql"
RAW_DIR = ROOT / "data" / "raw"
WORK_DIR = ROOT / "data" / "work"

# A normal desktop browser UA. Every source we hit is a public page; we send a real
# UA, honour a polite delay, and stop when a site asks us to (see the source modules).
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def load_env() -> None:
    """Load .env if present. Optional - the free path needs no keys."""
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except Exception:
        pass


def load_config() -> dict:
    with open(ROOT / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    return conn


def http_client(cfg: dict):
    import httpx
    fetch = cfg.get("fetch", {})
    return httpx.Client(
        headers={"User-Agent": fetch.get("user_agent", USER_AGENT)},
        timeout=fetch.get("request_timeout_seconds", 20),
        follow_redirects=True,
    )


def curl_get(url: str, timeout: int = 90) -> str:
    """Fetch a URL with the system `curl`.

    Some public directories fingerprint the TLS handshake of Python HTTP libraries and
    answer them with a 403, while a normal browser (or curl) gets a 200. Shelling out to
    curl - which ships on Windows 10+, macOS, and Linux - sidesteps that without pulling
    in a browser-impersonation dependency. Returns "" on any failure so callers can treat
    an empty result as "blocked or end of listing" and move on.
    """
    try:
        out = subprocess.run(
            ["curl", "-sS", "-L", "--compressed", "--retry", "3", "--retry-connrefused",
             "--retry-all-errors", "-A", USER_AGENT,
             "-H", "Accept-Language: en-US,en;q=0.9",
             "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
             url],
            capture_output=True, timeout=timeout,
        )
        if out.returncode != 0:
            return ""
        return out.stdout.decode("utf-8", "ignore")
    except FileNotFoundError:
        print("  ! curl not found on PATH. Install curl (ships with Windows 10+/macOS/Linux) "
              "or rely on the OpenStreetMap source, which uses Python HTTP.")
        return ""
    except Exception:
        return ""


def polite_sleep(cfg: dict) -> None:
    time.sleep(cfg.get("fetch", {}).get("delay_seconds", 1.0))


# --- database helpers ---

def insert_business(conn, row: dict, city: str | None, state: str | None, source: str) -> bool:
    """Insert one business; returns True if a new row was added (False if a dup)."""
    name = (row.get("name") or "").strip()
    if not name:
        return False
    website = (row.get("website") or "").strip() or None
    before = conn.total_changes
    conn.execute(
        """INSERT OR IGNORE INTO businesses
           (name, website, domain, phone, address, city, state, source, status, discovered_at)
           VALUES (?,?,?,?,?,?,?,?,'discovered',?)""",
        (name, website, domain_of(website), normalize_phone(row.get("phone")),
         (row.get("address") or "").strip() or None, city, state, source, now_stamp()),
    )
    return conn.total_changes > before


def existing_domains(conn) -> set:
    return {r[0] for r in conn.execute(
        "SELECT domain FROM businesses WHERE domain IS NOT NULL")}


def existing_phones(conn) -> set:
    ph = set()
    for q in ("SELECT phone FROM businesses WHERE phone IS NOT NULL",
              "SELECT direct_phone FROM contacts WHERE direct_phone IS NOT NULL"):
        for r in conn.execute(q):
            n = normalize_phone(r[0])
            if n:
                ph.add(n)
    return ph


# --- text + identity helpers ---

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}")

_GENERIC_EMAIL_PREFIXES = {
    "info", "hello", "contact", "support", "sales", "admin", "office",
    "team", "help", "marketing", "press", "careers", "jobs", "hi", "mail",
}


def area_code(phone: str | None) -> str | None:
    d = re.sub(r"\D", "", phone or "")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    return d[:3] if len(d) == 10 else None


def domain_of(url: str | None) -> str | None:
    if not url:
        return None
    try:
        import tldextract
        ext = tldextract.extract(url)
        if ext.domain and ext.suffix:
            return f"{ext.domain}.{ext.suffix}".lower()
    except Exception:
        pass
    try:
        host = urlparse(url if "//" in url else "//" + url).netloc.lower()
        return host[4:] if host.startswith("www.") else host or None
    except Exception:
        return None


def normalize_phone(raw: str | None) -> str | None:
    """Return E.164 (+1XXXXXXXXXX) when confidently US, else None."""
    if not raw:
        return None
    try:
        import phonenumbers
        for m in phonenumbers.PhoneNumberMatcher(raw, "US"):
            return phonenumbers.format_number(m.number, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        pass
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return None


def find_emails(text: str, prefer_domain: str | None = None) -> list[str]:
    """Emails found in text, personal (non-generic) first, on-domain preferred."""
    found, seen = [], set()
    for e in _EMAIL_RE.findall(text or ""):
        e = e.lower().rstrip(".")
        if e not in seen:
            seen.add(e)
            found.append(e)

    def rank(email: str) -> tuple:
        local = email.split("@")[0]
        return (1 if local in _GENERIC_EMAIL_PREFIXES else 0,
                0 if (prefer_domain and prefer_domain in email) else 1)

    return sorted(found, key=rank)


def find_phones(text: str) -> list[str]:
    out, seen = [], set()
    for raw in _PHONE_RE.findall(text or ""):
        norm = normalize_phone(raw)
        if norm and norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out
