# Quixify outreach in n8n (self-hosted)

The file `quixify-outreach-workflow.json` sends the Holiday Sprint sequence from
zunaira@quixifymedia.com through Hostinger, using the **outreach** tab of the Lead Database
sheet as its control panel.

## What it does

**Part 1 - every weekday at 9:45am US Eastern (6:45pm Pakistan time):**
1. Reads the `outreach` tab.
2. Picks today's emails: follow-ups that are due first, then new Day 1 emails. Max 20 a day.
   - Day 1: the personal email in column N ("Email (Day 1)").
   - Day 3, 7 and 14: the follow-ups in columns O, P and Q (portfolio link, Black Friday
     deadline + guarantee, break-up), sent with "Re: <same subject>". These cells are formulas
     that fill each prospect's name into the templates on the `outreach offer` tab, so editing a
     template there updates every row. Type over a cell to give one prospect a custom follow-up.
     If a cell is empty, n8n falls back to its built-in copy of the template.
3. Sends them one by one, 75 seconds apart.
4. Writes back to the sheet: Status, Step, Day 1 sent, Last sent.

**Part 2 - all the time:** watches your inbox. When a prospect replies, their Status becomes
`replied` and they get nothing more. Bounce notices set Status to `bounced`.

## You control it from the sheet (columns R to V)

| Status | Meaning |
|---|---|
| (blank) | Not emailed yet. Gets Day 1 when there is room in today's 20. |
| `active` | In the sequence. Gets the next follow-up when it is due. |
| `done` | All 4 emails sent. |
| `replied` / `bounced` | Stopped automatically. |
| anything else, e.g. `skip` | Never emailed. Type this yourself to exclude someone. |

If someone replies from a different address than the one we emailed, set their Status to
`replied` by hand.

## Setup (about 30 minutes, once)

### 1. Run n8n
n8n only sends while it is running, so it must be on at 9:45am US Eastern on weekdays.
- **On your computer:** install Docker Desktop, then run:
  ```
  docker run -d --name n8n --restart unless-stopped -p 5678:5678 -e GENERIC_TIMEZONE=America/New_York -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
  ```
  Open http://localhost:5678 and create your owner account.
- **Always on (recommended):** a small VPS. Hostinger's VPS has a one-click n8n template.

### 2. Import the workflow
In n8n: **Workflows > Add workflow > ... menu > Import from file** and pick
`quixify-outreach-workflow.json`.

### 3. Add three credentials (you type the passwords into n8n, never anywhere else)
- **Hostinger SMTP** (used by "Send via Hostinger"): host `smtp.hostinger.com`, port `465`,
  SSL/TLS on, user `zunaira@quixifymedia.com`, your mailbox password.
- **Hostinger IMAP** (used by "New email in inbox"): host `imap.hostinger.com`, port `993`,
  SSL/TLS on, same user and password.
- **Google Sheets OAuth2** (used by the 4 sheet steps): in n8n create a "Google Sheets OAuth2 API"
  credential and follow its "Docs" link. In short: Google Cloud Console > new project > enable
  the Google Sheets API > OAuth consent screen (External, add yourself as a test user) >
  Credentials > OAuth client ID (Web application) with the redirect URL n8n shows you
  (on your computer: `http://localhost:5678/rest/oauth2-credential/callback`) > paste the
  client ID and secret into n8n > Sign in with Google as quixifymedia.ae@gmail.com.

Then open each node with a red warning and pick the matching credential.

### 4. Preview without sending
Open **Plan today's emails** and click **Execute step**. You will see exactly who would get what
today. Nothing is sent from that button.

### 5. Turn it on
Toggle the workflow to **Active** (top right). From then on it runs by itself.

## Before the first send
- In Hostinger hPanel > Emails > quixifymedia.com, check SPF, DKIM and DMARC are set up.
  Without them cold email goes to spam.
- Check your Hostinger plan's daily sending limit is above 20.

## Good to know
- Sent emails are not copied into your Hostinger "Sent" folder; the sheet is the record.
  Replies still arrive in your inbox as normal.
- Follow-ups thread by subject ("Re: ..."), which Gmail and most inboxes group together.
- 64 prospects at 20 a day: everyone gets Day 1 within about 4 weekdays; the whole sequence
  finishes about 3 weeks after the first send.
