-- Local Lead Finder schema. Plain SQLite; created automatically on first run.

CREATE TABLE IF NOT EXISTS businesses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    website       TEXT,
    domain        TEXT,
    phone         TEXT,                        -- listed business phone from discovery
    address       TEXT,
    city          TEXT,
    state         TEXT,
    source        TEXT,                        -- designrush | yellowpages | openstreetmap | yelp
    status        TEXT DEFAULT 'discovered',   -- discovered | fetched | extracted
    discovered_at TEXT,
    UNIQUE(domain, phone)
);

CREATE TABLE IF NOT EXISTS pages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id  INTEGER NOT NULL,
    url          TEXT,
    content_path TEXT,
    fetched_at   TEXT,
    FOREIGN KEY (business_id) REFERENCES businesses(id)
);

CREATE TABLE IF NOT EXISTS contacts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id   INTEGER NOT NULL UNIQUE,
    owner_name    TEXT,
    owner_title   TEXT,
    email         TEXT,
    email_source  TEXT,                        -- regex | site
    direct_phone  TEXT,
    fit_score     INTEGER,                     -- 0-5, how well it matches your ICP
    method        TEXT,                        -- regex | claude
    needs_claude  INTEGER DEFAULT 0,           -- 1 = queued for the Claude Code extraction pass
    notes         TEXT,
    FOREIGN KEY (business_id) REFERENCES businesses(id)
);

-- Cross-run memory: every exported lead is recorded here so the NEXT run returns fresh leads.
CREATE TABLE IF NOT EXISTS delivered (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id  INTEGER,
    domain       TEXT,
    phone        TEXT,
    delivered_at TEXT,
    UNIQUE(domain, phone)
);

CREATE INDEX IF NOT EXISTS idx_businesses_status ON businesses(status);
CREATE INDEX IF NOT EXISTS idx_businesses_city ON businesses(city);
CREATE INDEX IF NOT EXISTS idx_contacts_needs_claude ON contacts(needs_claude);
CREATE INDEX IF NOT EXISTS idx_delivered_domain ON delivered(domain);
