# Session handoff - Quixify lead gen + Holiday Sprint outreach

Paste this file into the next Claude Code session to continue. Written 2026-10-08.
Owner: Zunaira (Quixify Media, zunaira@quixifymedia.com). Repo: `zunairaadnan59-droid/lead-gen-system`.

---

## 1. Where things stand (one paragraph)

848 local boutique leads collected across 21 high-income US cities; 64 have an email. A value-first
offer ("Holiday Sales Sprint") and a personal Day 1 cold email for each of the 64 are written and live
in the Google Sheet. A self-hosted **n8n** workflow was built to send the 4-step sequence from the
Hostinger mailbox; Zunaira still has to install n8n, add credentials and switch it on. Last open question:
how to reach the 784 leads without an email (proposal in section 9, **awaiting her yes**).

---

## 2. Key links and IDs

| Thing | Value |
|---|---|
| Google Sheet "Lead Database" | https://docs.google.com/spreadsheets/d/1jjELdaXwB4u9jRgb1yU4I9T3v-v2-mFEH4S_PdZDxPE/edit (owner quixifymedia.ae@gmail.com) |
| Sheet tabs we added | `lead database` (sheetId 1900000001, all 848 leads), `outreach offer` (1900000002), `outreach` (1900000003, the 64 emails) |
| Other existing tabs (don't touch) | Pakistan, Apollo Import Green Yellow Filtered, United States, United Kingdom, UAE, Singapore, Malaysia, Australia, D2C Food & Bev Outreach |
| Portfolio PDF (proof) | https://drive.google.com/file/d/1IGIYt1fk7qlcFYgHbWXH48fI3DDCGk9Y/view?usp=sharing (anyone with link can view) |
| Working git branch | `claude/modest-turing-e4a18n` (all work pushed; last commit `73f3d71`) |
| Repo default branch | `claude/leadgen-github-setup-ipqza8` (GitHub only runs scheduled/new workflows from here) |
| Sender mailbox | zunaira@quixifymedia.com on Hostinger (SMTP smtp.hostinger.com:465 SSL, IMAP imap.hostinger.com:993 SSL) |

---

## 3. Zunaira's decisions and preferences (follow these)

- **No phone calls / no SMS.** Outreach is email (and possibly Instagram DMs) only.
- **No postal address** in emails (she declined; we told her once that CAN-SPAM asks for one - don't nag again). Every email has a P.S. opt-out line except the Day 14 break-up.
- **Send to all 64** emails, including the 13 marked "No" (her call). Recommendation stands that "No" rows are low value.
- **Taking on every business** - so **no scarcity / "limited spots" claim** anywhere.
- **Price:** capped at **$1,899/month**; ad spend paid separately by the client to Meta. Only discussed on a call after the prospect watches the free video.
- **Guarantee (confirmed wording):** "If the Sprint doesn't earn its fee back in sales within 2 months, January is on us."
- **Proof:** the portfolio PDF as a **Drive link in the Day 3 follow-up** (not attached - attachments hurt deliverability). No invented results anywhere.
- **Sending:** her Hostinger business email, **self-hosted n8n** (not GitHub, not a paid cold-email tool, no Apollo sequences).
- Signature: `Zunaira` / `Quixify Media | zunaira@quixifymedia.com`.
- House style (CLAUDE.md): no em dashes; keep comments to the non-obvious why.

---

## 4. The leads

- **848 total**, all from YellowPages, local area-code filtered. Per city (approx 35-47 each): Beverly Hills 47, Palo Alto 46, San Francisco 46, Chicago 44, Scottsdale 44, Naples 44, Southampton 44, Greenwich 43, Boca Raton 43, Dallas 42, Houston 42, Aspen 41, New York 41, Boston 41, Atlanta 41, San Diego 39, Miami 39, Los Angeles 38, Austin 38, Seattle 35, Napa 10.
- With email **64** | owner name 27 | owner LinkedIn 8 | company LinkedIn 9.
- Fit scores of the 64 (0-5): 5:4, 4:5, 3:25, 2:13, 1:12, 0:5. "Send?" column: 51 Yes / 13 No.
- **The 784 without email:** 413 have a real website (many never fetched/read yet), 345 only have a YellowPages placeholder site (`*.localsearch.com`), 16 a directory/social page, 10 no website.
- Files: `data/leads/all_leads.csv` (all 848, columns company, owner, owner_title, email, owner_linkedin, company_linkedin, phone, website, location, fit_score, notes, source), `data/leads/outreach_2026-10-07.csv` (the 64 + research + emails), `data/leads.db` (SQLite).
- Enrichment sources: website reads by Claude (178 sites read), Crustdata (owner LinkedIn + 5 verified owner emails). **Crustdata: ~21 credits used, ~15 left** (people search 0.03/result cheap; profile+email ~2/person; contact-enrich endpoint is enterprise-only and refused).

---

## 5. ICP

Independent, owner-run clothing / gift / jewelry / specialty boutiques in affluent US towns, with a
Shopify/online store and/or foot-traffic shop; decision-maker = owner/founder. Pain: holiday sales rely on
regulars, Instagram posts and walk-ins, no paid ads engine; often fixable site leaks (stale promos, broken
prices, closed online store). Trigger: Black Friday (27 Nov 2026) through Christmas. Non-boutiques in the
list (lash/hair salons, fitness/Pilates studios, flooring, events cafe) got bookings/leads-based variants.

---

## 6. The offer - "Holiday Sales Sprint" (full text in sheet tab `outreach offer`)

- **Value first (free):** a personal 5-minute "Holiday Revenue Teardown" video per prospect: 3 places their store loses holiday sales + 3 ready-to-run Meta ad ideas. Theirs to keep.
- **Stack:** (1) holiday Meta ads done-for-you through New Year, (2) top 5 Shopify/site leak fixes before Black Friday, (3) bonus abandoned-cart + holiday email flow, (4) bonus 12 ad creatives from their own photos, (5) bonus gift guide page, (6) weekly plain-English report.
- **Price** up to $1,899/mo (cap). **Guarantee** as in section 3. **Urgency:** setup must start by **10 Nov** (Meta ads need ~2 weeks to learn). No scarcity.
- Built with the Hormozi skill (value equation / Grand Slam Offer) + outbound-leadgen skill's email framework (hook, pain, value, soft CTA, under 120 words).

---

## 7. The sequence

| Step | When | Content |
|---|---|---|
| 1 | Day 1 | Personal email per prospect (sheet `outreach` col N, subject col M), rewritten 2026-10-09 to hook, problem, deadline, free video, yes/no ask (75-115 words) |
| 2 | Day 3 | Follow-up + portfolio Drive link ("Re: <subject>") |
| 3 | Day 7 | Black Friday 10 Nov setup deadline + guarantee |
| 4 | Day 14 | Short break-up, no P.S. |

Per-prospect follow-ups live in sheet `outreach` cols O-Q as formulas over the `outreach offer` templates (B32-B34); n8n sends those cells, falling back to its built-in template if a cell is empty. Templates also in `data/outreach/followups.json`.
Max 20 emails/day, weekdays 9:45am US Eastern (6:45pm Pakistan). 64 leads: all Day 1s in ~4 weekdays,
sequence done ~3 weeks after first send. Simulated run: 250 emails total, cap held, replies/bounces stopped.

---

## 8. Sending setup - n8n (self-hosted)

- Files: `n8n/quixify-outreach-workflow.json` (import into n8n) and `n8n/SETUP.md` (step-by-step guide). Both were sent to Zunaira.
- **Part 1** (schedule, weekdays 9:45am ET): read `outreach` tab, Code node plans follow-ups first then new Day 1s (cap 20), loop one at a time: Send Email (SMTP) -> update sheet row (Status, Step, Day 1 sent, Last sent) -> wait 75s.
- **Part 2** (IMAP trigger, always on): new inbox mail -> Code node classifies reply vs bounce (ignores own address) -> look up row by Email -> set Status `replied`/`bounced` + Reply/notes.
- **Sheet control columns on `outreach` tab, R-V** (were O-S before the follow-up columns were added): Status, Step, Day 1 sent, Last sent, Reply/notes (formatted as plain text). Status: blank = not started, `active`, `done`, `replied`, `bounced`, anything else (e.g. `skip`) = never email.
- Code nodes were tested in Node.js with luxon over a simulated calendar using the real 64 rows. **Not tested:** the import into a real n8n, credential logins, real sending.
- Known limits: sent mail isn't copied to Hostinger "Sent" (sheet is the record); follow-ups thread by "Re:" subject only (n8n Send Email node can't set In-Reply-To).
- **Zunaira's to-do:** install n8n (Docker on laptop or Hostinger VPS one-click), import, add 3 credentials inside n8n (Hostinger SMTP, Hostinger IMAP, Google Sheets OAuth2 via Google Cloud), preview via "Plan today's emails > Execute step", toggle Active. Also check SPF/DKIM/DMARC for quixifymedia.com in hPanel and Hostinger daily send limit > 20.
- Also in repo (backup option, not in use): `lead_finder/outreach.py` + `python run.py outreach [--send]` - a Python sender doing the same with SMTP/IMAP (dry-run default). The GitHub sending workflow was **removed** so n8n is the only sender.

---

## 9. OPEN - next step awaiting Zunaira's answer

Question asked: how to reach the 784 leads without email. Proposal (she hasn't replied yet):
1. **Finish reading websites (free, biggest win):** run Enrich Prep on the ~413 real-website leads not yet read (use `count_per_city=0` mode; consider `max_pages_per_site` 3 -> 5), also capture Instagram handles. Rough estimate 50-100 more emails -> add to `outreach` tab so n8n picks them up.
2. **Instagram DMs** for no-email leads: write a short DM version of the offer; she sends ~20-30/day manually. Put handle-only leads in a new "DM list" tab.
3. **Website contact forms** for best-fit ones (manual).
4. **Email finders** for top leads only: Hunter.io / Snov.io free tiers, Apollo (needs re-auth), Crustdata (~15 credits left, ~7 lookups).
5. The 355 with no real website: weakest; Instagram/Google Maps search or skip.
Avoid: guessed info@ emails without verification (bounces hurt the mailbox), phone/SMS.

---

## 10. How the pipeline works (for running more)

- `python run.py find --city <key> --count N` (discover + export), `enrich-prep`, `apply`, `export --city X --keep --include-delivered`, `load-csv --city X`, `outreach`. Cities/keywords in `config.yaml` (niche = boutique/online store keywords).
- **This cloud sandbox can't reach outside websites** (proxy 403 on yellowpages, overpass, SMTP). Fetching runs on **GitHub Actions** instead:
  - "Find Leads" workflow (inputs: cities, count) - commits CSVs only.
  - "Enrich Prep" workflow (inputs: cities, count_per_city, fetch_limit). `count_per_city=0` = load existing city CSVs and fetch their sites (instead of discovering). Commits DB, `data/raw/` page text and `data/work/needs_claude.jsonl`.
  - Dispatch via GitHub MCP `actions_run_trigger` with `ref: claude/modest-turing-e4a18n`. New workflow files can't be dispatched until they exist on the default branch.
- After Enrich Prep: pull, read queued pages (condense helper approach: grep owner/founder/email/LinkedIn lines), write `data/work/claude_results.jsonl` (business_id, owner_name, owner_title, email, linkedin_url, owner_linkedin, fit_score, notes), `python run.py apply`, clear bad regex emails from mismatched sites, re-export, rebuild `data/leads/all_leads.csv` (export without --city, then rename).
- Google Sheets writes: use the Google Sheets connector (`update_values`, `update_spreadsheet`). Phone numbers need a leading `'` or Sheets drops the `+`. Don't send `writeControl`.

---

## 11. Environment gotchas learned

- claude.ai plugins arrive in cloud sessions **as skills only** (no slash commands/hooks), synced at session start. Plugin display names aren't visible; the "land clients with outreach" plugin is almost certainly the one providing the `outbound-leadgen` skill (hard-coded for Australian B2B tech + Apollo, so adapt it). `quixify-marketer` is hard-coded for Pakistan/PKR. `alex-hormozi-business-growth` used for the offer.
- **Apollo connector needs re-authorisation** (claude.ai connector settings) before Apollo tools work.
- Drive connector can't upload large files (the 694KB PDF failed) - user uploads herself.
- A push of the email-sending code was once blocked by the auto-mode safety classifier; it went through on retry after the stop hook asked to commit. Don't work around denials.
- A stop hook requires all changes committed and pushed before ending a turn.
