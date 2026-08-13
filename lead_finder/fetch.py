"""Fetch each business site's key pages to disk (free HTTP), so the owner-extraction pass has
text to read. No API, no metering. Runs concurrently across different hosts.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from lead_finder.common import get_db, http_client, load_config, now_stamp, polite_sleep, RAW_DIR


def _clean(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    # Capture tel:/mailto: hrefs before stripping - sites often expose the phone/email only in
    # a link, not visible text. Surface them so regex + Claude see them.
    contacts = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith("tel:"):
            contacts.append("PHONE: " + href[4:])
        elif href.lower().startswith("mailto:"):
            contacts.append("EMAIL: " + href[7:].split("?")[0])
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    lines = [ln.strip() for ln in soup.get_text(separator="\n").splitlines()]
    body = "\n".join(ln for ln in lines if ln)
    if contacts:
        body = "\n".join(dict.fromkeys(contacts)) + "\n" + body
    return body


def _fetch_site(client, cfg, business) -> list[tuple[str, str]]:
    base = business["website"]
    if not base.startswith("http"):
        base = "https://" + base
    out, seen = [], set()
    for slug in cfg["fetch"]["pages_to_try"]:
        if len(out) >= cfg["fetch"]["max_pages_per_site"]:
            break
        url = base if slug == "" else urljoin(base.rstrip("/") + "/", slug)
        if url in seen:
            continue
        seen.add(url)
        try:
            resp = client.get(url)
            if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                text = _clean(resp.text)
                if len(text) > 200:
                    out.append((url, text))
        except Exception:
            pass
        polite_sleep(cfg)
    return out


def run(limit: int | None = None) -> int:
    cfg = load_config()
    conn = get_db()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM businesses WHERE status='discovered' AND website IS NOT NULL"
        + (f" LIMIT {int(limit)}" if limit else "")
    ).fetchall()]
    total = len(rows)
    workers = int(cfg["fetch"].get("workers", 10))
    print(f"[fetch] {total} sites, {workers} workers - {now_stamp()}")
    if not total:
        conn.close()
        return 0

    client = http_client(cfg)      # httpx.Client is safe for concurrent requests

    def work(business):
        try:
            return business, _fetch_site(client, cfg, business)
        except Exception:
            return business, []

    fetched = done = 0
    try:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for fut in as_completed([ex.submit(work, b) for b in rows]):
                business, pages = fut.result()
                if pages:
                    site_dir = RAW_DIR / str(business["id"])
                    site_dir.mkdir(parents=True, exist_ok=True)
                    for n, (url, text) in enumerate(pages):
                        p = site_dir / f"page_{n}.txt"
                        p.write_text(f"URL: {url}\n\n{text}", encoding="utf-8")
                        conn.execute(
                            "INSERT INTO pages (business_id, url, content_path, fetched_at) VALUES (?,?,?,?)",
                            (business["id"], url, str(p), now_stamp()),
                        )
                    fetched += 1
                conn.execute("UPDATE businesses SET status='fetched' WHERE id=?", (business["id"],))
                done += 1
                if done % 50 == 0:
                    conn.commit()
                    print(f"  ... {done}/{total} ({fetched} with content) - {now_stamp()}")
            conn.commit()
    finally:
        client.close()
        conn.close()
    print(f"[fetch] done - {fetched} sites with content")
    return fetched
