---
description: Use Claude to read the discovered businesses' websites and fill in owner names + emails
argument-hint: [city] [limit]
---

You are the extraction engine for the **Local Lead Finder**. The discovery step found companies,
phones, and websites. Your job now is to read those websites and identify the **owner /
decision-maker** for each one - the part only a capable reader can do well.

Arguments: `$ARGUMENTS`
- Optional first word: the **city key** to re-export afterwards (e.g. `austin`).
- Optional second word: a **limit** on how many sites to fetch this pass (default: all discovered).

## Steps

1. **Fetch + queue.** Run:
   ```
   python run.py enrich-prep [--limit <limit>]
   ```
   This downloads each business site's key pages (home / about / team / contact) to
   `data/raw/<id>/` and writes a work queue to `data/work/needs_claude.jsonl`. Each line has:
   `business_id, name, website, city, state, text_paths, regex_email, regex_phone`.

2. **Read and judge.** Read `data/work/needs_claude.jsonl`. For **each** business, open the files
   listed in its `text_paths` and determine:
   - `owner_name` - the founder / owner / CEO / principal. **Only a real person who leads THIS
     company.** Watch for traps: client testimonials ("- John, CEO of SomeClient"), quoted
     experts, authors of blog posts, and staff who are clearly not decision-makers. If you cannot
     find a genuine owner with reasonable confidence, set `owner_name` to null. A null is better
     than a wrong name.
   - `owner_title` - their exact title if stated (Founder, CEO, Managing Partner, ...).
   - `email` - the best contact email; prefer a personal, on-domain address over info@/hello@.
     Fall back to `regex_email` if the pages have nothing better.
   - `direct_phone` - a direct/owner phone if present, else leave null (the listed phone is
     already captured).
   - `fit_score` - 0-5: how well this is an owner-led small/mid business you could actually reach
     the decision-maker at (5 = clear owner name + small team signals; 0 = faceless or huge corp).
   - `notes` - one short line of evidence ("Founder named on /about", "only a contact form", ...).

3. **Write results.** Append **one JSON object per line** to `data/work/claude_results.jsonl`:
   ```json
   {"business_id": 12, "owner_name": "Jane Smith", "owner_title": "Founder", "email": "jane@acme.com", "direct_phone": null, "fit_score": 4, "notes": "Founder named on /about"}
   ```
   Process every queued business. For big queues, work in batches and keep appending. You may
   spawn parallel subagents to read batches of sites and return these JSON lines - just make sure
   every `business_id` from the queue ends up written exactly once.

4. **Apply + re-export.** Run:
   ```
   python run.py apply
   python run.py export --city <city>        # omit --city to export everything
   ```
   Then tell the user how many owner names were filled and the path to the refreshed CSV.

## Rules

- **Never invent a name or email.** Null beats wrong - these are cold-call sheets and a wrong
  name burns the call. If the site is a testimonial wall or a faceless brand, say so in `notes`
  and leave `owner_name` null.
- This pass uses **your own Claude Code session** to read the pages. No API key, no extra cost.
